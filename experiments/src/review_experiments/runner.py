"""Base experiment runner with checkpoint/resume and progress display."""

from __future__ import annotations

import random
import uuid

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn

from .client import ExperimentClient
from .corpus import Corpus
from .persona.arms import ARMS
from .persona.pipeline import run_persona_review
from .schemas import WorkItem
from .scorer import Scorer
from .storage import ExperimentDB

console = Console()


class PersonaExperimentRunner:
    """Runs the persona experiment with checkpoint/resume support."""

    def __init__(
        self,
        corpus: Corpus,
        db: ExperimentDB,
        client: ExperimentClient,
        use_llm_judge: bool = False,
    ):
        self.corpus = corpus
        self.db = db
        self.client = client
        self.scorer = Scorer(
            defect_manifest=corpus.defect_manifest,
            distractor_manifest=corpus.distractor_manifest,
            llm_judge=client if use_llm_judge else None,
            use_llm_judge=use_llm_judge,
        )

    def run(
        self,
        n_runs: int = 5,
        arms: list[str] | None = None,
        file_ids: list[str] | None = None,
        seed: int = 42,
    ) -> None:
        """Run the full persona experiment."""
        arm_names = arms or list(ARMS.keys())
        all_file_ids = file_ids or self.corpus.file_ids()
        corpus_sha = self.corpus.manifest_sha256()

        # Build work items
        work_items: list[tuple[WorkItem, str]] = []  # (item, system_prompt)
        for run_idx in range(1, n_runs + 1):
            run_id = f"run_{run_idx:03d}"

            # Ensure run exists in DB
            try:
                self.db.create_run(
                    run_id=run_id,
                    experiment="persona",
                    config={
                        "n_runs": n_runs,
                        "arms": arm_names,
                        "seed": seed,
                        "model": self.client.model,
                        "temperature": self.client.temperature,
                    },
                    corpus_sha256=corpus_sha,
                )
            except Exception:
                pass  # Run already exists (resume case)

            # Randomize file order per run
            rng = random.Random(seed + run_idx)
            shuffled_files = list(all_file_ids)
            rng.shuffle(shuffled_files)

            # Randomize arm order per file
            for file_id in shuffled_files:
                shuffled_arms = list(arm_names)
                rng.shuffle(shuffled_arms)
                for arm in shuffled_arms:
                    item = WorkItem(
                        experiment="persona",
                        run_id=run_id,
                        file_id=file_id,
                        arm=arm,
                        step="review",
                    )
                    work_items.append((item, ARMS[arm]))

        # Filter out completed items
        pending = [(item, prompt) for item, prompt in work_items if not self.db.is_completed(item)]
        total = len(work_items)
        done = total - len(pending)

        if not pending:
            console.print("[green]All work items already completed.[/green]")
            return

        console.print(f"[bold]Persona experiment[/bold]: {total} total items, {done} already done, {len(pending)} remaining")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Reviewing", total=total, completed=done)

            for item, system_prompt in pending:
                progress.update(task, description=f"[cyan]{item.run_id}[/] {item.file_id} arm={item.arm}")

                result = run_persona_review(
                    item=item,
                    system_prompt=system_prompt,
                    corpus=self.corpus,
                    client=self.client,
                    scorer=self.scorer,
                    db=self.db,
                )

                progress.advance(task)

                if result:
                    scored, file_score = result
                    tp = len(file_score.true_positives)
                    fn = len(file_score.false_negatives)
                    console.print(
                        f"  {item.file_id} arm={item.arm}: "
                        f"[green]{tp} TP[/], [red]{fn} FN[/], "
                        f"recall={file_score.recall:.2f}",
                        highlight=False,
                    )

        # Print summary
        cost = self.db.get_cost_summary()
        console.print(f"\n[bold]Complete.[/bold] Total cost: ${cost['total_cost_usd']:.2f} "
                      f"({cost['api_calls']} calls, {cost['input_tokens'] + cost['output_tokens']:,} tokens)")

    def dry_run(
        self,
        n_runs: int = 5,
        arms: list[str] | None = None,
        file_ids: list[str] | None = None,
        seed: int = 42,
    ) -> None:
        """Show what would be executed without making API calls."""
        arm_names = arms or list(ARMS.keys())
        all_file_ids = file_ids or self.corpus.file_ids()

        total = len(all_file_ids) * len(arm_names) * n_runs
        console.print(f"[bold]Dry run — persona experiment[/bold]")
        console.print(f"  Files: {len(all_file_ids)}")
        console.print(f"  Arms: {arm_names}")
        console.print(f"  Runs: {n_runs}")
        console.print(f"  Total API calls: {total}")
        console.print(f"  Model: {self.client.model}")
        console.print(f"  Temperature: {self.client.temperature}")
