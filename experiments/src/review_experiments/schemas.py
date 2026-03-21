"""Pydantic models for experiment data contracts.

All data flows through these types: corpus loading, API responses,
scoring, storage, and analysis.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Corpus schemas
# ---------------------------------------------------------------------------


class DefectEntry(BaseModel):
    """A single seeded defect in a corpus file."""

    defect_id: str  # e.g., "file_001_d01"
    file: str  # relative path within corpus
    line_start: int
    line_end: int
    category: Literal[
        "security",
        "logic",
        "performance",
        "error_handling",
        "architecture",
        "integration",
    ]
    severity: Literal["critical", "major", "minor"]
    difficulty: Literal["obvious", "moderate", "subtle"]
    keywords: list[str]  # for automated matching — substring matches in findings
    description: str
    correct_fix: str


class DistractorEntry(BaseModel):
    """A code pattern that looks suspicious but is actually correct."""

    distractor_id: str
    file: str
    line_start: int
    line_end: int
    description: str
    explanation: str  # why it's actually correct


class DefectManifest(BaseModel):
    """Complete defect manifest for an experiment corpus."""

    experiment: str
    version: str
    defects: list[DefectEntry]

    def defects_for_file(self, file: str) -> list[DefectEntry]:
        return [d for d in self.defects if d.file == file]


class DistractorManifest(BaseModel):
    """Distractor manifest — patterns that should NOT be flagged."""

    experiment: str
    version: str
    distractors: list[DistractorEntry]

    def distractors_for_file(self, file: str) -> list[DistractorEntry]:
        return [d for d in self.distractors if d.file == file]


# ---------------------------------------------------------------------------
# Review output schemas (parsed from Claude responses)
# ---------------------------------------------------------------------------


class ReviewFinding(BaseModel):
    """A single finding from a code review."""

    file: str
    line_start: int
    line_end: int
    severity: str
    category: str
    finding: str
    suggested_fix: str | None = None


class ReviewOutput(BaseModel):
    """Parsed output from a single review API call."""

    findings: list[ReviewFinding]
    raw_response: str  # full API response text
    parse_status: Literal["ok", "parse_failed"] = "ok"


# ---------------------------------------------------------------------------
# Scoring schemas
# ---------------------------------------------------------------------------


class FindingClassification(str, Enum):
    TRUE_POSITIVE = "TP"
    FALSE_POSITIVE_DISTRACTOR = "FP_distractor"
    FALSE_POSITIVE_NOVEL = "FP_novel"
    VALID_UNEXPECTED = "valid_unexpected"


class MatchMethod(str, Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    LLM_JUDGE = "llm_judge"
    NONE = "none"


class ScoredFinding(BaseModel):
    """A review finding matched against the manifest."""

    finding: ReviewFinding
    classification: FindingClassification
    matched_defect_id: str | None = None
    matched_distractor_id: str | None = None
    match_method: MatchMethod = MatchMethod.NONE
    match_score: float | None = None  # numerical similarity; enables post-hoc threshold sensitivity analysis


class FileScore(BaseModel):
    """Aggregated scores for one file in one arm/run."""

    file: str
    arm: str
    run_id: str
    true_positives: list[str] = Field(default_factory=list)  # defect_ids detected
    false_negatives: list[str] = Field(default_factory=list)  # defect_ids missed
    fp_distractor: int = 0
    fp_novel: int = 0
    valid_unexpected: int = 0
    recall: float = 0.0
    precision: float = 0.0
    f1: float = 0.0


# ---------------------------------------------------------------------------
# API call tracking
# ---------------------------------------------------------------------------


class APICallRecord(BaseModel):
    """Record of a single Anthropic API call for provenance and cost tracking."""

    call_id: str  # UUID
    experiment: str
    arm: str
    run_id: str
    file_id: str
    step: str  # "review", "execute", "synthesize"
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_seconds: float
    system_prompt_hash: str  # SHA256
    timestamp: datetime


# ---------------------------------------------------------------------------
# Correction audit (sequential experiment)
# ---------------------------------------------------------------------------


class FixQuality(str, Enum):
    OPTIMAL = "optimal"
    CORRECT_SUBOPTIMAL = "correct_suboptimal"
    INCORRECT = "incorrect"
    NOT_ATTEMPTED = "not_attempted"


class CorrectionAuditEntry(BaseModel):
    """Assessment of a single defect fix by the executor."""

    defect_id: str
    fix_attempted: bool
    fix_succeeded: bool
    regression_introduced: bool
    fix_quality: FixQuality


# ---------------------------------------------------------------------------
# Checkpoint / work item
# ---------------------------------------------------------------------------


class WorkItemStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    PARSE_FAILED = "parse_failed"


class WorkItem(BaseModel):
    """Identifies a single unit of work for checkpoint/resume."""

    experiment: str
    run_id: str
    file_id: str
    arm: str
    step: str  # "review", "execute_r1", "review_r2", etc.
