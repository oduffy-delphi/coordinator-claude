"""Async orchestrator for running the persona review experiment.

Builds the full matrix of (arm × file × run), randomizes file order per run,
checks the result store for completed work, and runs with adaptive concurrency.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from .api_client import ReviewClient
from .config import Arm, CORPUS_DIR, DEFAULT_CONCURRENCY, EXPERIMENT_ID
from .parser import parse_review_response
from .prompt_builder import build_system_prompt, build_user_message
from .result_store import ResultStore


@dataclass
class RunConfig:
    """Configuration for a single experiment run."""

    experiment_id: str = EXPERIMENT_ID
    arms: list[Arm] | None = None  # None = all arms
    n_runs: int = 5
    concurrency: int = DEFAULT_CONCURRENCY
    corpus_dir: Path | None = None

    def __post_init__(self) -> None:
        if self.arms is None:
            self.arms = list(Arm)


@dataclass
class WorkItem:
    """A single unit of work: one arm × one file × one run."""

    arm: Arm
    file_path: Path
    run_index: int

    @property
    def file_stem(self) -> str:
        return self.file_path.stem


@dataclass
class RunStats:
    """Statistics from a completed experiment run."""

    total_scheduled: int
    skipped_existing: int
    completed: int
    failed: int
    parse_errors: int
    total_duration: float


async def run_experiment(config: RunConfig) -> RunStats:
    """Execute the full experiment matrix.

    For each run, file order is randomized (even though fresh sessions make
    ordering theoretically irrelevant — satisfies the control requirement).
    """
    corpus_dir = config.corpus_dir or CORPUS_DIR / "files"
    store = ResultStore(config.experiment_id)
    client = ReviewClient()

    # Discover corpus files
    code_files = sorted(
        p for p in corpus_dir.iterdir()
        if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".js")
    )
    if not code_files:
        raise FileNotFoundError(f"No code files found in {corpus_dir}")

    # Build work items
    all_items: list[WorkItem] = []
    skipped = 0
    for run_idx in range(config.n_runs):
        # Randomize file order per run
        shuffled = list(code_files)
        random.shuffle(shuffled)
        for arm in config.arms:
            for file_path in shuffled:
                if store.exists(arm.value, file_path.stem, run_idx):
                    skipped += 1
                    continue
                all_items.append(WorkItem(arm=arm, file_path=file_path, run_index=run_idx))

    total_scheduled = len(all_items) + skipped
    print(f"Work items: {len(all_items)} pending, {skipped} skipped (already complete)")
    print(f"Total matrix: {total_scheduled} ({len(config.arms)} arms × {len(code_files)} files × {config.n_runs} runs)")

    if not all_items:
        print("Nothing to do — all work items already completed.")
        return RunStats(
            total_scheduled=total_scheduled,
            skipped_existing=skipped,
            completed=0,
            failed=0,
            parse_errors=0,
            total_duration=0.0,
        )

    # Adaptive concurrency
    semaphore = asyncio.Semaphore(config.concurrency)
    completed = 0
    failed = 0
    parse_errors = 0
    start_time = asyncio.get_event_loop().time()

    # Pre-build system prompts (one per arm, reused across files/runs)
    system_prompts = {arm: build_system_prompt(arm) for arm in config.arms}

    progress = tqdm(total=len(all_items), desc="Reviews", unit="call")

    async def process_item(item: WorkItem) -> None:
        nonlocal completed, failed, parse_errors

        async with semaphore:
            try:
                user_msg = build_user_message(item.file_path)
                response = await client.review(
                    system_prompt=system_prompts[item.arm],
                    user_message=user_msg,
                    arm=item.arm.value,
                    run_id=f"run_{item.run_index}",
                    file_id=item.file_stem,
                )

                # Parse the response
                parse_result = parse_review_response(response.text)
                if parse_result.review.parse_status == "parse_failed":
                    parse_errors += 1

                # Save immediately (crash-resume)
                store.save(
                    arm=item.arm.value,
                    file_stem=item.file_stem,
                    run_index=item.run_index,
                    review=parse_result.review,
                    call_record=response.call_record,
                )
                completed += 1

            except Exception as e:
                failed += 1
                tqdm.write(f"FAILED: {item.arm.value}/{item.file_stem}/run_{item.run_index}: {e}")

            finally:
                progress.update(1)

    # Run all items concurrently (bounded by semaphore)
    tasks = [asyncio.create_task(process_item(item)) for item in all_items]
    await asyncio.gather(*tasks)

    progress.close()
    await client.close()

    total_duration = asyncio.get_event_loop().time() - start_time

    return RunStats(
        total_scheduled=total_scheduled,
        skipped_existing=skipped,
        completed=completed,
        failed=failed,
        parse_errors=parse_errors,
        total_duration=total_duration,
    )


async def run_pilot(
    n_runs: int = 10,
    pilot_arm: Arm = Arm.D,
    pilot_files: list[str] | None = None,
    corpus_dir: Path | None = None,
) -> RunStats:
    """Run the determinism pilot: limited files × limited runs × single arm.

    Default: 3 files × 10 runs × Arm D = 30 calls.
    """
    corpus_dir = corpus_dir or CORPUS_DIR / "files"

    if pilot_files:
        code_files = [corpus_dir / f for f in pilot_files]
    else:
        # Auto-select: first 3 files (should be 1 clean, 1 moderate, 1 dense)
        code_files = sorted(
            p for p in corpus_dir.iterdir()
            if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".js")
        )[:3]

    config = RunConfig(
        experiment_id=f"{EXPERIMENT_ID}_pilot",
        arms=[pilot_arm],
        n_runs=n_runs,
        corpus_dir=corpus_dir,
    )
    # Override corpus_dir to use the pilot files specifically
    config.corpus_dir = corpus_dir

    return await run_experiment(config)
