"""Extract ReviewOutput JSON from LLM responses.

Uses a fallback chain:
1. Regex-extract first ```json ... ``` block, then json.loads()
2. If that fails, attempt repair: strip trailing commas, close unclosed braces
3. If repair fails, flag as parse_error — store raw response for manual inspection
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .schemas import ReviewFinding, ReviewOutput


@dataclass
class ParseResult:
    """Result of attempting to parse a review response."""

    review: ReviewOutput
    errors: list[str] = field(default_factory=list)


# Regex to find the first ```json ... ``` fenced block
_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


def _extract_json_block(text: str) -> str | None:
    """Extract the first ```json fenced block from text."""
    match = _JSON_BLOCK_RE.search(text)
    return match.group(1).strip() if match else None


def _repair_json(raw: str) -> str:
    """Attempt lightweight repairs on malformed JSON."""
    # Strip trailing commas before } or ]
    repaired = re.sub(r",\s*([}\]])", r"\1", raw)
    # Remove control characters (except newline/tab)
    repaired = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", repaired)
    # Close unclosed braces/brackets (simple heuristic)
    opens = repaired.count("{") - repaired.count("}")
    if opens > 0:
        repaired += "}" * opens
    opens = repaired.count("[") - repaired.count("]")
    if opens > 0:
        repaired += "]" * opens
    return repaired


def _dict_to_review(data: dict, raw_response: str) -> ReviewOutput:
    """Convert a parsed JSON dict to a ReviewOutput."""
    findings = []
    for f in data.get("findings", []):
        findings.append(
            ReviewFinding(
                file=f.get("file", "unknown"),
                line_start=f.get("line_start", 0),
                line_end=f.get("line_end", f.get("line_start", 0)),
                severity=f.get("severity", "unknown"),
                category=f.get("category", "unknown"),
                finding=f.get("finding", ""),
                suggested_fix=f.get("suggested_fix"),
            )
        )
    return ReviewOutput(findings=findings, raw_response=raw_response)


def parse_review_response(raw_response: str) -> ParseResult:
    """Parse a raw LLM response into a structured ReviewOutput.

    Tries extraction → repair → fallback in sequence.
    Always returns a ParseResult; check .errors for issues.
    """
    errors: list[str] = []

    # Step 1: Extract JSON block
    json_str = _extract_json_block(raw_response)
    if json_str is None:
        errors.append("No ```json block found in response")
        # Try parsing the entire response as JSON (unlikely but cheap)
        json_str = raw_response

    # Step 2: Try direct parse
    try:
        data = json.loads(json_str)
        return ParseResult(review=_dict_to_review(data, raw_response))
    except json.JSONDecodeError as e:
        errors.append(f"Direct parse failed: {e}")

    # Step 3: Try repair
    repaired = _repair_json(json_str)
    try:
        data = json.loads(repaired)
        errors.append("Parse succeeded after repair")
        return ParseResult(
            review=_dict_to_review(data, raw_response), errors=errors
        )
    except json.JSONDecodeError as e:
        errors.append(f"Repair parse failed: {e}")

    # Step 4: Total failure — return empty review with parse_failed status
    return ParseResult(
        review=ReviewOutput(
            findings=[],
            raw_response=raw_response,
            parse_status="parse_failed",
        ),
        errors=errors,
    )
