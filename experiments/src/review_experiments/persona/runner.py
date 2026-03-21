"""Sequential orchestrator for the persona review experiment.

Builds the work matrix (arm × file × run), interleaves arms per file,
checks for completed work, and runs sequentially via agent spawning.
Results are persisted as JSON-per-call for crash recovery.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from ..parser import parse_review_response
from .agent_client import ReviewClient
from .config import Arm, CORPUS_DIR, EXPERIMENT_ID, PILOT_ARM, PILOT_RUNS, RESULTS_DIR
from .prompt_builder import build_system_prompt, build_user_message


# ---------------------------------------------------------------------------
# Result persistence (JSON-per-call, crash-resumable)
# ---------------------------------------------------------------------------


class ResultStore:
    """JSON-per-call persistence for experiment results."""

    def __init__(self, experiment_id: str, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or RESULTS_DIR) / "runs" / experiment_id

    def _path(self, arm: str, file_stem: str, run_index: int) -> Path:
        return self.base_dir / arm / file_stem / f"run_{run_index}.json"

    def exists(self, arm: str, file_stem: str, run_index: int) -> bool:
        return self._path(arm, file_stem, run_index).is_file()

    def save(self, arm: str, file_stem: str, run_index: int, data: dict) -> Path:
        path = self._path(arm, file_stem, run_index)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path

    def load(self, arm: str, file_stem: str, run_index: int) -> dict:
        return json.loads(self._path(arm, file_stem, run_index).read_text(encoding="utf-8"))

    def count_total(self) -> int:
        if not self.base_dir.is_dir():
            return 0
        return sum(1 for _ in self.base_dir.rglob("run_*.json"))


# ---------------------------------------------------------------------------
# Work items and run configuration
# ---------------------------------------------------------------------------


@dataclass
class RunConfig:
    """Configuration for an experiment run."""

    experiment_id: str = EXPERIMENT_ID
    arms: list[Arm] | None = None
    n_runs: int = 5
    corpus_dir: Path | None = None
    model: str = "sonnet"
    file_filter: list[str] | None = None  # Only process these filenames

    def __post_init__(self) -> None:
        if self.arms is None:
            self.arms = list(Arm)


@dataclass
class WorkItem:
    arm: Arm
    file_path: Path
    run_index: int

    @property
    def file_stem(self) -> str:
        return self.file_path.stem


@dataclass
class RunStats:
    total_scheduled: int
    skipped_existing: int
    completed: int
    failed: int
    parse_errors: int
    total_duration: float


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------


def run_experiment(config: RunConfig) -> RunStats:
    """Execute the full experiment matrix sequentially.

    Arms are interleaved within each run: for each file, run both arms
    before moving to the next file.
    """
    corpus_dir = config.corpus_dir or CORPUS_DIR / "files"
    store = ResultStore(config.experiment_id)
    client = ReviewClient(model=config.model)

    code_files = sorted(
        p for p in corpus_dir.iterdir()
        if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".js")
    )
    if config.file_filter:
        filter_set = set(config.file_filter)
        code_files = [p for p in code_files if p.name in filter_set]
    if not code_files:
        raise FileNotFoundError(f"No code files found in {corpus_dir}")

    # Build interleaved work items
    all_items: list[WorkItem] = []
    skipped = 0
    for run_idx in range(config.n_runs):
        shuffled = list(code_files)
        random.shuffle(shuffled)
        for file_path in shuffled:
            for arm in config.arms:
                if store.exists(arm.value, file_path.stem, run_idx):
                    skipped += 1
                    continue
                all_items.append(WorkItem(arm=arm, file_path=file_path, run_index=run_idx))

    total_scheduled = len(all_items) + skipped
    print(f"Work items: {len(all_items)} pending, {skipped} skipped (already complete)")
    print(f"Total matrix: {total_scheduled} ({len(config.arms)} arms × {len(code_files)} files × {config.n_runs} runs)")

    if not all_items:
        print("Nothing to do — all work items already completed.")
        return RunStats(total_scheduled, skipped, 0, 0, 0, 0.0)

    system_prompts = {arm: build_system_prompt(arm) for arm in config.arms}

    completed = 0
    failed = 0
    parse_errors = 0
    start_time = time.monotonic()
    progress = tqdm(total=len(all_items), desc="Reviews", unit="call")

    for item in all_items:
        try:
            user_msg = build_user_message(item.file_path)
            response = client.review(
                system_prompt=system_prompts[item.arm],
                user_message=user_msg,
                arm=item.arm.value,
                run_id=f"run_{item.run_index}",
                file_id=item.file_stem,
            )

            parse_result = parse_review_response(response.text)
            is_parse_error = parse_result.review.parse_status == "parse_failed"
            if is_parse_error:
                parse_errors += 1

            store.save(
                arm=item.arm.value,
                file_stem=item.file_stem,
                run_index=item.run_index,
                data={
                    "review": parse_result.review.model_dump(mode="json"),
                    "call_record": response.call_record.model_dump(mode="json"),
                    "parse_errors": parse_result.errors,
                },
            )
            completed += 1

        except Exception as e:
            failed += 1
            tqdm.write(f"FAILED: {item.arm.value}/{item.file_stem}/run_{item.run_index}: {e}")

        finally:
            progress.update(1)

    progress.close()
    total_duration = time.monotonic() - start_time

    return RunStats(total_scheduled, skipped, completed, failed, parse_errors, total_duration)


def run_pilot(
    n_runs: int = PILOT_RUNS,
    pilot_arm: Arm = PILOT_ARM,
    pilot_files: list[str] | None = None,
    corpus_dir: Path | None = None,
    model: str = "sonnet",
) -> RunStats:
    """Run the determinism pilot: limited files × limited runs × single arm.

    Default: 3 files × 10 runs × SPECIALIST arm = 30 calls.
    """
    corpus_dir = corpus_dir or CORPUS_DIR / "files"

    # Default to first 3 files if none specified
    if not pilot_files:
        all_files = sorted(
            p.name for p in corpus_dir.iterdir()
            if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".js")
        )
        pilot_files = all_files[:3]

    config = RunConfig(
        experiment_id=f"{EXPERIMENT_ID}_pilot",
        arms=[pilot_arm],
        n_runs=n_runs,
        corpus_dir=corpus_dir,
        model=model,
        file_filter=pilot_files,
    )

    return run_experiment(config)
