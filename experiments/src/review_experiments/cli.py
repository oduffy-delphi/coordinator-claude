"""CLI entry point for the experiment harness."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .corpus import Corpus
from .storage import ExperimentDB

console = Console()
DEFAULT_DB = "results/runs.db"


@click.group()
def main():
    """LLM Code Review Experiment Harness."""
    pass


@main.command("validate-corpus")
@click.option("--experiment", required=True, type=click.Choice(["persona", "sequential"]))
@click.option("--corpus-path", default=None, help="Path to corpus directory")
def validate_corpus(experiment: str, corpus_path: str | None):
    """Validate corpus files and manifests."""
    if corpus_path is None:
        corpus_path = str(Path("corpus") / experiment)

    corpus = Corpus(corpus_path)
    errors = corpus.validate()

    if errors:
        console.print(f"[red]Validation failed with {len(errors)} error(s):[/red]")
        for err in errors:
            console.print(f"  - {err}")
        raise SystemExit(1)

    manifest = corpus.defect_manifest
    file_ids = corpus.file_ids()
    console.print(f"[green]Corpus valid.[/green]")
    console.print(f"  Files: {len(file_ids)}")
    console.print(f"  Defects: {len(manifest.defects)}")
    if corpus.distractor_manifest:
        console.print(f"  Distractors: {len(corpus.distractor_manifest.distractors)}")
    console.print(f"  SHA256: {corpus.manifest_sha256()[:16]}...")


# ---------------------------------------------------------------------------
# Persona experiment commands
# ---------------------------------------------------------------------------

@main.group("persona")
def persona_group():
    """Persona review experiment commands."""
    pass


@persona_group.command("run")
@click.option("--n-runs", default=5, help="Number of complete runs")
@click.option("--arms", default=None, help="Comma-separated arm names (default: all)")
@click.option("--files", default=None, help="Comma-separated file IDs (default: all)")
@click.option("--corpus-path", default=None, help="Path to corpus directory")
@click.option("--db", default=DEFAULT_DB, help="Path to results database")
@click.option("--model", default="claude-sonnet-4-20250514", help="Model ID")
@click.option("--temperature", default=0.0, help="Temperature")
@click.option("--dry-run", is_flag=True, help="Show work items without calling API")
def persona_run(
    n_runs: int,
    arms: str | None,
    files: str | None,
    corpus_path: str | None,
    db: str,
    model: str,
    temperature: float,
    dry_run: bool,
):
    """Run the persona review experiment."""
    from .client import ExperimentClient
    from .persona.config import CORPUS_DIR, Arm
    from .persona.prompt_builder import build_system_prompt
    from .persona.pipeline import run_persona_review
    from .schemas import WorkItem

    if corpus_path is None:
        corpus_path = str(CORPUS_DIR)

    corpus = Corpus(corpus_path)
    errors = corpus.validate()
    if errors:
        console.print(f"[red]Corpus validation failed:[/red]")
        for err in errors:
            console.print(f"  - {err}")
        raise SystemExit(1)

    arm_list = [Arm(a) for a in arms.split(",")] if arms else list(Arm)
    file_list = files.split(",") if files else corpus.file_ids()

    if dry_run:
        total = len(arm_list) * len(file_list) * n_runs
        console.print(f"[yellow]Dry run — {total} work items:[/yellow]")
        console.print(f"  Arms: {[a.value for a in arm_list]}")
        console.print(f"  Files: {len(file_list)}")
        console.print(f"  Runs: {n_runs}")
        return

    client = ExperimentClient(model=model, temperature=temperature)

    with ExperimentDB(db) as database:
        completed = 0
        skipped = 0

        for run_idx in range(n_runs):
            for arm in arm_list:
                system_prompt = build_system_prompt(arm)
                for file_id in file_list:
                    item = WorkItem(
                        experiment="persona_review_v1",
                        run_id=f"run_{run_idx}",
                        file_id=file_id,
                        arm=arm.value,
                        step="review",
                    )
                    executed = run_persona_review(
                        item=item,
                        system_prompt=system_prompt,
                        corpus=corpus,
                        client=client,
                        db=database,
                    )
                    if executed:
                        completed += 1
                    else:
                        skipped += 1

        console.print(f"[green]Done. {completed} completed, {skipped} skipped (already done).[/green]")


# ---------------------------------------------------------------------------
# Status and export (shared across experiments)
# ---------------------------------------------------------------------------

@main.command("status")
@click.option("--db", default=DEFAULT_DB, help="Path to results database")
def status(db: str):
    """Show progress of current/past runs."""
    db_path = Path(db)
    if not db_path.exists():
        console.print(f"[red]Database not found: {db}[/red]")
        raise SystemExit(1)

    with ExperimentDB(db) as database:
        cost = database.get_cost_summary()

        table = Table(title="Experiment Status")
        table.add_column("Metric", style="bold")
        table.add_column("Value")

        table.add_row("API Calls", str(cost["api_calls"]))
        table.add_row("Input Tokens", f"{cost['input_tokens']:,}")
        table.add_row("Output Tokens", f"{cost['output_tokens']:,}")
        table.add_row("Total Cost", f"${cost['total_cost_usd']:.2f}")

        console.print(table)


@main.command("export")
@click.option("--experiment", required=True, type=click.Choice(["persona", "sequential"]))
@click.option("--db", default=DEFAULT_DB, help="Path to results database")
@click.option("--format", "fmt", default="csv", type=click.Choice(["csv", "json"]))
@click.option("--output", default=None, help="Output file path")
def export_data(experiment: str, db: str, fmt: str, output: str | None):
    """Export results for external analysis (R, etc.)."""
    import pandas as pd

    db_path = Path(db)
    if not db_path.exists():
        console.print(f"[red]Database not found: {db}[/red]")
        raise SystemExit(1)

    with ExperimentDB(db) as database:
        rows = database.get_file_scores(experiment)

    if not rows:
        console.print("[yellow]No results found.[/yellow]")
        return

    df = pd.DataFrame(rows)

    if output is None:
        output = f"results/{experiment}_scores.{fmt}"

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        df.to_csv(output, index=False)
    else:
        df.to_json(output, orient="records", indent=2)

    console.print(f"[green]Exported {len(df)} rows to {output}[/green]")


if __name__ == "__main__":
    main()
