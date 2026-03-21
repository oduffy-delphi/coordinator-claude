"""Sequential experiment pipeline — multi-step review for each (file, arm) pair.

Each arm has a different step sequence:
  A (PARALLEL):        R1 review, R2 review, synthesize, execute
  B (SEQUENTIAL_FIX):  R1 review, execute R1, R2 review, execute R2
  C (SEQUENTIAL_NO_FIX): R1 review, R2 review (with R1 notes), execute

Uses shared infrastructure (client, parser, scorer, storage) with
per-step checkpointing and intermediate artifact persistence for
crash recovery.
"""

from __future__ import annotations

import json
import math
import uuid

from ..client import ExperimentClient
from ..corpus import Corpus
from ..parser import parse_review_response
from ..schemas import FileScore, ReviewOutput, ScoredFinding, WorkItem, WorkItemStatus
from ..scorer import score_review
from ..storage import ExperimentDB
from .config import ARM_STEPS, Arm, EXPERIMENT_ID


# ---------------------------------------------------------------------------
# Reviewer prompts
# ---------------------------------------------------------------------------

R1_SYSTEM_PROMPT = (
    "You are a domain-focused code reviewer specializing in security and logic. "
    "Focus on: security vulnerabilities, logic errors, incorrect control flow, "
    "race conditions, and input validation issues. Be thorough but precise — "
    "flag real problems, not style preferences."
)

R2_SYSTEM_PROMPT = (
    "You are a generalist code reviewer with broad coverage. "
    "Focus on: error handling, architecture, maintainability, performance, "
    "integration issues, and any remaining defects. Be thorough but precise — "
    "flag real problems, not style preferences."
)

R2_WITH_NOTES_SYSTEM_PROMPT = (
    "You are a generalist code reviewer. A prior reviewer has already examined "
    "this code and found the issues listed below. Your job is to:\n"
    "1. Review the code independently for any issues the prior reviewer missed\n"
    "2. Note any disagreements with the prior reviewer's findings\n"
    "3. Focus on: error handling, architecture, maintainability, performance, "
    "integration issues\n\n"
    "Report ONLY additional findings not already covered by the prior reviewer."
)


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------


def _do_review(
    item: WorkItem,
    system_prompt: str,
    code_content: str,
    file_name: str,
    corpus: Corpus,
    client: ExperimentClient,
    db: ExperimentDB,
) -> ReviewOutput | None:
    """Execute a review step. Returns parsed ReviewOutput, or None on double parse failure."""
    review_output, api_record = client.review(
        system_prompt=system_prompt,
        code_content=code_content,
        file_name=file_name,
        experiment=item.experiment,
        arm=item.arm,
        run_id=item.run_id,
        file_id=item.file_id,
        step=item.step,
    )

    parse_result = parse_review_response(review_output.raw_response)

    # Retry once on parse failure
    if parse_result.review.parse_status == "parse_failed":
        review_output_retry, api_record_retry = client.review(
            system_prompt=system_prompt + "\n\nIMPORTANT: Respond with valid JSON only.",
            code_content=code_content,
            file_name=file_name,
            experiment=item.experiment,
            arm=item.arm,
            run_id=item.run_id,
            file_id=item.file_id,
            step=f"{item.step}_retry",
        )
        retry_result = parse_review_response(review_output_retry.raw_response)
        if retry_result.review.parse_status == "ok":
            parse_result = retry_result
            api_record = api_record_retry

    # Score findings against manifest
    scored = score_review(
        review=parse_result.review,
        file_stem=item.file_id,
        arm=item.arm,
        run_index=int(item.run_id.split("_")[-1]) if "_" in item.run_id else 0,
        defect_manifest=corpus.defect_manifest,
        distractor_manifest=corpus.distractor_manifest,
    )

    file_score = FileScore(
        file=file_name,
        arm=item.arm,
        run_id=item.run_id,
        true_positives=[f.matched_defect_id for f in scored.true_positives],
        false_negatives=scored.undetected_defects,
        fp_distractor=len(scored.fp_distractor),
        fp_novel=len(scored.fp_novel),
        valid_unexpected=len(scored.valid_unexpected),
        recall=scored.recall if not math.isnan(scored.recall) else 0.0,
        precision=scored.precision if not math.isnan(scored.precision) else 0.0,
    )
    if file_score.recall + file_score.precision > 0:
        file_score.f1 = (
            2 * file_score.recall * file_score.precision
            / (file_score.recall + file_score.precision)
        )

    findings_json = json.dumps(
        [f.model_dump() for f in parse_result.review.findings]
    )

    db.record_review(
        item=item,
        api_record=api_record,
        review_id=str(uuid.uuid4()),
        findings_json=findings_json,
        parse_status=parse_result.review.parse_status,
        scored_findings=scored.scored_findings,
        file_score=file_score,
        checkpoint_status=(
            WorkItemStatus.COMPLETED
            if parse_result.review.parse_status == "ok"
            else WorkItemStatus.PARSE_FAILED
        ),
        raw_response=review_output.raw_response,
    )

    if parse_result.review.parse_status == "parse_failed":
        return None
    return parse_result.review


