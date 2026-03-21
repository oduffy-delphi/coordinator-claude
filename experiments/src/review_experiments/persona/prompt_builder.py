"""Assemble system + user messages per arm for the persona review experiment.

The system message is: arm-specific prompt + shared output format.
The user message is: the code file with a review instruction.
"""

from __future__ import annotations

from pathlib import Path

from .config import ARM_PROMPT_FILES, PROMPTS_DIR, SHARED_OUTPUT_FORMAT, Arm


def _load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts directory."""
    path = PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt(arm: Arm) -> str:
    """Build the full system prompt for a given arm.

    Concatenates the arm-specific prompt with the shared output format.
    The output format is identical across all arms — this is a design invariant.
    """
    arm_prompt = _load_prompt_file(ARM_PROMPT_FILES[arm])
    output_format = _load_prompt_file(SHARED_OUTPUT_FORMAT)
    return f"{arm_prompt}\n\n{output_format}"


def build_user_message(code_file: Path) -> str:
    """Build the user message containing the code to review.

    The instruction is deliberately minimal and identical across arms —
    all behavioral variation comes from the system prompt.
    """
    code_content = code_file.read_text(encoding="utf-8")
    filename = code_file.name
    return (
        f"Review this code. Report all issues you find, "
        f"with file location, severity, and explanation.\n\n"
        f"**File: `{filename}`**\n\n"
        f"```\n{code_content}\n```"
    )


def get_all_system_prompts() -> dict[Arm, str]:
    """Build system prompts for all arms. Useful for verification."""
    return {arm: build_system_prompt(arm) for arm in Arm}
