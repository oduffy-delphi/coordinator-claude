"""Configuration for the persona review experiment."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Experiment identity
# ---------------------------------------------------------------------------

EXPERIMENT_ID = "persona_review_v1"

# ---------------------------------------------------------------------------
# Arms — the 5 experimental conditions
# ---------------------------------------------------------------------------


class Arm(str, Enum):
    """Experimental conditions forming a 2×2 factorial + baseline.

    The 2×2 factorial crosses naming (unnamed/named) × framing (1p/3p):
        |           | 1st person | 3rd person |
        |-----------|------------|------------|
        | Unnamed   | B          | B_PRIME    |
        | Named     | D          | C          |

    Arm A is the external baseline (vanilla, no persona description).
    """

    A = "A"              # Vanilla — minimal instruction
    B = "B"              # Rich description, unnamed, 1st person
    B_PRIME = "B_PRIME"  # Rich description, unnamed, 3rd person
    C = "C"              # Rich description, named (Patrik), 3rd person
    D = "D"              # Rich description, named (Patrik), 1st person — production


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

# Pinned to exact dated ID — aliases may resolve to different checkpoints.
MODEL = "claude-opus-4-6-20250115"
TEMPERATURE = 0
MAX_TOKENS = 4096

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
    Arm.A: "arm_a_vanilla.md",
    Arm.B: "arm_b_rich_unnamed_1p.md",
    Arm.B_PRIME: "arm_bp_rich_unnamed_3p.md",
    Arm.C: "arm_c_rich_named_3p.md",
    Arm.D: "arm_d_rich_named_1p.md",
}

SHARED_OUTPUT_FORMAT = "shared_output_format.md"

# ---------------------------------------------------------------------------
# Runner defaults
# ---------------------------------------------------------------------------

DEFAULT_CONCURRENCY = 10
PILOT_RUNS = 10
PILOT_ARM = Arm.D
