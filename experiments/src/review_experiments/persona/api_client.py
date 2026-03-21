"""Thin async wrapper around the Anthropic SDK.

Each call creates a fresh messages.create() — no conversation state.
Handles 429/500/529 retries with exponential backoff.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass

import anthropic

from ..schemas import APICallRecord
from .config import EXPERIMENT_ID, MAX_TOKENS, MODEL, TEMPERATURE


@dataclass
class APIResponse:
    """Raw response from a single API call with metadata."""

    text: str
    input_tokens: int
    output_tokens: int
    duration_seconds: float
    call_record: APICallRecord


# Status codes that trigger retry
_RETRYABLE_STATUS_CODES = {429, 500, 529}
_MAX_RETRIES = 5
_BASE_DELAY = 2.0  # seconds


class ReviewClient:
    """Async client for making review API calls."""

    def __init__(
        self,
        model: str = MODEL,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
    ) -> None:
        self._client = anthropic.AsyncAnthropic()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def review(
        self,
        system_prompt: str,
        user_message: str,
        *,
        arm: str,
        run_id: str,
        file_id: str,
    ) -> APIResponse:
        """Send a single review request and return the response.

        Each call is a fresh session — no prior context.
        Retries on 429/500/529 with exponential backoff.
        """
        system_hash = hashlib.sha256(system_prompt.encode()).hexdigest()
        start = time.monotonic()

        response = await self._call_with_retry(system_prompt, user_message)

        duration = time.monotonic() - start
        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Approximate cost (Opus pricing: $15/M input, $75/M output)
        cost = (input_tokens * 15 + output_tokens * 75) / 1_000_000

        call_record = APICallRecord(
            call_id=str(uuid.uuid4()),
            experiment=EXPERIMENT_ID,
            arm=arm,
            run_id=run_id,
            file_id=file_id,
            step="review",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            duration_seconds=duration,
            system_prompt_hash=system_hash,
            timestamp=response.created_at if hasattr(response, "created_at") else None,
        )

        return APIResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_seconds=duration,
            call_record=call_record,
        )

    async def _call_with_retry(
        self, system_prompt: str, user_message: str
    ) -> anthropic.types.Message:
        """Make the API call with exponential backoff on retryable errors."""
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                return await self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
            except anthropic.APIStatusError as e:
                last_error = e
                if e.status_code not in _RETRYABLE_STATUS_CODES:
                    raise

                # Use Retry-After header if available
                retry_after = None
                if hasattr(e, "response") and e.response is not None:
                    retry_after_str = e.response.headers.get("retry-after")
                    if retry_after_str:
                        try:
                            retry_after = float(retry_after_str)
                        except ValueError:
                            pass

                delay = retry_after or (_BASE_DELAY * (2**attempt))
                await asyncio.sleep(delay)

        raise last_error  # type: ignore[misc]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()
