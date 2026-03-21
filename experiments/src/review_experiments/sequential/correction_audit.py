"""Correction audit — per-defect fix quality assessment.

After each executor step, compares the corrected code against the defect
manifest to determine which defects were addressed and how well.

Two audit strategies:
1. **Keyword-based** (default): checks whether defect keywords are still
   present in the corrected code. Fast, deterministic, no API calls.
2. **LLM-based** (optional): uses Haiku to judge whether each defect was
   fixed. More accurate but costs API calls.

The audit runs on ALL arms, not just Arm B — this lets us decompose the
primary outcome (residual defect count) into review effectiveness vs fix
effectiveness independently.
"""

from __future__ import annotations

from ..client import ExperimentClient
from ..schemas import CorrectionAuditEntry, DefectEntry, DefectManifest, FixQuality
from ..storage import ExperimentDB


def audit_corrections_keyword(
    original_code: str,
    corrected_code: str,
    defects: list[DefectEntry],
) -> list[CorrectionAuditEntry]:
    """Audit corrections using keyword presence heuristic.

    For each defect, checks:
    - Whether the corrected code differs from original in the defect's line range
    - Whether defect keywords are still present in the corrected code

    This is a fast, deterministic proxy. The LLM-based audit is more accurate
    but costs API calls per defect.
    """
    original_lines = original_code.splitlines()
    corrected_lines = corrected_code.splitlines()
    entries = []

    for defect in defects:
        # Extract relevant line ranges (0-indexed, with bounds checking)
        start = max(0, defect.line_start - 1)
        end = min(len(original_lines), defect.line_end)
        corr_end = min(len(corrected_lines), defect.line_end)

        orig_region = "\n".join(original_lines[start:end])
        corr_region = "\n".join(corrected_lines[start:corr_end]) if start < len(corrected_lines) else ""

        # Did the code change in this region?
        fix_attempted = orig_region != corr_region

        if not fix_attempted:
            entries.append(CorrectionAuditEntry(
                defect_id=defect.defect_id,
                fix_attempted=False,
                fix_succeeded=False,
                regression_introduced=False,
                fix_quality=FixQuality.NOT_ATTEMPTED,
            ))
            continue

        # Check if defect keywords are still present in the corrected code
        keywords_remaining = sum(
            1 for kw in defect.keywords
            if kw.lower() in corrected_code.lower()
        )
        keywords_total = len(defect.keywords)

        if keywords_total == 0:
            # No keywords to check — can't determine success via keywords
            fix_succeeded = fix_attempted  # assume success if attempted
            quality = FixQuality.CORRECT_SUBOPTIMAL  # uncertain
        elif keywords_remaining == 0:
            fix_succeeded = True
            quality = FixQuality.OPTIMAL
        elif keywords_remaining < keywords_total:
            fix_succeeded = True
            quality = FixQuality.CORRECT_SUBOPTIMAL
        else:
            # All keywords still present — fix likely didn't address the defect
            fix_succeeded = False
            quality = FixQuality.INCORRECT

        entries.append(CorrectionAuditEntry(
            defect_id=defect.defect_id,
            fix_attempted=True,
            fix_succeeded=fix_succeeded,
            regression_introduced=False,  # keyword audit can't detect regressions
            fix_quality=quality,
        ))

    return entries


def audit_corrections_llm(
    original_code: str,
    corrected_code: str,
    defects: list[DefectEntry],
    client: ExperimentClient,
) -> list[CorrectionAuditEntry]:
    """Audit corrections using LLM (Haiku) as judge.

    For each defect, asks Haiku to assess:
    - Was a fix attempted?
    - Did the fix succeed?
    - Was a regression introduced?
    - What is the fix quality?

    More accurate than keyword-based but costs one Haiku call per defect.
    """
    entries = []

    for defect in defects:
        prompt = (
            "You are a code fix quality auditor. Compare the original and corrected "
            "code, then assess whether a specific known defect was addressed.\n\n"
            "Respond with ONLY a JSON object: "
            '{"fix_attempted": true/false, "fix_succeeded": true/false, '
            '"regression_introduced": true/false, '
            '"fix_quality": "optimal"|"correct_suboptimal"|"incorrect"|"not_attempted"}'
        )
        user_msg = (
            f"## Known Defect\n"
            f"ID: {defect.defect_id}\n"
            f"Description: {defect.description}\n"
            f"Location: lines {defect.line_start}-{defect.line_end}\n"
            f"Correct fix: {defect.correct_fix}\n\n"
            f"## Original Code\n```\n{original_code}\n```\n\n"
            f"## Corrected Code\n```\n{corrected_code}\n```\n\n"
            "Assess whether this specific defect was fixed."
        )

        import json
        try:
            response = client._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                temperature=0,
                system=prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = response.content[0].text.strip()
            # Extract JSON
            data = json.loads(text)
            entries.append(CorrectionAuditEntry(
                defect_id=defect.defect_id,
                fix_attempted=data.get("fix_attempted", False),
                fix_succeeded=data.get("fix_succeeded", False),
                regression_introduced=data.get("regression_introduced", False),
                fix_quality=FixQuality(data.get("fix_quality", "not_attempted")),
            ))
        except (json.JSONDecodeError, KeyError, ValueError):
            # Fallback to keyword-based for this defect
            keyword_results = audit_corrections_keyword(
                original_code, corrected_code, [defect]
            )
            entries.extend(keyword_results)

    return entries


def run_correction_audit(
    original_code: str,
    corrected_code: str,
    defect_manifest: DefectManifest,
    file_id: str,
    run_id: str,
    arm: str,
    step: str,
    db: ExperimentDB,
    client: ExperimentClient | None = None,
    use_llm: bool = False,
) -> list[CorrectionAuditEntry]:
    """Run correction audit and persist results.

    Args:
        original_code: Code before executor applied fixes.
        corrected_code: Code after executor applied fixes.
        defect_manifest: Full defect manifest.
        file_id: File identifier.
        run_id: Run identifier.
        arm: Arm name.
        step: Which executor step this audit follows (e.g., "execute_r1").
        db: Database for persisting results.
        client: Required if use_llm=True.
        use_llm: Use Haiku-based audit instead of keyword-based.

    Returns:
        List of CorrectionAuditEntry for each defect in this file.
    """
    # Get defects for this file (try both with and without extension)
    defects = defect_manifest.defects_for_file(file_id)
    if not defects:
        # Try with common extensions stripped
        for suffix in (".py", ".ts", ".tsx", ".js"):
            if file_id.endswith(suffix):
                defects = defect_manifest.defects_for_file(file_id[: -len(suffix)])
                break

    if not defects:
        return []

    if use_llm and client is not None:
        entries = audit_corrections_llm(original_code, corrected_code, defects, client)
    else:
        entries = audit_corrections_keyword(original_code, corrected_code, defects)

    # Persist to DB
    db.record_correction_audit(
        run_id=run_id,
        arm=arm,
        file_id=file_id,
        step=step,
        entries=[
            (e.defect_id, e.fix_attempted, e.fix_succeeded,
             e.regression_introduced, e.fix_quality.value)
            for e in entries
        ],
    )

    return entries
