"""Persona experiment pipeline — single-pass review for each (file, arm) pair."""

from __future__ import annotations

import json
import uuid

from ..client import ExperimentClient
from ..corpus import Corpus
from ..schemas import FileScore, ScoredFinding, WorkItem, WorkItemStatus
from ..scorer import Scorer
from ..storage import ExperimentDB


def run_persona_review(
    item: WorkItem,
    system_prompt: str,
    corpus: Corpus,
    client: ExperimentClient,
    scorer: Scorer,
    db: ExperimentDB,
) -> tuple[list[ScoredFinding], FileScore] | None:
    """Run a single persona review: one API call, score, store.

    Returns None if already checkpointed. Otherwise returns scored findings.
    """
    # Check if already done
    if db.is_completed(item):
        return None

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

    # Handle parse failure
    if review_output.parse_status == "parse_failed":
        # Retry once with nudge
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

        if review_output_retry.parse_status == "ok":
            review_output = review_output_retry
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
            return None

    # Score findings
    scored_findings, file_score = scorer.score_findings(
        findings=review_output.findings,
        file_id=item.file_id,
        arm=item.arm,
        run_id=item.run_id,
    )

    # Store atomically
    findings_json = json.dumps(
        [f.model_dump() for f in review_output.findings]
    )
    db.record_review(
        item=item,
        api_record=api_record,
        review_id=str(uuid.uuid4()),
        findings_json=findings_json,
        parse_status="ok",
        scored_findings=scored_findings,
        file_score=file_score,
    )

    return scored_findings, file_score
