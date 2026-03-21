"""Tests for the SQLite storage layer."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from review_experiments.schemas import (
    APICallRecord,
    FileScore,
    FindingClassification,
    MatchMethod,
    ReviewFinding,
    ScoredFinding,
    WorkItem,
    WorkItemStatus,
)
from review_experiments.storage import ExperimentDB


def _make_api_record(**overrides) -> APICallRecord:
    defaults = {
        "call_id": "test-call-001",
        "experiment": "persona",
        "arm": "A",
        "run_id": "run-1",
        "file_id": "file_001",
        "step": "review",
        "model": "claude-sonnet-4-20250514",
        "input_tokens": 1000,
        "output_tokens": 500,
        "cost_usd": 0.0105,
        "duration_seconds": 2.5,
        "system_prompt_hash": "abc123",
        "timestamp": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return APICallRecord(**defaults)


def test_create_and_close():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = ExperimentDB(db_path)
        assert db_path.exists()
        db.close()


def test_run_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        with ExperimentDB(Path(tmpdir) / "test.db") as db:
            db.create_run("run-1", "persona", config={"model": "sonnet"})
            db.complete_run("run-1")


def test_checkpoint_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        with ExperimentDB(Path(tmpdir) / "test.db") as db:
            item = WorkItem(
                experiment="persona",
                run_id="run-1",
                file_id="file_001",
                arm="A",
                step="review",
            )
            # Not completed yet
            assert not db.is_completed(item)
            assert db.get_checkpoint_status(item) is None

            # Record a review (creates checkpoint)
            db.create_run("run-1", "persona")
            api_record = _make_api_record()
            finding = ReviewFinding(
                file="file_001.py",
                line_start=10,
                line_end=12,
                severity="major",
                category="security",
                finding="SQL injection vulnerability",
            )
            scored = ScoredFinding(
                finding=finding,
                classification=FindingClassification.TRUE_POSITIVE,
                matched_defect_id="file_001_d01",
                match_method=MatchMethod.EXACT,
            )
            file_score = FileScore(
                file="file_001.py",
                arm="A",
                run_id="run-1",
                true_positives=["file_001_d01"],
                false_negatives=["file_001_d02"],
                recall=0.5,
                precision=1.0,
                f1=0.667,
            )
            db.record_review(
                item=item,
                api_record=api_record,
                review_id="rev-001",
                findings_json='[{"finding": "SQL injection"}]',
                parse_status="ok",
                scored_findings=[scored],
                file_score=file_score,
            )

            # Now completed
            assert db.is_completed(item)
            assert db.get_checkpoint_status(item) == WorkItemStatus.COMPLETED


def test_cost_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        with ExperimentDB(Path(tmpdir) / "test.db") as db:
            db.create_run("run-1", "persona")
            item = WorkItem(
                experiment="persona", run_id="run-1", file_id="f1", arm="A", step="review"
            )
            db.record_review(
                item=item,
                api_record=_make_api_record(call_id="c1", file_id="f1"),
                review_id="r1",
                findings_json="[]",
                parse_status="ok",
                scored_findings=[],
                file_score=FileScore(file="f1", arm="A", run_id="run-1"),
            )
            summary = db.get_cost_summary("run-1")
            assert summary["api_calls"] == 1
            assert summary["input_tokens"] == 1000
            assert summary["total_cost_usd"] > 0
