"""Tests for the scoring engine."""

from review_experiments.schemas import (
    DefectManifest,
    DistractorManifest,
    FindingClassification,
    MatchMethod,
    ReviewFinding,
)
from review_experiments.scorer import Scorer

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
    ],
)


def _make_scorer(**kwargs) -> Scorer:
    return Scorer(
        defect_manifest=DEFECT_MANIFEST,
        distractor_manifest=DISTRACTOR_MANIFEST,
        **kwargs,
    )


def test_exact_match():
    """Finding on the exact line with matching category → TP."""
    scorer = _make_scorer()
    finding = ReviewFinding(
        file="file_001.py",
        line_start=11,
        line_end=11,
        severity="critical",
        category="security",
        finding="SQL injection vulnerability using f-string in query",
    )
    scored, file_score = scorer.score_findings([finding], "file_001", "A", "run-1")
    assert len(scored) == 1
    assert scored[0].classification == FindingClassification.TRUE_POSITIVE
    assert scored[0].matched_defect_id == "f1_d01"
    assert scored[0].match_method == MatchMethod.EXACT


def test_keyword_match_different_category():
    """Finding with wrong category but matching keywords → TP via keyword."""
    scorer = _make_scorer()
    finding = ReviewFinding(
        file="file_001.py",
        line_start=11,
        line_end=11,
        severity="critical",
        category="error_handling",  # wrong category
        finding="SQL injection risk due to string interpolation in query",
    )
    scored, _ = scorer.score_findings([finding], "file_001", "A", "run-1")
    assert scored[0].classification == FindingClassification.TRUE_POSITIVE
    assert scored[0].matched_defect_id == "f1_d01"


def test_line_proximity():
    """Finding near but not on the exact line → still matches."""
    scorer = _make_scorer()
    finding = ReviewFinding(
        file="file_001.py",
        line_start=15,
        line_end=15,
        severity="critical",
        category="security",
        finding="SQL injection — the query on line 11 uses string interpolation",
    )
    scored, _ = scorer.score_findings([finding], "file_001", "A", "run-1")
    assert scored[0].classification == FindingClassification.TRUE_POSITIVE
    assert scored[0].matched_defect_id == "f1_d01"


def test_distractor_match():
    """Finding that matches a distractor → FP_distractor."""
    scorer = _make_scorer()
    finding = ReviewFinding(
        file="file_001.py",
        line_start=14,
        line_end=14,
        severity="minor",
        category="error_handling",
        finding="Connection not properly closed — should use context manager",
    )
    scored, _ = scorer.score_findings([finding], "file_001", "A", "run-1")
    assert scored[0].classification == FindingClassification.FALSE_POSITIVE_DISTRACTOR


def test_novel_false_positive():
    """Finding that matches nothing → FP_novel."""
    scorer = _make_scorer()
    finding = ReviewFinding(
        file="file_001.py",
        line_start=1,
        line_end=1,
        severity="minor",
        category="architecture",
        finding="Module docstring could be more descriptive",
    )
    scored, _ = scorer.score_findings([finding], "file_001", "A", "run-1")
    assert scored[0].classification == FindingClassification.FALSE_POSITIVE_NOVEL


def test_no_double_claim():
    """Two findings matching the same defect — only the first gets TP."""
    scorer = _make_scorer()
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
    scored, _ = scorer.score_findings(findings, "file_001", "A", "run-1")
    tp_count = sum(1 for s in scored if s.classification == FindingClassification.TRUE_POSITIVE)
    # First one claims d01, second should NOT also match d01
    assert scored[0].classification == FindingClassification.TRUE_POSITIVE
    assert scored[0].matched_defect_id == "f1_d01"
    # Second either matches d02 (different defect, if close enough) or is FP
    assert scored[1].matched_defect_id != "f1_d01" or scored[1].classification != FindingClassification.TRUE_POSITIVE


def test_file_score_aggregation():
    """Multiple findings produce correct aggregate scores."""
    scorer = _make_scorer()
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
    _, file_score = scorer.score_findings(findings, "file_001", "B", "run-2")
    assert len(file_score.true_positives) == 2
    assert len(file_score.false_negatives) == 1  # d03 not found
    assert file_score.recall == 2 / 3
    assert file_score.precision == 1.0


def test_out_of_range_no_match():
    """Finding far from any defect → FP_novel."""
    scorer = _make_scorer()
    finding = ReviewFinding(
        file="file_001.py",
        line_start=50,
        line_end=55,
        severity="minor",
        category="security",
        finding="Some issue far from any seeded defect",
    )
    scored, _ = scorer.score_findings([finding], "file_001", "A", "run-1")
    assert scored[0].classification == FindingClassification.FALSE_POSITIVE_NOVEL