def _do_execute(
    item: WorkItem,
    code_content: str,
    findings_text: str,
    client: ExperimentClient,
    db: ExperimentDB,
) -> str | None:
    """Execute a fix step. Returns corrected code, or None on failure."""
    corrected_code, api_record = client.execute(
        code_content=code_content,
        findings_text=findings_text,
        experiment=item.experiment,
        arm=item.arm,
        run_id=item.run_id,
        file_id=item.file_id,
        step=item.step,
    )

    db.record_api_call_only(
        item=item,
        api_record=api_record,
        raw_response=corrected_code,
    )

    return corrected_code


def _do_synthesize(
    item: WorkItem,
    r1_findings: str,
    r2_findings: str,
    client: ExperimentClient,
    db: ExperimentDB,
) -> str | None:
    """Synthesize two independent review outputs (Arm A). Returns merged findings text."""
    merged_text, api_record = client.synthesize(
        r1_findings=r1_findings,
        r2_findings=r2_findings,
        experiment=item.experiment,
        arm=item.arm,
        run_id=item.run_id,
        file_id=item.file_id,
    )

    db.record_api_call_only(
        item=item,
        api_record=api_record,
        raw_response=merged_text,
    )

    return merged_text


def _format_findings(review: ReviewOutput) -> str:
    """Format review findings as text for executor/R2 consumption."""
    return json.dumps(
        {"findings": [f.model_dump() for f in review.findings]},
        indent=2,
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_sequential_file(
    file_id: str,
    arm: Arm,
    run_id: str,
    corpus: Corpus,
    client: ExperimentClient,
    db: ExperimentDB,
) -> bool:
    """Run the full pipeline for one (file, arm, run) triple.

    Handles checkpoint/resume: checks each step against DB, skips completed
    steps and retrieves their outputs for downstream use.

    Returns True if any work was done, False if all steps already complete.
    """
    steps = ARM_STEPS[arm]
    code_content = corpus.read_file(file_id)
    file_name = corpus.file_name(file_id)

    # Pipeline state — accumulated as steps execute or resume
    r1_review: ReviewOutput | None = None
    r2_review: ReviewOutput | None = None
    r1_findings_text: str | None = None
    r2_findings_text: str | None = None
    corrected_code: str | None = None
    merged_findings: str | None = None
    any_work_done = False

    for step_name, step_type in steps:
        item = WorkItem(
            experiment=EXPERIMENT_ID,
            run_id=run_id,
            file_id=file_id,
            arm=arm.value,
            step=step_name,
        )

        # Check if already done — if so, recover state for downstream steps
        if db.is_completed(item):
            prior_output = db.get_step_output(run_id, file_id, arm.value, step_name)
            if step_name == "review_r1":
                if prior_output:
                    parse_result = parse_review_response(prior_output)
                    r1_review = parse_result.review
                    r1_findings_text = _format_findings(r1_review)
            elif step_name in ("review_r2", "review_r2_with_notes"):
                if prior_output:
                    parse_result = parse_review_response(prior_output)
                    r2_review = parse_result.review
                    r2_findings_text = _format_findings(r2_review)
            elif step_name in ("execute", "execute_r1", "execute_r2"):
                corrected_code = prior_output
            elif step_name == "synthesize":
                merged_findings = prior_output
            continue

        any_work_done = True

        # --- Execute the step ---

        if step_type == "review" and step_name == "review_r1":
            r1_review = _do_review(
                item=item,
                system_prompt=R1_SYSTEM_PROMPT,
                code_content=code_content,
                file_name=file_name,
                corpus=corpus,
                client=client,
                db=db,
            )
            if r1_review is None:
                return True  # parse failure — stop this file's pipeline
            r1_findings_text = _format_findings(r1_review)

        elif step_type == "review" and step_name == "review_r2":
            # Arm A: R2 reviews original code
            # Arm B: R2 reviews corrected code (after execute_r1)
            review_code = corrected_code if arm == Arm.SEQUENTIAL_FIX else code_content
            r2_review = _do_review(
                item=item,
                system_prompt=R2_SYSTEM_PROMPT,
                code_content=review_code,
                file_name=file_name,
                corpus=corpus,
                client=client,
                db=db,
            )
            if r2_review is None:
                return True
            r2_findings_text = _format_findings(r2_review)

        elif step_type == "review" and step_name == "review_r2_with_notes":
            # Arm C: R2 reviews original code with R1's findings attached
            augmented_prompt = (
                R2_WITH_NOTES_SYSTEM_PROMPT
                + f"\n\n## Prior Reviewer's Findings\n{r1_findings_text}"
            )
            r2_review = _do_review(
                item=item,
                system_prompt=augmented_prompt,
                code_content=code_content,
                file_name=file_name,
                corpus=corpus,
                client=client,
                db=db,
            )
            if r2_review is None:
                return True
            r2_findings_text = _format_findings(r2_review)

        elif step_type == "synthesize":
            if r1_findings_text is None or r2_findings_text is None:
                raise RuntimeError(
                    f"Cannot synthesize without both R1 and R2 findings "
                    f"(file={file_id}, arm={arm.value})"
                )
            merged_findings = _do_synthesize(
                item=item,
                r1_findings=r1_findings_text,
                r2_findings=r2_findings_text,
                client=client,
                db=db,
            )

        elif step_type == "execute":
            # Determine which findings and code to apply
            if step_name == "execute_r1":
                exec_findings = r1_findings_text
                exec_code = code_content
            elif step_name == "execute_r2":
                exec_findings = r2_findings_text
                exec_code = corrected_code  # apply to intermediate artifact
            elif arm == Arm.PARALLEL:
                exec_findings = merged_findings
                exec_code = code_content
            elif arm == Arm.SEQUENTIAL_NO_FIX:
                # Combine R1 + R2 findings
                combined = {"note": "Combined findings from R1 and R2"}
                exec_findings = (
                    f"## Reviewer 1 Findings\n{r1_findings_text}\n\n"
                    f"## Reviewer 2 Additional Findings\n{r2_findings_text}"
                )
                exec_code = code_content
            else:
                raise RuntimeError(f"Unexpected execute step: {step_name} for arm {arm.value}")

            if exec_findings is None or exec_code is None:
                raise RuntimeError(
                    f"Missing inputs for execute step {step_name} "
                    f"(file={file_id}, arm={arm.value})"
                )

            corrected_code = _do_execute(
                item=item,
                code_content=exec_code,
                findings_text=exec_findings,
                client=client,
                db=db,
            )

    return any_work_done
