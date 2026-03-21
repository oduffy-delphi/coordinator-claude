#!/usr/bin/env python3
"""Run the persona review experiment in chunkable increments.

Designed for running the full experiment across multiple sessions.
Each invocation picks up where the last one left off (JSON-per-call
crash resume). Use --max-calls to limit cost/time per session.

Usage:
    # Pilot: 3 files, 10 runs, SPECIALIST only
    uv run python scripts/run_persona_experiment.py --pilot

    # Full experiment, 20 calls at a time
    uv run python scripts/run_persona_experiment.py --max-calls 20

    # Check progress without running
    uv run python scripts/run_persona_experiment.py --status

    # Resume with increased timeout (for long reviews)
    uv run python scripts/run_persona_experiment.py --max-calls 50 --timeout 600
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from review_experiments.parser import parse_review_response
from review_experiments.persona.agent_client import ReviewClient
from review_experiments.persona.config import (
    Arm,
    CORPUS_DIR,
    EXPERIMENT_ID,
    RESULTS_DIR,
)
from review_experiments.persona.prompt_builder import (
    build_system_prompt,
    build_user_message,
)


# ---------------------------------------------------------------------------
# Result store (JSON-per-call, crash-resumable)
# ---------------------------------------------------------------------------

class ResultStore:
    def __init__(self, experiment_id: str):
        self.base_dir = RESULTS_DIR / "runs" / experiment_id

    def path(self, arm: str, file_stem: str, run_index: int) -> Path:
        return self.base_dir / arm / file_stem / f"run_{run_index}.json"

    def exists(self, arm: str, file_stem: str, run_index: int) -> bool:
        return self.path(arm, file_stem, run_index).is_file()

    def save(self, arm: str, file_stem: str, run_index: int, data: dict) -> Path:
        p = self.path(arm, file_stem, run_index)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return p

    def count(self) -> int:
        if not self.base_dir.is_dir():
            return 0
        return sum(1 for _ in self.base_dir.rglob("run_*.json"))

    def inventory(self) -> dict[str, dict[str, list[int]]]:
        """Returns {arm: {file_stem: [run_indices]}}."""
        inv: dict[str, dict[str, list[int]]] = {}
        if not self.base_dir.is_dir():
            return inv
        for arm_dir in sorted(self.base_dir.iterdir()):
            if not arm_dir.is_dir():
                continue
            inv[arm_dir.name] = {}
            for file_dir in sorted(arm_dir.iterdir()):
                if not file_dir.is_dir():
                    continue
                runs = sorted(
                    int(p.stem.split("_")[1])
                    for p in file_dir.glob("run_*.json")
                )
                inv[arm_dir.name][file_dir.name] = runs
        return inv


# ---------------------------------------------------------------------------
# Work item generation
# ---------------------------------------------------------------------------

def build_work_items(
    store: ResultStore,
    arms: list[Arm],
    code_files: list[Path],
    n_runs: int,
) -> list[tuple[Arm, Path, int]]:
    """Build interleaved work items, skipping completed ones."""
    items = []
    skipped = 0
    for run_idx in range(n_runs):
        shuffled = list(code_files)
        random.seed(run_idx)  # deterministic shuffle per run for reproducibility
        random.shuffle(shuffled)
        for file_path in shuffled:
            for arm in arms:
                if store.exists(arm.value, file_path.stem, run_idx):
                    skipped += 1
                else:
                    items.append((arm, file_path, run_idx))
    return items, skipped


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(args):
    experiment_id = args.experiment_id
    store = ResultStore(experiment_id)
    client = ReviewClient(model=args.model, timeout=args.timeout)

    # Discover corpus
    corpus_dir = Path(args.corpus_dir) / "files"
    code_files = sorted(
        p for p in corpus_dir.iterdir()
        if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".js")
    )
    if args.files:
        filter_set = set(args.files.split(","))
        code_files = [p for p in code_files if p.name in filter_set]

    if not code_files:
        print(f"No code files found in {corpus_dir}")
        return 1

    arms = [Arm(a) for a in args.arms.split(",")] if args.arms else list(Arm)

    # Build work items
    items, skipped = build_work_items(store, arms, code_files, args.n_runs)
    total = len(items) + skipped

    print(f"Experiment: {experiment_id}")
    print(f"Arms: {[a.value for a in arms]}")
    print(f"Files: {len(code_files)}")
    print(f"Runs: {args.n_runs}")
    print(f"Total matrix: {total} ({len(arms)} arms × {len(code_files)} files × {args.n_runs} runs)")
    print(f"Pending: {len(items)}, Already done: {skipped}")
    print()

    if not items:
        print("Nothing to do — all work items already completed.")
        return 0

    # Apply max-calls limit
    if args.max_calls and args.max_calls < len(items):
        items = items[:args.max_calls]
        print(f"Limiting to {args.max_calls} calls this session ({len(items)} work items)")
        print()

    # Pre-build system prompts
    system_prompts = {arm: build_system_prompt(arm) for arm in arms}

    completed = 0
    failed = 0
    parse_errors = 0
    start_time = time.monotonic()

    for i, (arm, file_path, run_idx) in enumerate(items, 1):
        label = f"[{i}/{len(items)}] {arm.value}/{file_path.stem}/run_{run_idx}"
        print(f"{label} ... ", end="", flush=True)

        try:
            user_msg = build_user_message(file_path)
            response = client.review(
                system_prompt=system_prompts[arm],
                user_message=user_msg,
                arm=arm.value,
                run_id=f"run_{run_idx}",
                file_id=file_path.stem,
            )

            parse_result = parse_review_response(response.text)
            is_parse_error = parse_result.review.parse_status == "parse_failed"
            if is_parse_error:
                parse_errors += 1

            store.save(
                arm=arm.value,
                file_stem=file_path.stem,
                run_index=run_idx,
                data={
                    "review": parse_result.review.model_dump(mode="json"),
                    "call_record": response.call_record.model_dump(mode="json"),
                    "parse_errors": parse_result.errors,
                },
            )
            n_findings = len(parse_result.review.findings)
            print(f"OK ({n_findings} findings, {response.duration_seconds:.0f}s)")
            completed += 1

        except Exception as e:
            failed += 1
            err_msg = str(e)
            if "timed out" in err_msg:
                print(f"TIMEOUT ({args.timeout}s)")
            else:
                print(f"FAILED: {err_msg[:80]}")

    elapsed = time.monotonic() - start_time
    total_done = store.count()

    print()
    print(f"Session: {completed} completed, {failed} failed, {parse_errors} parse errors")
    print(f"Duration: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"Overall progress: {total_done}/{total} ({total_done/total*100:.0f}%)")

    return 0


def show_status(args):
    """Show progress without running anything."""
    experiment_id = args.experiment_id
    store = ResultStore(experiment_id)

    corpus_dir = Path(args.corpus_dir) / "files"
    code_files = sorted(
        p for p in corpus_dir.iterdir()
        if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".js")
    )
    arms = [Arm(a) for a in args.arms.split(",")] if args.arms else list(Arm)

    total = len(arms) * len(code_files) * args.n_runs
    done = store.count()
    inv = store.inventory()

    print(f"Experiment: {experiment_id}")
    print(f"Progress: {done}/{total} ({done/total*100:.0f}%)" if total > 0 else "No work items")
    print()

    for arm_name, files in inv.items():
        print(f"  {arm_name}:")
        for file_stem, runs in files.items():
            print(f"    {file_stem}: {len(runs)} runs ({runs})")


def main():
    parser = argparse.ArgumentParser(description="Run persona review experiment")
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID, help="Experiment identifier")
    parser.add_argument("--n-runs", type=int, default=30, help="Total runs per arm×file")
    parser.add_argument("--arms", default=None, help="Comma-separated arms (default: all)")
    parser.add_argument("--files", default=None, help="Comma-separated filenames (default: all)")
    parser.add_argument("--corpus-dir", default=str(CORPUS_DIR), help="Corpus directory")
    parser.add_argument("--model", default="sonnet", help="Model alias")
    parser.add_argument("--timeout", type=int, default=600, help="Per-call timeout in seconds")
    parser.add_argument("--max-calls", type=int, default=None, help="Max calls this session")
    parser.add_argument("--status", action="store_true", help="Show progress and exit")
    parser.add_argument("--pilot", action="store_true", help="Run pilot (3 files, 10 runs, SPECIALIST)")

    args = parser.parse_args()

    if args.pilot:
        args.experiment_id = f"{EXPERIMENT_ID}_pilot"
        args.n_runs = 10
        args.arms = "SPECIALIST"
        args.files = "config_loader.py,payment_processor.py,task_scheduler.py"

    if args.status:
        show_status(args)
        return

    sys.exit(run(args))


if __name__ == "__main__":
    main()
