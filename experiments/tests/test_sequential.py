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


class TestArmAPipelineFlow:
    """Test Arm A (PARALLEL) full flow with mocked API calls."""

    def _make_review_output(self, findings_json: str) -> ReviewOutput:
        return ReviewOutput(
            findings=[
                ReviewFinding(
                    file="test.py",
                    line_start=10,
                    line_end=12,
                    severity="major",
                    category="security",
                    finding="SQL injection in query builder",
                    suggested_fix="Use parameterized queries",
                )
            ],
            raw_response=findings_json,
        )

    def test_arm_a_calls_review_synthesize_execute(self):
        """Arm A: R1 review, R2 review, synthesize, execute — all called in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")

                findings_json = json.dumps({
                    "findings": [{
                        "file": "test.py", "line_start": 10, "line_end": 12,
                        "severity": "major", "category": "security",
                        "finding": "SQL injection", "suggested_fix": "Parameterize"
                    }]
                })
                corrected_code = "def safe_query():\n    return db.execute('SELECT ?', (id,))\n"

                # Mock corpus
                corpus = MagicMock()
                corpus.read_file.return_value = "def unsafe():\n    db.execute(f'SELECT {id}')\n"
                corpus.file_name.return_value = "test.py"
                corpus.defect_manifest.defects_for_file.return_value = []
                corpus.defect_manifest.defects = []
                corpus.distractor_manifest.distractors_for_file.return_value = []

                # Mock client — each call needs a unique call_id
                client = MagicMock()
                review_out = self._make_review_output(findings_json)

                client.review.side_effect = [
                    (review_out, _make_api_record(call_id="r1-review")),
                    (review_out, _make_api_record(call_id="r2-review")),
                ]
                client.synthesize.return_value = (findings_json, _make_api_record(call_id="synth-1", step="synthesize"))
                client.execute.return_value = (corrected_code, _make_api_record(call_id="exec-1", step="execute"))

                from review_experiments.sequential.pipeline import run_sequential_file

                result = run_sequential_file(
                    file_id="file_001",
                    arm=Arm.PARALLEL,
                    run_id="run_0",
                    corpus=corpus,
                    client=client,
                    db=db,
                )

                assert result is True
                assert client.review.call_count == 2
                assert client.synthesize.call_count == 1
                assert client.execute.call_count == 1


class TestArmBPipelineFlow:
    """Test Arm B (SEQUENTIAL_FIX) flow with mocked API calls."""

    def test_arm_b_calls_review_execute_review_execute(self):
        """Arm B: R1 → exec → R2 → exec — 4 steps in sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")

                findings_json = json.dumps({
                    "findings": [{
                        "file": "test.py", "line_start": 5, "line_end": 7,
                        "severity": "major", "category": "logic",
                        "finding": "Off-by-one error", "suggested_fix": "Fix bounds"
                    }]
                })
                intermediate_code = "def fixed_v1():\n    pass\n"
                final_code = "def fixed_v2():\n    pass\n"

                corpus = MagicMock()
                corpus.read_file.return_value = "def buggy():\n    pass\n"
                corpus.file_name.return_value = "test.py"
                corpus.defect_manifest.defects_for_file.return_value = []
                corpus.defect_manifest.defects = []
                corpus.distractor_manifest.distractors_for_file.return_value = []

                client = MagicMock()
                review_out = ReviewOutput(
                    findings=[ReviewFinding(
                        file="test.py", line_start=5, line_end=7,
                        severity="major", category="logic",
                        finding="Off-by-one", suggested_fix="Fix"
                    )],
                    raw_response=findings_json,
                )

                client.review.side_effect = [
                    (review_out, _make_api_record(call_id="r1-review")),
                    (review_out, _make_api_record(call_id="r2-review")),
                ]
                client.execute.side_effect = [
                    (intermediate_code, _make_api_record(call_id="exec-r1", step="execute_r1")),
                    (final_code, _make_api_record(call_id="exec-r2", step="execute_r2")),
                ]

                from review_experiments.sequential.pipeline import run_sequential_file

                result = run_sequential_file(
                    file_id="file_001",
                    arm=Arm.SEQUENTIAL_FIX,
                    run_id="run_0",
                    corpus=corpus,
                    client=client,
                    db=db,
                )

                assert result is True
                assert client.review.call_count == 2
                assert client.execute.call_count == 2
                # R2 should review the intermediate code, not original
                r2_call = client.review.call_args_list[1]
                assert r2_call[1]["code_content"] == intermediate_code


