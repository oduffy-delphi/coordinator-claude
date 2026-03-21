"""Scoring engine for matching review findings against defect/distractor manifests.

Uses deterministic keyword + line proximity matching with optimal bipartite
assignment (no LLM-as-judge). This ensures reproducible, auditable scoring.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import linear_sum_assignment

from ..schemas import (
    DefectEntry,
    DefectManifest,
    DistractorEntry,
    DistractorManifest,
    FindingClassification,
    ReviewFinding,
    ReviewOutput,
    ScoredFinding,
    MatchMethod,
)
from .config import DEFECTS_MANIFEST, DISTRACTORS_MANIFEST, RESULTS_DIR


# ---------------------------------------------------------------------------
# Match scoring
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD = 0.4
DEFAULT_LINE_TOLERANCE = 5
LINE_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4


def _line_overlap(
    finding_start: int,
    finding_end: int,
    target_start: int,
    target_end: int,
    tolerance: int = DEFAULT_LINE_TOLERANCE,
) -> bool:
    """Check if finding's line range overlaps target's range (with tolerance)."""
    return (
        finding_start <= target_end + tolerance
        and finding_end >= target_start - tolerance
    )


def _keyword_score(finding_text: str, keywords: list[str]) -> float:
    """Fraction of keywords that appear as case-insensitive substrings in finding text."""
    if not keywords:
        return 0.0
    text_lower = finding_text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches / len(keywords)


def match_score(
    finding: ReviewFinding,
    defect: DefectEntry,
    line_tolerance: int = DEFAULT_LINE_TOLERANCE,
) -> float:
    """Compute match score between a finding and a defect.

    match_score = line_score * 0.6 + keyword_score * 0.4

    A match is viable if score >= threshold (default 0.4).
    """
    line_score = 1.0 if _line_overlap(
        finding.line_start, finding.line_end,
        defect.line_start, defect.line_end,
        line_tolerance,
    ) else 0.0

    kw_score = _keyword_score(
        finding.finding + " " + (finding.suggested_fix or ""),
        defect.keywords,
    )

    return line_score * LINE_WEIGHT + kw_score * KEYWORD_WEIGHT


def match_score_distractor(
    finding: ReviewFinding,
    distractor: DistractorEntry,
    line_tolerance: int = DEFAULT_LINE_TOLERANCE,
) -> float:
    """Compute match score between a finding and a distractor.

    Uses line overlap only (distractors don't have keywords).
    Returns 1.0 if lines overlap, 0.0 otherwise.
    """
    return 1.0 if _line_overlap(
        finding.line_start, finding.line_end,
        distractor.line_start, distractor.line_end,
        line_tolerance,
    ) else 0.0


# ---------------------------------------------------------------------------
# Bipartite matching
# ---------------------------------------------------------------------------


def _optimal_assignment(
    findings: list[ReviewFinding],
    defects: list[DefectEntry],
    threshold: float = DEFAULT_THRESHOLD,
    line_tolerance: int = DEFAULT_LINE_TOLERANCE,
) -> dict[int, int]:
    """Optimal bipartite matching: findings → defects.

    Uses scipy.optimize.linear_sum_assignment on the negated cost matrix.
    Returns dict mapping finding_index → defect_index for matched pairs.
    """
    if not findings or not defects:
        return {}

    n_findings = len(findings)
    n_defects = len(defects)

    # Build cost matrix (findings × defects)
    cost_matrix = np.zeros((n_findings, n_defects))
    for i, finding in enumerate(findings):
        for j, defect in enumerate(defects):
            score = match_score(finding, defect, line_tolerance)
            cost_matrix[i, j] = score if score >= threshold else 0.0

    # Negate for maximum-weight matching
    # linear_sum_assignment minimizes, so we negate to maximize
    row_indices, col_indices = linear_sum_assignment(-cost_matrix)

    # Filter out zero-weight matches (below threshold)
    matches = {}
    for r, c in zip(row_indices, col_indices):
        if cost_matrix[r, c] > 0:
            matches[r] = c

    return matches


# ---------------------------------------------------------------------------
# Full scoring pipeline
# ---------------------------------------------------------------------------


@dataclass
class ScoredReview:
    """Complete scoring result for one review."""

    file: str
    arm: str
    run_index: int
    scored_findings: list[ScoredFinding]
    undetected_defects: list[str]  # defect_ids not matched by any finding

    @property
    def true_positives(self) -> list[ScoredFinding]:
        return [f for f in self.scored_findings
                if f.classification == FindingClassification.TRUE_POSITIVE]

    @property
    def fp_distractor(self) -> list[ScoredFinding]:
        return [f for f in self.scored_findings
                if f.classification == FindingClassification.FALSE_POSITIVE_DISTRACTOR]

    @property
    def fp_novel(self) -> list[ScoredFinding]:
        return [f for f in self.scored_findings
                if f.classification == FindingClassification.FALSE_POSITIVE_NOVEL]

    @property
    def valid_unexpected(self) -> list[ScoredFinding]:
        return [f for f in self.scored_findings
                if f.classification == FindingClassification.VALID_UNEXPECTED]

    @property
    def recall(self) -> float:
        total_defects = len(self.true_positives) + len(self.undetected_defects)
        if total_defects == 0:
            return 1.0  # No defects to find = perfect recall
        return len(self.true_positives) / total_defects

    @property
    def precision(self) -> float:
        total_findings = len(self.scored_findings)
        if total_findings == 0:
            return 1.0
        useful = len(self.true_positives) + len(self.valid_unexpected)
        return useful / total_findings


def score_review(
    review: ReviewOutput,
    file_stem: str,
    arm: str,
    run_index: int,
    defect_manifest: DefectManifest,
    distractor_manifest: DistractorManifest,
    threshold: float = DEFAULT_THRESHOLD,
    line_tolerance: int = DEFAULT_LINE_TOLERANCE,
) -> ScoredReview:
    """Score a single review against the manifests.

    Pipeline:
    1. Compute optimal bipartite matching: findings → defects
    2. Classify matched findings as TP
    3. Check unmatched findings against distractors
    4. Remaining unmatched findings = novel FP
    5. Unmatched defects = false negatives
    """
    # Get file-specific defects and distractors
    # Match against any finding whose file field contains the stem
    file_defects = [d for d in defect_manifest.defects if file_stem in d.file]
    file_distractors = [d for d in distractor_manifest.distractors if file_stem in d.file]

    findings = review.findings
    scored: list[ScoredFinding] = []

    # Step 1-2: Optimal bipartite assignment (findings → defects)
    assignment = _optimal_assignment(findings, file_defects, threshold, line_tolerance)

    matched_finding_indices = set(assignment.keys())
    matched_defect_indices = set(assignment.values())

    # Classify matched findings as TP
    for finding_idx, defect_idx in assignment.items():
        scored.append(ScoredFinding(
            finding=findings[finding_idx],
            classification=FindingClassification.TRUE_POSITIVE,
            matched_defect_id=file_defects[defect_idx].defect_id,
            match_method=MatchMethod.FUZZY,
        ))

    # Step 3: Check unmatched findings against distractors
    for i, finding in enumerate(findings):
        if i in matched_finding_indices:
            continue

        # Check against distractors
        is_distractor = False
        for distractor in file_distractors:
            if match_score_distractor(finding, distractor, line_tolerance) > 0:
                scored.append(ScoredFinding(
                    finding=finding,
                    classification=FindingClassification.FALSE_POSITIVE_DISTRACTOR,
                    matched_distractor_id=distractor.distractor_id,
                    match_method=MatchMethod.FUZZY,
                ))
                is_distractor = True
                break

        # Step 4: Remaining = novel FP
        if not is_distractor:
            scored.append(ScoredFinding(
                finding=finding,
                classification=FindingClassification.FALSE_POSITIVE_NOVEL,
                match_method=MatchMethod.NONE,
            ))

    # Step 5: Undetected defects
    undetected = [
        file_defects[j].defect_id
        for j in range(len(file_defects))
        if j not in matched_defect_indices
    ]

    return ScoredReview(
        file=file_stem,
        arm=arm,
        run_index=run_index,
        scored_findings=scored,
        undetected_defects=undetected,
    )


# ---------------------------------------------------------------------------
# Batch scoring (score all results from an experiment)
# ---------------------------------------------------------------------------


@dataclass
class ExperimentScores:
    """Aggregated scores across all results in an experiment."""

    total_reviews: int
    total_findings: int
    true_positives: int
    fp_distractor: int
    fp_novel: int
    valid_unexpected: int
    reviews: list[ScoredReview] = field(default_factory=list)


def score_experiment(
    experiment_id: str,
    threshold: float = DEFAULT_THRESHOLD,
    line_tolerance: int = DEFAULT_LINE_TOLERANCE,
    defects_path: Path | None = None,
    distractors_path: Path | None = None,
    results_dir: Path | None = None,
) -> ExperimentScores:
    """Score all completed results for an experiment."""
    # Load manifests
    dp = defects_path or DEFECTS_MANIFEST
    dip = distractors_path or DISTRACTORS_MANIFEST
    rd = (results_dir or RESULTS_DIR) / "runs" / experiment_id

    with open(dp) as f:
        defect_manifest = DefectManifest(**yaml.safe_load(f))
    with open(dip) as f:
        distractor_manifest = DistractorManifest(**yaml.safe_load(f))

    scores = ExperimentScores(
        total_reviews=0,
        total_findings=0,
        true_positives=0,
        fp_distractor=0,
        fp_novel=0,
        valid_unexpected=0,
    )

    if not rd.is_dir():
        return scores

    # Iterate over all result files
    for result_file in rd.rglob("run_*.json"):
        parts = result_file.relative_to(rd).parts
        if len(parts) != 3:
            continue
        arm, file_stem, run_file = parts
        run_index = int(run_file.stem.split("_", 1)[1])

        data = json.loads(result_file.read_text(encoding="utf-8"))
        review = ReviewOutput(**data["review"])

        scored = score_review(
            review=review,
            file_stem=file_stem,
            arm=arm,
            run_index=run_index,
            defect_manifest=defect_manifest,
            distractor_manifest=distractor_manifest,
            threshold=threshold,
            line_tolerance=line_tolerance,
        )

        scores.reviews.append(scored)
        scores.total_reviews += 1
        scores.total_findings += len(scored.scored_findings)
        scores.true_positives += len(scored.true_positives)
        scores.fp_distractor += len(scored.fp_distractor)
        scores.fp_novel += len(scored.fp_novel)
        scores.valid_unexpected += len(scored.valid_unexpected)

    return scores
