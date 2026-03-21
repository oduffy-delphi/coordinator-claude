"""CLI entry point for the persona review experiment.

Subcommands: pilot, run, score, analyze.
"""

from __future__ import annotations

from pathlib import Path

import click

from .config import Arm, EXPERIMENT_ID


@click.group()
def main() -> None:
    """Persona review experiment harness."""


@main.command()
@click.option("--runs", "-n", default=10, help="Number of runs per file")
@click.option("--arm", default="SPECIALIST", help="Arm to pilot (default: SPECIALIST)")
@click.option("--files", "-f", multiple=True, help="Specific files to pilot (stems)")
@click.option("--model", "-m", default="sonnet", help="Model alias (default: sonnet)")
def pilot(runs: int, arm: str, files: tuple[str, ...], model: str) -> None:
    """Run the determinism pilot (small-scale variance test)."""
    from .runner import run_pilot

    pilot_arm = Arm(arm)
    pilot_files = list(files) if files else None

    stats = run_pilot(n_runs=runs, pilot_arm=pilot_arm, pilot_files=pilot_files, model=model)
    _print_stats(stats, "Pilot")


@main.command()
@click.option("--runs", "-n", default=5, help="Number of complete runs")
@click.option("--arms", "-a", multiple=True, help="Arms to include (default: all)")
@click.option("--model", "-m", default="sonnet", help="Model alias (default: sonnet)")
@click.option("--experiment-id", default=EXPERIMENT_ID, help="Experiment identifier")
def run(runs: int, arms: tuple[str, ...], model: str, experiment_id: str) -> None:
    """Run the full experiment (or a subset of arms)."""
    from .runner import RunConfig, run_experiment

    arm_list = [Arm(a) for a in arms] if arms else None
    config = RunConfig(
        experiment_id=experiment_id,
        arms=arm_list,
        n_runs=runs,
        model=model,
    )

    stats = run_experiment(config)
    _print_stats(stats, "Experiment")


@main.command()
@click.option("--experiment-id", default=EXPERIMENT_ID, help="Experiment to score")
@click.option("--threshold", default=0.4, help="Match score threshold")
@click.option("--line-tolerance", default=5, help="Line proximity tolerance (±)")
def score(experiment_id: str, threshold: float, line_tolerance: int) -> None:
    """Score all completed results against the manifests."""
    from .scorer import score_experiment

    results = score_experiment(
        experiment_id=experiment_id,
        threshold=threshold,
        line_tolerance=line_tolerance,
    )
    click.echo(f"Scored {results.total_findings} findings across {results.total_reviews} reviews")
    click.echo(f"  TP: {results.true_positives}  FP(distractor): {results.fp_distractor}  "
               f"FP(novel): {results.fp_novel}  Valid unexpected: {results.valid_unexpected}")


@main.command()
@click.option("--experiment-id", default=EXPERIMENT_ID, help="Experiment to analyze")
@click.option("--output", "-o", default=None, help="Output report path")
def analyze(experiment_id: str, output: str | None) -> None:
    """Run the analysis pipeline and generate the report."""
    click.echo(f"Analysis pipeline for {experiment_id} — not yet implemented (Phase 6)")


def _print_stats(stats, label: str) -> None:
    """Pretty-print run statistics."""
    click.echo(f"\n{'=' * 50}")
    click.echo(f"{label} Complete")
    click.echo(f"{'=' * 50}")
    click.echo(f"  Total scheduled:  {stats.total_scheduled}")
    click.echo(f"  Skipped (resume): {stats.skipped_existing}")
    click.echo(f"  Completed:        {stats.completed}")
    click.echo(f"  Failed:           {stats.failed}")
    click.echo(f"  Parse errors:     {stats.parse_errors}")
    click.echo(f"  Duration:         {stats.total_duration:.1f}s")
    click.echo(f"{'=' * 50}\n")