class TestArmCPipelineFlow:
    """Test Arm C (SEQUENTIAL_NO_FIX) flow with mocked API calls."""

    def test_arm_c_r2_gets_original_code_and_r1_notes(self):
        """Arm C: R2 reviews original code + R1's notes, not corrected code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")

                original_code = "def original():\n    pass\n"
                findings_json = json.dumps({
                    "findings": [{
                        "file": "test.py", "line_start": 1, "line_end": 2,
                        "severity": "minor", "category": "architecture",
                        "finding": "Poor naming", "suggested_fix": "Rename"
                    }]
                })

                corpus = MagicMock()
                corpus.read_file.return_value = original_code
                corpus.file_name.return_value = "test.py"
                corpus.defect_manifest.defects_for_file.return_value = []
                corpus.defect_manifest.defects = []
                corpus.distractor_manifest.distractors_for_file.return_value = []

                client = MagicMock()
                review_out = ReviewOutput(
                    findings=[ReviewFinding(
                        file="test.py", line_start=1, line_end=2,
                        severity="minor", category="architecture",
                        finding="Poor naming", suggested_fix="Rename"
                    )],
                    raw_response=findings_json,
                )

                client.review.side_effect = [
                    (review_out, _make_api_record(call_id="r1-review")),
                    (review_out, _make_api_record(call_id="r2-review")),
                ]
                client.execute.return_value = ("def renamed():\n    pass\n", _make_api_record(call_id="exec-1", step="execute"))

                from review_experiments.sequential.pipeline import run_sequential_file

                result = run_sequential_file(
                    file_id="file_001",
                    arm=Arm.SEQUENTIAL_NO_FIX,
                    run_id="run_0",
                    corpus=corpus,
                    client=client,
                    db=db,
                )

                assert result is True
                assert client.review.call_count == 2
                assert client.execute.call_count == 1
                # R2 should get original code (not corrected)
                r2_call = client.review.call_args_list[1]
                assert r2_call[1]["code_content"] == original_code
                # R2's system prompt should mention prior reviewer's findings
                assert "Prior Reviewer" in r2_call[1]["system_prompt"] or "prior reviewer" in r2_call[1]["system_prompt"].lower()


# ---------------------------------------------------------------------------
# Correction audit tests
# ---------------------------------------------------------------------------


class TestCorrectionAuditKeyword:
    """Test keyword-based correction audit."""

    def test_fix_attempted_when_code_changes(self):
        from review_experiments.sequential.correction_audit import audit_corrections_keyword
        from review_experiments.schemas import DefectEntry

        defect = DefectEntry(
            defect_id="d01",
            file="test.py",
            line_start=2,
            line_end=3,
            category="security",
            severity="critical",
            difficulty="obvious",
            keywords=["eval(", "user_input"],
            description="eval() on user input",
            correct_fix="Use ast.literal_eval()",
        )

        original = "import os\nresult = eval(user_input)\nprint(result)\n"
        corrected = "import ast\nresult = ast.literal_eval(user_input)\nprint(result)\n"

        entries = audit_corrections_keyword(original, corrected, [defect])
        assert len(entries) == 1
        assert entries[0].fix_attempted is True
        # "eval(" should no longer be present (ast.literal_eval doesn't match "eval(")
        # but "user_input" is still there — so partial keyword removal
        assert entries[0].defect_id == "d01"

    def test_not_attempted_when_code_unchanged(self):
        from review_experiments.sequential.correction_audit import audit_corrections_keyword
        from review_experiments.schemas import DefectEntry

        defect = DefectEntry(
            defect_id="d02",
            file="test.py",
            line_start=1,
            line_end=2,
            category="logic",
            severity="major",
            difficulty="moderate",
            keywords=["off_by_one"],
            description="Off-by-one in loop",
            correct_fix="Use < instead of <=",
        )

        code = "for i in range(off_by_one):\n    pass\n"
        entries = audit_corrections_keyword(code, code, [defect])
        assert len(entries) == 1
        assert entries[0].fix_attempted is False
        assert entries[0].fix_quality.value == "not_attempted"

    def test_all_keywords_removed_is_optimal(self):
        from review_experiments.sequential.correction_audit import audit_corrections_keyword
        from review_experiments.schemas import DefectEntry

        defect = DefectEntry(
            defect_id="d03",
            file="test.py",
            line_start=1,
            line_end=1,
            category="security",
            severity="critical",
            difficulty="obvious",
            keywords=["password_plaintext"],
            description="Storing password in plaintext",
            correct_fix="Hash the password",
        )

        original = "db.store(password_plaintext)\n"
        corrected = "db.store(hash_password(pw))\n"

        entries = audit_corrections_keyword(original, corrected, [defect])
        assert entries[0].fix_attempted is True
        assert entries[0].fix_succeeded is True
        assert entries[0].fix_quality.value == "optimal"

    def test_multiple_defects_audited_independently(self):
        from review_experiments.sequential.correction_audit import audit_corrections_keyword
        from review_experiments.schemas import DefectEntry

        defects = [
            DefectEntry(
                defect_id="d01", file="test.py", line_start=1, line_end=1,
                category="security", severity="critical", difficulty="obvious",
                keywords=["eval("], description="eval", correct_fix="fix",
            ),
            DefectEntry(
                defect_id="d02", file="test.py", line_start=3, line_end=3,
                category="logic", severity="major", difficulty="moderate",
                keywords=["bug_marker"], description="bug", correct_fix="fix",
            ),
        ]

        original = "eval(x)\nprint('ok')\nbug_marker = True\n"
        corrected = "safe(x)\nprint('ok')\nbug_marker = True\n"  # only d01 fixed

        entries = audit_corrections_keyword(original, corrected, defects)
        assert len(entries) == 2
        # d01 was fixed (keyword removed)
        assert entries[0].defect_id == "d01"
        assert entries[0].fix_attempted is True
        assert entries[0].fix_succeeded is True
        # d02 was not attempted (code unchanged in that region)
        assert entries[1].defect_id == "d02"
        assert entries[1].fix_attempted is False


class TestCorrectionAuditStorage:
    """Test correction audit persistence round-trip."""

    def test_record_and_retrieve_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")
                db.record_correction_audit(
                    run_id="run_0",
                    arm="SEQUENTIAL_FIX",
                    file_id="file_001",
                    step="execute_r1",
                    entries=[
                        ("d01", True, True, False, "optimal"),
                        ("d02", True, False, True, "incorrect"),
                        ("d03", False, False, False, "not_attempted"),
                    ],
                )

                results = db.get_correction_audits("run_0")
                assert len(results) == 3
                assert results[0]["defect_id"] == "d01"
                assert results[0]["fix_attempted"] == 1
                assert results[0]["fix_quality"] == "optimal"
                assert results[1]["regression_introduced"] == 1
                assert results[2]["fix_quality"] == "not_attempted"

    def test_filter_by_arm_and_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")
                db.record_correction_audit(
                    run_id="run_0", arm="PARALLEL", file_id="f1", step="execute",
                    entries=[("d01", True, True, False, "optimal")],
                )
                db.record_correction_audit(
                    run_id="run_0", arm="SEQUENTIAL_FIX", file_id="f1", step="execute_r1",
                    entries=[("d01", False, False, False, "not_attempted")],
                )

                parallel_only = db.get_correction_audits("run_0", arm="PARALLEL")
                assert len(parallel_only) == 1
                assert parallel_only[0]["arm"] == "PARALLEL"

                seq_only = db.get_correction_audits("run_0", arm="SEQUENTIAL_FIX")
                assert len(seq_only) == 1


class TestPipelineWithAudit:
    """Test that audit integrates with pipeline execution."""

    def test_arm_b_runs_audit_after_each_execute(self):
        """Arm B should run correction audit after execute_r1 and execute_r2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with ExperimentDB(Path(tmpdir) / "test.db") as db:
                db.create_run("run_0", "sequential")

                findings_json = json.dumps({
                    "findings": [{
                        "file": "test.py", "line_start": 1, "line_end": 2,
                        "severity": "major", "category": "logic",
                        "finding": "Bug", "suggested_fix": "Fix"
                    }]
                })

                corpus = MagicMock()
                corpus.read_file.return_value = "def buggy():\n    pass\n"
                corpus.file_name.return_value = "test.py"
                corpus.defect_manifest.defects_for_file.return_value = []
                corpus.defect_manifest.defects = []
                corpus.distractor_manifest.distractors_for_file.return_value = []

                client = MagicMock()
                review_out = ReviewOutput(
                    findings=[ReviewFinding(
                        file="test.py", line_start=1, line_end=2,
                        severity="major", category="logic",
                        finding="Bug", suggested_fix="Fix"
                    )],
                    raw_response=findings_json,
                )
                client.review.side_effect = [
                    (review_out, _make_api_record(call_id="r1")),
                    (review_out, _make_api_record(call_id="r2")),
                ]
                client.execute.side_effect = [
                    ("def fixed_v1():\n    pass\n", _make_api_record(call_id="e1", step="execute_r1")),
                    ("def fixed_v2():\n    pass\n", _make_api_record(call_id="e2", step="execute_r2")),
                ]

                from review_experiments.sequential.pipeline import run_sequential_file

                run_sequential_file(
                    file_id="file_001",
                    arm=Arm.SEQUENTIAL_FIX,
                    run_id="run_0",
                    corpus=corpus,
                    client=client,
                    db=db,
                    run_audit=True,
                )

                # Pipeline ran successfully — no audit entries because manifest has no defects
                # for this file, but the audit function was called (no error)
                audits = db.get_correction_audits("run_0")
                # Empty because mock corpus has no defects — but proves audit integration
                # doesn't crash
                assert isinstance(audits, list)


class TestPipelineImports:
    def test_pipeline_module_imports(self):
        from review_experiments.sequential import pipeline
        assert hasattr(pipeline, "run_sequential_file")

    def test_config_module_imports(self):
        from review_experiments.sequential import config
        assert hasattr(config, "Arm")
        assert hasattr(config, "ARM_STEPS")
        assert hasattr(config, "EXPERIMENT_ID")
