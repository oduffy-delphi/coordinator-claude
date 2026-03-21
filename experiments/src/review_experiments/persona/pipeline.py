"""Persona experiment pipeline — single-pass review for each (file, arm) pair.

Uses shared infrastructure (client, parser, scorer, storage) with
persona-specific prompt building and configuration.
"""

from __future__ import annotations

import json
import uuid

from ..client import ExperimentClient
from ..corpus import Corpus
from ..parser import parse_review_response
from ..schemas import FileScore, WorkItem, WorkItemStatus
from ..scorer import score_review
from ..storage import ExperimentDB


def run_persona_review(
    item: WorkItem,
    system_prompt: str,
    corpus: Corpus,
    client: ExperimentClient,
    db: ExperimentDB,
) -> bool:
    """Run a single persona review: one API call, parse, score, store.

    Returns True if review was executed, False if already checkpointed.
    """
    # Check if already done
    if db.is_completed(item):
        return False

    # Read the code file
    code_content = corpus.read_file(item.file_id)
    file_name = corpus.file_name(item.file_id)

    # Call the API
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

    # Parse with the shared parser (handles JSON extraction + repair)
    parse_result = parse_review_response(review_output.raw_response)

    # Handle parse failure — retry once with nudge
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
        else:
            # Double failure — record as parse_failed
            db.record_review(
                item=item,
                api_record=api_record,
                review_id=str(uuid.uuid4()),
                findings_json="[]",
                parse_status="parse_failed",
                scored_findings=[],
                file_score=FileScore(
                    file=file_name, arm=item.arm, run_id=item.run_id
                ),
                checkpoint_status=WorkItemStatus.PARSE_FAILED,
            )
            return True

    # Score findings using the shared bipartite scorer
    scored = score_review(
        review=parse_result.review,
        file_stem=item.file_id,
        arm=item.arm,
        run_index=int(item.run_id.split("_")[-1]) if "_" in item.run_id else 0,
        defect_manifest=corpus.defect_manifest,
        distractor_manifest=corpus.distractor_manifest,
    )

    # Build FileScore from ScoredReview
    import math
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

    # Store atomically
    findings_json = json.dumps(
        [f.model_dump() for f in parse_result.review.findings]
    )
    db.record_review(
        item=item,
        api_record=api_record,
        review_id=str(uuid.uuid4()),
        findings_json=findings_json,
        parse_status="ok",
        scored_findings=scored.scored_findings,
        file_score=file_score,
    )

    return True
