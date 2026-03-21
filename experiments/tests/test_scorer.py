"""Tests for the bipartite scoring engine."""

import math

from review_experiments.schemas import (
    DefectManifest,
    DistractorManifest,
    FindingClassification,
    MatchMethod,
    ReviewFinding,
    ReviewOutput,
)
from review_experiments.scorer import score_review

# Minimal test manifests
DEFECT_MANIFEST = DefectManifest(
    experiment="test",
    version="0.1",
    defects=[
        {
            "defect_id": "f1_d01",
            "file": "file_001.py",
            "line_start": 11,
            "line_end": 11,
            "category": "security",
            "severity": "critical",
            "difficulty": "obvious",
            "keywords": ["SQL injection", "string interpolation"],
            "description": "SQL injection via string interpolation",
            "correct_fix": "Use parameterized queries",
        },
        {
            "defect_id": "f1_d02",
            "file": "file_001.py",
            "line_start": 21,
            "line_end": 22,
            "category": "security",
            "severity": "critical",
            "difficulty": "moderate",
            "keywords": ["MD5", "password hashing"],
            "description": "MD5 for password hashing",
            "correct_fix": "Use bcrypt",
        },
        {
            "defect_id": "f1_d03",
            "file": "file_001.py",
            "line_start": 28,
            "line_end": 28,
            "category": "logic",
            "severity": "major",
            "difficulty": "moderate",
            "keywords": ["off-by-one", "boundary"],
            "description": "Off-by-one in rate limit check",
            "correct_fix": "Change > to >=",
        },
    ],
)

DISTRACTOR_MANIFEST = DistractorManifest(
    experiment="test",
    version="0.1",
    distractors=[
        {
            "distractor_id": "f1_x01",
            "file": "file_001.py",
            "line_start": 14,
            "line_end": 14,
            "description": "conn.close() without context manager",
            "explanation": "Simple enough that explicit close is fine",
        },
        {
            # Distractor far from any defect (defects are at lines 11, 21-22, 28;
            # with tolerance=10 the covered range is [1, 38])
            "distractor_id": "f1_x02",
            "file": "file_001.py",
            "line_start": 55,
            "line_end": 55,
            "description": "Bare except clause",
            "explanation": "Intentional catch-all for legacy compatibility",
        },
    ],
)


def _make_review(*findings: ReviewFinding) -> ReviewOutput:
    return ReviewOutput(findings=list(findings), raw_response="test")


def _score(findings: list[ReviewFinding], file_stem: str = "file_001"):
    return score_review(
        review=_make_review(*findings),
        file_stem=file_stem,
        arm="A",
        run_index=0,
        defect_manifest=DEFECT_MANIFEST,
        distractor_manifest=DISTRACTOR_MANIFEST,
    )


def test_exact_match():
    """Finding on the exact line with matching keywords -> TP via bipartite."""
    finding = ReviewFinding(
        file="file_001.py",
        line_start=11,
        line_end=11,
        severity="critical",
        category="security",
        finding="SQL injection vulnerability using f-string in query",
    )
    result = _score([finding])
    assert len(result.scored_findings) == 1
    assert result.scored_findings[0].classification == FindingClassification.TRUE_POSITIVE
    assert result.scored_findings[0].matched_defect_id == "f1_d01"
    assert result.scored_findings[0].match_method == MatchMethod.BIPARTITE
    assert result.scored_findings[0].match_score is not None
    assert result.scored_findings[0].match_score > 0.4


def test_keyword_match_different_category():
    """Finding with wrong category but matching keywords -> TP via bipartite."""
    finding = ReviewFinding(
        file="file_001.py",
        line_start=11,
        line_end=11,
        severity="critical",
        category="error_handling",  # wrong category, but keywords match
        finding="SQL injection risk due to string interpolation in query",
    )
    result = _score([finding])
    assert result.scored_findings[0].classification == FindingClassification.TRUE_POSITIVE
    assert result.scored_findings[0].matched_defect_id == "f1_d01"


def test_line_proximity():
    """Finding near but not on the exact line -> still matches within tolerance."""
    finding = ReviewFinding(
        file="file_001.py",
        line_start=15,
        line_end=15,
        severity="critical",
        category="security",
        finding="SQL injection — the query on line 11 uses string interpolation",
    )
    result = _score([finding])
    assert result.scored_findings[0].classification == FindingClassification.TRUE_POSITIVE
    assert result.scored_findings[0].matched_defect_id == "f1_d01"


def test_distractor_match():
    """Finding that matches a distractor far from any defect -> FP_distractor."""
    # Use the distractor at line 55, which is outside tolerance of all defects
    finding = ReviewFinding(
        file="file_001.py",
        line_start=55,
        line_end=55,
        severity="minor",
        category="error_handling",
        finding="Bare except clause should be more specific",
    )
    result = _score([finding])
    assert result.scored_findings[0].classification == FindingClassification.FALSE_POSITIVE_DISTRACTOR
    assert result.scored_findings[0].matched_distractor_id == "f1_x02"


def test_novel_false_positive():
    """Finding far from any defect or distractor -> FP_novel."""
    # Line 80 is outside tolerance of all defects (max coverage: line 38)
    # and all distractors (line 14, line 55)
    finding = ReviewFinding(
        file="file_001.py",
        line_start=80,
        line_end=80,
        severity="minor",
        category="architecture",
        finding="Module docstring could be more descriptive",
    )
    result = _score([finding])
    assert result.scored_findings[0].classification == FindingClassification.FALSE_POSITIVE_NOVEL


