"""Configuration for the persona review experiment.

2-arm design: BASELINE (generic reviewer) vs SPECIALIST (richly-described
Patrik persona). Execution via Claude Code agent spawning — no direct API
access, so no temperature/model/max_tokens controls.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Experiment identity
# ---------------------------------------------------------------------------

EXPERIMENT_ID = "persona_review_v1"

# ---------------------------------------------------------------------------
# Arms — the 2 experimental conditions
# ---------------------------------------------------------------------------


class Arm(str, Enum):
    """Experimental conditions for the specialist review experiment.

    BASELINE:   Generic reviewer — no behavioral description, no focus areas.
    SPECIALIST: Full production Patrik prompt — rich description, stated focus
                areas, review standards, adversarial framing.

    The shared output format (JSON schema + coverage declaration) is identical
    across both arms.
    """

    BASELINE = "BASELINE"
    SPECIALIST = "SPECIALIST"


# ---------------------------------------------------------------------------
# Paths (relative to experiments/ directory)
# ---------------------------------------------------------------------------

EXPERIMENTS_ROOT = Path(__file__).resolve().parents[3]  # experiments/

PROMPTS_DIR = EXPERIMENTS_ROOT / "prompts" / "persona_review"
CORPUS_DIR = EXPERIMENTS_ROOT / "corpus" / "persona_review"
RESULTS_DIR = EXPERIMENTS_ROOT / "results"

DEFECTS_MANIFEST = CORPUS_DIR / "manifests" / "defects.yaml"
DISTRACTORS_MANIFEST = CORPUS_DIR / "manifests" / "distractors.yaml"
ADJUDICATIONS_MANIFEST = CORPUS_DIR / "manifests" / "adjudications.yaml"

# Prompt file names per arm
ARM_PROMPT_FILES: dict[Arm, str] = {
    Arm.BASELINE: "arm_baseline.md",
    Arm.SPECIALIST: "arm_specialist.md",
}

SHARED_OUTPUT_FORMAT = "shared_output_format.md"

# ---------------------------------------------------------------------------
# Runner defaults
# ---------------------------------------------------------------------------

PILOT_RUNS = 10
PILOT_ARM = Arm.SPECIALIST
