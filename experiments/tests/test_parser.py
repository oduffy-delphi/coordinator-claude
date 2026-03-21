"""Tests for the response parser."""

from review_experiments.parser import parse_review_response


def test_valid_json_block():
    """Parse a properly fenced JSON response."""
    raw = '''Here are my findings:

```json
{
  "findings": [
    {
      "file": "app.py",
      "line_start": 10,
      "line_end": 10,
      "severity": "critical",
      "category": "security",
      "finding": "SQL injection",
      "suggested_fix": "Use parameterized queries"
    }
  ]
}
```'''
    result = parse_review_response(raw)
    assert len(result.errors) == 0
    assert result.review.parse_status == "ok"
    assert len(result.review.findings) == 1
    assert result.review.findings[0].file == "app.py"
    assert result.review.findings[0].line_start == 10


def test_bare_json():
    """Parse bare JSON without code fence."""
    raw = '{"findings": [{"file": "x.py", "line_start": 1, "line_end": 1, "severity": "minor", "category": "logic", "finding": "bug"}]}'
    result = parse_review_response(raw)
    assert result.review.parse_status == "ok"
    assert len(result.review.findings) == 1


def test_malformed_json_repair():
    """Trailing commas get repaired."""
    raw = '''```json
{
  "findings": [
    {
      "file": "x.py",
      "line_start": 1,
      "line_end": 1,
      "severity": "minor",
      "category": "logic",
      "finding": "bug",
    },
  ]
}
```'''
    result = parse_review_response(raw)
    assert result.review.parse_status == "ok"
    assert len(result.review.findings) == 1
    assert any("repair" in e.lower() for e in result.errors)


def test_total_parse_failure():
    """Completely unparseable response -> parse_failed."""
    raw = "I found some issues but here they are in prose format, not JSON."
    result = parse_review_response(raw)
    assert result.review.parse_status == "parse_failed"
    assert len(result.review.findings) == 0
    assert len(result.errors) > 0


def test_empty_findings():
    """Valid JSON with no findings."""
    raw = '```json\n{"findings": []}\n```'
    result = parse_review_response(raw)
    assert result.review.parse_status == "ok"
    assert len(result.review.findings) == 0


def test_missing_optional_fields():
    """Findings with missing optional fields get defaults."""
    raw = '```json\n{"findings": [{"file": "x.py", "line_start": 5}]}\n```'
    result = parse_review_response(raw)
    assert result.review.parse_status == "ok"
    assert result.review.findings[0].line_end == 5  # defaults to line_start
    assert result.review.findings[0].severity == "unknown"
    assert result.review.findings[0].suggested_fix is None
