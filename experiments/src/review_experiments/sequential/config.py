"""Configuration for the sequential vs parallel review experiment.

3-arm design testing whether sequential review with fix gates (our architecture)
outperforms the industry-standard parallel+aggregate approach.

Arm A: Parallel + aggregate (R1 ‖ R2 → synthesize → execute)
Arm B: Sequential + fix gates (R1 → execute → R2 → execute)
Arm C: Sequential, no fix gates (R1 → R2 with R1's notes → execute)
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Experiment identity
# ---------------------------------------------------------------------------

EXPERIMENT_ID = "sequential_review_v1"

# ---------------------------------------------------------------------------
# Arms — the 3 experimental conditions
# ---------------------------------------------------------------------------


class Arm(str, Enum):
    """Experimental conditions for the sequential review experiment."""

    PARALLEL = "PARALLEL"
    SEQUENTIAL_FIX = "SEQUENTIAL_FIX"
    SEQUENTIAL_NO_FIX = "SEQUENTIAL_NO_FIX"


# Step sequences per arm — defines the pipeline structure.
# Each step is a (step_name, step_type) pair where step_type determines
# which pipeline function handles it.
ARM_STEPS: dict[Arm, list[tuple[str, str]]] = {
    Arm.PARALLEL: [
        ("review_r1", "review"),
        ("review_r2", "review"),
        ("synthesize", "synthesize"),
        ("execute", "execute"),
    ],
    Arm.SEQUENTIAL_FIX: [
        ("review_r1", "review"),
        ("execute_r1", "execute"),
        ("review_r2", "review"),
        ("execute_r2", "execute"),
    ],
    Arm.SEQUENTIAL_NO_FIX: [
        ("review_r1", "review"),
        ("review_r2_with_notes", "review"),
        ("execute", "execute"),
    ],
}

# ---------------------------------------------------------------------------
# Reviewer roles
# ---------------------------------------------------------------------------

REVIEWER_1_ROLE = "domain"  # Security + logic emphasis
REVIEWER_2_ROLE = "generalist"  # Broad coverage

# ---------------------------------------------------------------------------
# Paths (relative to experiments/ directory)
# ---------------------------------------------------------------------------

EXPERIMENTS_ROOT = Path(__file__).resolve().parents[3]  # experiments/

PROMPTS_DIR = EXPERIMENTS_ROOT / "prompts" / "sequential_review"
CORPUS_DIR = EXPERIMENTS_ROOT / "corpus" / "sequential_review"
RESULTS_DIR = EXPERIMENTS_ROOT / "results"

DEFECTS_MANIFEST = CORPUS_DIR / "manifests" / "defects.yaml"
DISTRACTORS_MANIFEST = CORPUS_DIR / "manifests" / "distractors.yaml"
