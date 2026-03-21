"""Claude Code agent-spawning client for the review experiment.

Each review dispatches a fresh Claude Code session via `claude --print`.
No conversation state between calls. No temperature or token-count control —
this is the ecological validity trade-off for testing in the production
environment.
"""

from __future__ import annotations

import hashlib
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from ..schemas import APICallRecord
from .config import EXPERIMENT_ID


@dataclass
class AgentResponse:
    """Response from a single Claude Code agent dispatch."""

    text: str
    duration_seconds: float
    call_record: APICallRecord


# Agent spawning defaults
DEFAULT_MODEL = "sonnet"
DEFAULT_TIMEOUT = 600  # 10 minutes per review (300s caused ~10% timeout rate in pilot)


class ReviewClient:
    """Client that dispatches reviews via Claude Code agent spawning."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.model = model
        self.timeout = timeout

    def review(
        self,
        system_prompt: str,
        user_message: str,
        *,
        arm: str,
        run_id: str,
        file_id: str,
    ) -> AgentResponse:
        """Dispatch a single review via Claude Code and return the response.

        Each call spawns a fresh `claude --print` process with:
        - --no-session-persistence: don't save to session history
        - --system-prompt: the arm-specific prompt + shared output format
        - --model: the model alias (same checkpoint within a calendar day)

        Note: --bare is NOT used because it skips OAuth auth (we use Claude
        Code Max subscription). Claude Code system context (CLAUDE.md, hooks)
        is loaded but affects both arms equally — a systematic bias, not a
        differential one.

        The user message (code to review) is passed as the positional prompt arg.
        """
        system_hash = hashlib.sha256(system_prompt.encode()).hexdigest()
        start = time.monotonic()

        cmd = [
            "claude",
            "--print",
            "--no-session-persistence",
            "--model", self.model,
            "--system-prompt", system_prompt,
            user_message,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        duration = time.monotonic() - start

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Claude Code exited with code {result.returncode}: {stderr}"
            )

        text = result.stdout

        call_record = APICallRecord(
            call_id=str(uuid.uuid4()),
            experiment=EXPERIMENT_ID,
            arm=arm,
            run_id=run_id,
            file_id=file_id,
            step="review",
            model=self.model,
            # Agent spawning doesn't expose token counts or cost
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            duration_seconds=duration,
            system_prompt_hash=system_hash,
            timestamp=datetime.now(timezone.utc),
        )

        return AgentResponse(
            text=text,
            duration_seconds=duration,
            call_record=call_record,
        )
