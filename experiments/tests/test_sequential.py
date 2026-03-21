"""Tests for the sequential experiment pipeline."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from review_experiments.schemas import (
    APICallRecord,
    FileScore,
    ReviewFinding,
    ReviewOutput,
    ScoredFinding,
    WorkItem,
    WorkItemStatus,
)
from review_experiments.sequential.config import ARM_STEPS, Arm, EXPERIMENT_ID
from review_experiments.storage import ExperimentDB


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestConfig:
    def test_arm_values(self):
        assert Arm.PARALLEL.value == "PARALLEL"
        assert Arm.SEQUENTIAL_FIX.value == "SEQUENTIAL_FIX"
        assert Arm.SEQUENTIAL_NO_FIX.value == "SEQUENTIAL_NO_FIX"

    def test_all_arms_have_steps(self):
        for arm in Arm:
            assert arm in ARM_STEPS
            assert len(ARM_STEPS[arm]) >= 3

    def test_parallel_step_sequence(self):
        steps = ARM_STEPS[Arm.PARALLEL]
        names = [s[0] for s in steps]
        assert names == ["review_r1", "review_r2", "synthesize", "execute"]

    def test_sequential_fix_step_sequence(self):
        steps = ARM_STEPS[Arm.SEQUENTIAL_FIX]
        names = [s[0] for s in steps]
        assert names == ["review_r1", "execute_r1", "review_r2", "execute_r2"]

    def test_sequential_no_fix_step_sequence(self):
        steps = ARM_STEPS[Arm.SEQUENTIAL_NO_FIX]
        names = [s[0] for s in steps]
        assert names == ["review_r1", "review_r2_with_notes", "execute"]

    def test_step_types_valid(self):
        valid_types = {"review", "execute", "synthesize"}
        for arm in Arm:
            for step_name, step_type in ARM_STEPS[arm]:
                assert step_type in valid_types, f"Invalid step type '{step_type}' in {arm.value}"

    def test_experiment_id(self):
        assert EXPERIMENT_ID == "sequential_review_v1"


# ---------------------------------------------------------------------------
# Storage raw_response round-trip tests
# ---------------------------------------------------------------------------


def _make_api_record(**overrides) -> APICallRecord:
    defaults = {
        "call_id": "test-call-001",
        "experiment": "sequential",
        "arm": "PARALLEL",
        "run_id": "run_0",
        "file_id": "file_001",
        "step": "review_r1",
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


class TestStorageRawResponse:
    """Tests that raw_response is stored and retrievable (bug fix verification)."""

    def test_record_review_stores_raw_response(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")
                item = WorkItem(
                    experiment="sequential",
                    run_id="run_0",
                    file_id="file_001",
                    arm="PARALLEL",
                    step="review_r1",
                )
                raw = '{"findings": [{"file": "test.py", "line_start": 1}]}'
                db.record_review(
                    item=item,
                    api_record=_make_api_record(),
                    review_id="rev-001",
                    findings_json="[]",
                    parse_status="ok",
                    scored_findings=[],
                    file_score=FileScore(file="test.py", arm="PARALLEL", run_id="run_0"),
                    raw_response=raw,
                )

                retrieved = db.get_step_output("run_0", "file_001", "PARALLEL", "review_r1")
                assert retrieved == raw

    def test_record_api_call_only_stores_raw_response(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")
                item = WorkItem(
                    experiment="sequential",
                    run_id="run_0",
                    file_id="file_001",
                    arm="SEQUENTIAL_FIX",
                    step="execute_r1",
                )
                corrected_code = "def fixed_function():\n    return 42\n"
                db.record_api_call_only(
                    item=item,
                    api_record=_make_api_record(
                        call_id="exec-001",
                        arm="SEQUENTIAL_FIX",
                        step="execute_r1",
                    ),
                    raw_response=corrected_code,
                )

                retrieved = db.get_step_output("run_0", "file_001", "SEQUENTIAL_FIX", "execute_r1")
                assert retrieved == corrected_code

    def test_get_step_output_returns_none_for_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                result = db.get_step_output("run_0", "file_001", "PARALLEL", "review_r1")
                assert result is None

    def test_raw_response_none_when_not_provided(self):
        """Backward compat: raw_response defaults to None when not passed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")
                item = WorkItem(
                    experiment="sequential",
                    run_id="run_0",
                    file_id="file_001",
                    arm="PARALLEL",
                    step="review_r1",
                )
                db.record_review(
                    item=item,
                    api_record=_make_api_record(),
                    review_id="rev-002",
                    findings_json="[]",
                    parse_status="ok",
                    scored_findings=[],
                    file_score=FileScore(file="test.py", arm="PARALLEL", run_id="run_0"),
                    # no raw_response passed — should default to None
                )

                retrieved = db.get_step_output("run_0", "file_001", "PARALLEL", "review_r1")
                assert retrieved is None


# ---------------------------------------------------------------------------
# Pipeline checkpoint/resume tests
# ---------------------------------------------------------------------------


class TestPipelineCheckpointResume:
    """Test that the pipeline correctly skips completed steps on resume."""

    def test_all_steps_completed_returns_false(self):
        """If all steps are checkpointed, run_sequential_file returns False (no work done)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")

                # Checkpoint all steps for Arm C (3 steps)
                for step_name, _ in ARM_STEPS[Arm.SEQUENTIAL_NO_FIX]:
                    item = WorkItem(
                        experiment=EXPERIMENT_ID,
                        run_id="run_0",
                        file_id="file_001",
                        arm="SEQUENTIAL_NO_FIX",
                        step=step_name,
                    )
                    db.record_api_call_only(
                        item=item,
                        api_record=_make_api_record(
                            call_id=f"call-{step_name}",
                            arm="SEQUENTIAL_NO_FIX",
                            step=step_name,
                        ),
                        raw_response='{"findings": []}',
                    )

                # Now run the pipeline — should skip everything
                from review_experiments.sequential.pipeline import run_sequential_file

                corpus = MagicMock()
                client = MagicMock()

                result = run_sequential_file(
                    file_id="file_001",
                    arm=Arm.SEQUENTIAL_NO_FIX,
                    run_id="run_0",
                    corpus=corpus,
                    client=client,
                    db=db,
                )
                assert result is False
                # Client should not have been called
                client.review.assert_not_called()
                client.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Pipeline import test
# ---------------------------------------------------------------------------


class TestPipelineImports:
    def test_pipeline_module_imports(self):
        from review_experiments.sequential import pipeline
        assert hasattr(pipeline, "run_sequential_file")

    def test_config_module_imports(self):
        from review_experiments.sequential import config
        assert hasattr(config, "Arm")
        assert hasattr(config, "ARM_STEPS")
        assert hasattr(config, "EXPERIMENT_ID")
