"""Anthropic API client wrapper with retry, cost tracking, and response parsing."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone

import anthropic

from .schemas import APICallRecord, ReviewFinding, ReviewOutput

# Pricing per million tokens (as of 2026-03 for Sonnet)
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
}
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}

# JSON schema for structured review output — included in all review prompts
REVIEW_OUTPUT_SCHEMA = """\
Respond with a JSON object containing your findings. Use this exact schema:
```json
{
  "findings": [
    {
      "file": "<filename>",
      "line_start": <int>,
      "line_end": <int>,
      "severity": "critical|major|minor",
      "category": "security|logic|performance|error_handling|architecture|integration",
      "finding": "<description of the issue>",
      "suggested_fix": "<how to fix it>"
    }
  ]
}
```
If you find no issues, return `{"findings": []}`.
Return ONLY the JSON object, no other text."""


class ExperimentClient:
    """Wrapper around the Anthropic SDK for controlled experiment API calls."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        self._client = anthropic.Anthropic()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def review(
        self,
        system_prompt: str,
        code_content: str,
        file_name: str,
        *,
        experiment: str,
        arm: str,
        run_id: str,
        file_id: str,
        step: str = "review",
    ) -> tuple[ReviewOutput, APICallRecord]:
        """Send code for review and return parsed output + API call record.

        The system_prompt should contain the reviewer persona.
        The code_content is presented as a user message.
        The REVIEW_OUTPUT_SCHEMA is appended to the user message.
        """
        user_message = (
            f"Review the following code file (`{file_name}`):\n\n"
            f"```\n{code_content}\n```\n\n"
            f"{REVIEW_OUTPUT_SCHEMA}"
        )

        raw_response, api_record = self._call(
            system_prompt=system_prompt,
            user_message=user_message,
            experiment=experiment,
            arm=arm,
            run_id=run_id,
            file_id=file_id,
            step=step,
        )

        review_output = self._parse_review_response(raw_response)
        return review_output, api_record

    def execute(
        self,
        code_content: str,
        findings_text: str,
        *,
        experiment: str,
        arm: str,
        run_id: str,
        file_id: str,
        step: str = "execute",
    ) -> tuple[str, APICallRecord]:
        """Apply review findings to code and return corrected code + API record."""
        system_prompt = (
            "You are a code executor. Apply the review findings to the code. "
            "Make minimal changes to resolve each issue. "
            "Return ONLY the corrected code, no explanations."
        )
        user_message = (
            f"## Code\n```\n{code_content}\n```\n\n"
            f"## Review Findings\n{findings_text}\n\n"
            "Apply all findings. Return only the corrected code in a code fence."
        )

        raw_response, api_record = self._call(
            system_prompt=system_prompt,
            user_message=user_message,
            experiment=experiment,
            arm=arm,
            run_id=run_id,
            file_id=file_id,
            step=step,
        )

        # Extract code from response
        corrected = self._extract_code_block(raw_response) or raw_response
        return corrected, api_record

    def synthesize(
        self,
        r1_findings: str,
        r2_findings: str,
        *,
        experiment: str,
        arm: str,
        run_id: str,
        file_id: str,
    ) -> tuple[str, APICallRecord]:
        """Merge two independent review outputs (Arm A synthesis step)."""
        system_prompt = (
            "You are a review synthesis agent. You receive findings from two independent "
            "code reviewers. Your job is to:\n"
            "1. Deduplicate findings that describe the same issue\n"
            "2. Resolve any conflicting recommendations\n"
            "3. Produce a unified, prioritized findings list\n\n"
            "Return the merged findings as a JSON array in the same schema as the inputs."
        )
        user_message = (
            f"## Reviewer 1 Findings\n{r1_findings}\n\n"
            f"## Reviewer 2 Findings\n{r2_findings}\n\n"
            "Merge these into a single deduplicated findings list. "
            "Return ONLY the JSON object with a 'findings' array."
        )

        raw_response, api_record = self._call(
            system_prompt=system_prompt,
            user_message=user_message,
            experiment=experiment,
            arm=arm,
            run_id=run_id,
            file_id=file_id,
            step="synthesize",
        )

        return raw_response, api_record

    def judge_match(
        self,
        defect_description: str,
        finding_description: str,
    ) -> bool:
        """Use Haiku to judge whether a finding matches a manifest defect."""
        system_prompt = (
            "You are a matching judge. Determine whether a code review finding "
            "describes the same issue as a known defect. Respond with ONLY 'yes' or 'no'."
        )
        user_message = (
            f"Known defect: {defect_description}\n\n"
            f"Review finding: {finding_description}\n\n"
            "Does the review finding describe the same issue as the known defect? "
            "Answer ONLY 'yes' or 'no'."
        )

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        answer = response.content[0].text.strip().lower()
        return answer.startswith("yes")

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _call(
        self,
        system_prompt: str,
        user_message: str,
        experiment: str,
        arm: str,
        run_id: str,
        file_id: str,
        step: str,
        retries: int = 3,
    ) -> tuple[str, APICallRecord]:
        """Make an API call with retry and return raw text + record."""
        prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()[:16]
        call_id = str(uuid.uuid4())

        last_error = None
        for attempt in range(retries):
            try:
                start = time.monotonic()
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                duration = time.monotonic() - start

                raw_text = response.content[0].text
                pricing = PRICING.get(self.model, DEFAULT_PRICING)
                cost = (
                    response.usage.input_tokens * pricing["input"]
                    + response.usage.output_tokens * pricing["output"]
                ) / 1_000_000

                record = APICallRecord(
                    call_id=call_id,
                    experiment=experiment,
                    arm=arm,
                    run_id=run_id,
                    file_id=file_id,
                    step=step,
                    model=self.model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    cost_usd=cost,
                    duration_seconds=duration,
                    system_prompt_hash=prompt_hash,
                    timestamp=datetime.now(timezone.utc),
                )
                return raw_text, record

            except anthropic.RateLimitError:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                last_error = "rate_limit"
            except anthropic.APIError as e:
                if attempt < retries - 1:
                    time.sleep(2)
                    last_error = str(e)
                else:
                    raise

        raise RuntimeError(f"API call failed after {retries} retries: {last_error}")

    def _parse_review_response(self, raw: str) -> ReviewOutput:
        """Parse a review response into structured ReviewOutput."""
        json_str = self._extract_json(raw)
        if json_str is None:
            # Retry nudge would happen at the caller level
            return ReviewOutput(findings=[], raw_response=raw, parse_status="parse_failed")

        try:
            data = json.loads(json_str)
            findings = [ReviewFinding(**f) for f in data.get("findings", [])]
            return ReviewOutput(findings=findings, raw_response=raw, parse_status="ok")
        except (json.JSONDecodeError, TypeError, KeyError):
            return ReviewOutput(findings=[], raw_response=raw, parse_status="parse_failed")

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """Extract JSON from text, handling markdown code fences."""
        # Try JSON in code fence first
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try bare JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0).strip()

        return None

    @staticmethod
    def _extract_code_block(text: str) -> str | None:
        """Extract code from a markdown code fence."""
        match = re.search(r"```(?:\w+)?\s*\n(.*?)\n```", text, re.DOTALL)
        return match.group(1) if match else None