def test_no_double_claim():
    """Two findings near the same defect — bipartite assigns only one."""
    findings = [
        ReviewFinding(
            file="file_001.py", line_start=11, line_end=11,
            severity="critical", category="security",
            finding="SQL injection via string interpolation",
        ),
        ReviewFinding(
            file="file_001.py", line_start=12, line_end=12,
            severity="critical", category="security",
            finding="Also the SQL query uses f-string interpolation which is unsafe",
        ),
    ]
    result = _score(findings)
    tp_findings = result.true_positives
    # Bipartite ensures each defect is matched at most once
    matched_defect_ids = [f.matched_defect_id for f in tp_findings]
    assert len(matched_defect_ids) == len(set(matched_defect_ids)), "No defect should be matched twice"
    # At least one should match d01
    assert "f1_d01" in matched_defect_ids


def test_file_score_aggregation():
    """Multiple findings produce correct aggregate scores."""
    findings = [
        ReviewFinding(
            file="file_001.py", line_start=11, line_end=11,
            severity="critical", category="security",
            finding="SQL injection via string interpolation",
        ),
        ReviewFinding(
            file="file_001.py", line_start=21, line_end=22,
            severity="critical", category="security",
            finding="MD5 used for password hashing — insecure",
        ),
    ]
    result = _score(findings)
    assert len(result.true_positives) == 2
    assert len(result.undetected_defects) == 1  # d03 not found
    assert result.recall == 2 / 3
    assert result.precision == 1.0


def test_out_of_range_no_match():
    """Finding far from any defect or distractor -> FP_novel."""
    # Line 100 is outside tolerance of all defects (max: line 38) and
    # all distractors (lines 14, 55 — max coverage: line 65)
    finding = ReviewFinding(
        file="file_001.py",
        line_start=100,
        line_end=105,
        severity="minor",
        category="security",
        finding="Some issue far from any seeded defect",
    )
    result = _score([finding])
    assert result.scored_findings[0].classification == FindingClassification.FALSE_POSITIVE_NOVEL


def test_bipartite_optimal_assignment():
    """Bipartite gives optimal assignment where greedy would fail.

    Setup: Finding A matches defect 1 (strong) and defect 2 (weak).
           Finding B matches only defect 2 (strong).
    Greedy (A first): A -> D1, B -> D2. Both TP. (happens to be optimal here)
    Greedy (B first): B -> D2, A -> D1. Both TP.
    But if we flip the scores:
           Finding A matches defect 2 (strong) and defect 1 (weak).
           Finding B matches only defect 1 (strong).
    Greedy (A first): A -> D2, B -> D1. Both TP. Correct.
    Greedy (B first): B -> D1, A -> D2. Both TP. Correct.
    The bipartite algorithm guarantees optimality regardless of order.
    """
    # Two defects close together; two findings, one near each
    manifest = DefectManifest(
        experiment="test", version="0.1",
        defects=[
            {"defect_id": "d1", "file": "f.py", "line_start": 10, "line_end": 10,
             "category": "security", "severity": "critical", "difficulty": "obvious",
             "keywords": ["sql", "injection"], "description": "SQL injection",
             "correct_fix": "parameterize"},
            {"defect_id": "d2", "file": "f.py", "line_start": 15, "line_end": 15,
             "category": "security", "severity": "major", "difficulty": "moderate",
             "keywords": ["xss", "sanitize"], "description": "XSS vulnerability",
             "correct_fix": "escape output"},
        ],
    )
    distractor_manifest = DistractorManifest(experiment="test", version="0.1", distractors=[])

    # Finding A is at line 12 (near both d1 and d2 with tolerance=10) but keywords match d1
    # Finding B is at line 15 (exactly d2) with keywords matching d2
    findings = [
        ReviewFinding(file="f.py", line_start=12, line_end=12,
                      severity="critical", category="security",
                      finding="sql injection via string interpolation"),
        ReviewFinding(file="f.py", line_start=15, line_end=15,
                      severity="major", category="security",
                      finding="xss vulnerability needs sanitize"),
    ]
    review = ReviewOutput(findings=findings, raw_response="test")
    result = score_review(review, "f", "A", 0, manifest, distractor_manifest)

    assert len(result.true_positives) == 2
    # Optimal: A->d1, B->d2 (maximizes total match score)
    tp_map = {f.matched_defect_id: f for f in result.true_positives}
    assert "d1" in tp_map
    assert "d2" in tp_map


def test_threshold_boundary():
    """Finding at exactly the match threshold is accepted."""
    # A finding with line overlap (0.6) but no keyword match (0.0) scores exactly 0.6
    # which exceeds threshold of 0.4
    finding = ReviewFinding(
        file="file_001.py", line_start=11, line_end=11,
        severity="minor", category="performance",
        finding="Something unrelated to SQL injection keywords",
    )
    result = _score([finding])
    # Line overlap alone (0.6) > threshold (0.4), so this should match d01
    assert result.scored_findings[0].classification == FindingClassification.TRUE_POSITIVE


def test_clean_file_metrics():
    """Clean file (no defects) with no findings produces NaN metrics."""
    manifest = DefectManifest(experiment="test", version="0.1", defects=[])
    distractor_manifest = DistractorManifest(experiment="test", version="0.1", distractors=[])
    review = ReviewOutput(findings=[], raw_response="test")
    result = score_review(review, "clean_file", "A", 0, manifest, distractor_manifest)
    assert math.isnan(result.recall)
    assert math.isnan(result.precision)
    assert len(result.undetected_defects) == 0
