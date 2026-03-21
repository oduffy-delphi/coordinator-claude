# Specialist Review Experiment — Implementation & Operations

## Context

We're measuring whether dispatching a richly-described specialist reviewer (Patrik) produces measurably better code review output than dispatching a generic reviewer. This tests the production Claude Code pattern — EM dispatches a specialist subagent — not isolated API calls.

**Research grounding** (`docs/research/2026-03-19-named-persona-performance.md`):
- A-HMAD specialized roles: **4-6% accuracy gains, 30%+ error reduction**
- Persona vectors are causally real (Anthropic research) — rich behavioral descriptions steer model activations
- The active ingredient is **description richness and coverage specialization**, not naming

**Expected effect:** ~4-7pp improvement in defect detection rate. The pilot suggests the actual range will depend heavily on file complexity — simpler files may show ceiling effects.

## Experimental Design (Final)

### Arms

| Arm | Prompt file | Description |
|-----|------------|-------------|
| **BASELINE** | `arm_baseline.md` | "Review this code for bugs and issues." + shared output format |
| **SPECIALIST** | `arm_specialist.md` | Full Patrik prompt (3rd person, rich description, review standards, adversarial framing) + shared output format |

### Execution

Reviews run via **Claude Code agent spawning** (`claude --print --no-session-persistence --model sonnet --system-prompt "..." "user message"`). Each review is a fresh subprocess — no conversation state between calls.

**Key parameters:**
- Model: `sonnet` (alias resolves to same checkpoint within a calendar day)
- Timeout: 600s per call (increased from 300s after pilot showed 10% timeout rate)
- No `--bare` flag (requires OAuth for Claude Code Max subscription)
- Claude Code system context (CLAUDE.md, hooks) loads but affects both arms equally

### Corpus (Implemented)

**32 defects across 10 files, 15 distractors.**

| File | Lang | Lines | Defects | Density | Categories |
|------|------|-------|---------|---------|------------|
| config_loader.py | Python | 120 | 0 | Clean | FP measurement |
| auth_middleware.ts | TS | 190 | 2 | Sparse | Security |
| cache_manager.py | Python | 183 | 4 | Moderate | Logic/concurrency |
| data_pipeline.ts | TS | 226 | 3 | Moderate | Logic/error handling |
| task_scheduler.py | Python | 215 | 7 | Dense | Logic/error handling |
| payment_processor.py | Python | 189 | 4 | Moderate | Security/logic |
| websocket_handler.ts | TS | 251 | 3 | Moderate | Performance/logic |
| user_service.py | Python | 248 | 3 | Moderate | Security |
| event_emitter.ts | TS | 241 | 3 | Moderate | Logic/performance |
| file_processor.py | Python | 231 | 3 | Moderate | Security/error handling |

**Difficulty distribution:** 8 obvious (25%) / 13 moderate (41%) / 11 subtle (34%)
**Category distribution:** security 7, logic 16, performance 2, error_handling 7

### Statistical Design

**Primary:** GLMM with binomial family: `defect_detected ~ arm + (1 | file) + (1 | defect_id)`
**N:** 30 runs per arm × 32 defects = 960 observations per arm
**Supplementary:** Interaction models with difficulty and category

### Scoring

Deterministic bipartite matching (no LLM-as-judge):
1. Line proximity + keyword matching → match score (threshold ≥ 0.4)
2. `scipy.optimize.linear_sum_assignment` for optimal finding→defect assignment
3. Unmatched findings classified as FP_distractor, FP_novel, or valid_unexpected

## Architecture (Post-Reconciliation)

The codebase went through a module reconciliation that consolidated persona-specific duplicates into the shared parent package. The current structure:

```
experiments/
  scripts/
    run_persona_experiment.py        # ← PRIMARY ENTRY POINT for running experiment
  corpus/persona_review/
    manifests/{defects,distractors}.yaml
    files/*.{py,ts}                  # 10 corpus files
  prompts/persona_review/
    shared_output_format.md
    arm_baseline.md
    arm_specialist.md
  src/review_experiments/
    __init__.py                      # Shared package exports
    schemas.py                       # Pydantic models (all experiments)
    parser.py                        # JSON extraction with repair fallback
    scorer.py                        # Bipartite matcher
    storage.py                       # SQLite persistence
    client.py                        # Anthropic SDK client (for API-mode runs)
    corpus.py                        # Corpus loading and validation
    cli.py                           # Unified CLI (persona + sequential experiments)
    persona/
      __init__.py
      config.py                      # Arm enum (BASELINE/SPECIALIST), paths
      prompt_builder.py              # System + user message assembly
      agent_client.py                # Claude Code subprocess dispatch
      pipeline.py                    # Single-review pipeline (API-mode)
  results/                           # .gitignored — JSON-per-call outputs
    runs/{experiment_id}/{arm}/{file_stem}/run_{n}.json
  tests/                             # 28 tests passing
```

**Two execution modes exist:**
1. **Agent spawning** (via `scripts/run_persona_experiment.py`): Uses `agent_client.py` → `claude --print` subprocess. This is what we use — ecological validity.
2. **API mode** (via `cli.py persona run`): Uses `client.py` → `anthropic.Anthropic()`. Available for comparison but not the primary path.

## How to Run the Experiment

### Check progress
```bash
cd experiments
uv run python scripts/run_persona_experiment.py --status
```

### Run a batch (chunkable — resumes automatically)
```bash
# ~30 minutes (about 9 calls)
uv run python scripts/run_persona_experiment.py --max-calls 9

# ~70 minutes (about 20 calls)
uv run python scripts/run_persona_experiment.py --max-calls 20

# Let it run until done (no limit)
uv run python scripts/run_persona_experiment.py
```

### Run the pilot (fills gaps from initial pilot)
```bash
uv run python scripts/run_persona_experiment.py --pilot --max-calls 5
```

### Full experiment parameters (default)
- 30 runs × 2 arms × 10 files = **600 calls**
- At ~3.5 min/call = ~35 hours total
- Designed to be spread across multiple sessions via `--max-calls`

## Pilot Results (Phase 4 — Completed)

**27/30 calls completed** (3 timeouts at 300s), 1 parse failure (3.7%).

### Detection Rates (SPECIALIST arm only)

**payment_processor.py** (4 defects, 9 successful runs):
| Defect | Difficulty | Detection Rate |
|--------|-----------|---------------|
| payment_refund_zero_falsy | subtle | 100% (9/9) |
| payment_capture_toctou | moderate | 89% (8/9) |
| payment_webhook_decode_before_verify | moderate | 89% (8/9) |
| payment_refund_log_pii | obvious | 67% (6/9) |
| **Overall** | | **86%** |

**task_scheduler.py** (7 defects, 8 successful runs):
| Defect | Difficulty | Detection Rate |
|--------|-----------|---------------|
| scheduler_dependency_validation | obvious | 75% (6/8) |
| scheduler_no_cancel_support | moderate | 62% (5/8) |
| scheduler_heapq_unstable | subtle | 38% (3/8) |
| scheduler_summary_missing_pending | obvious | 38% (3/8) |
| scheduler_retry_off_by_one | moderate | 12% (1/8) |
| scheduler_deadlock_remaining_stale | subtle | 12% (1/8) |
| scheduler_result_not_awaited | moderate | 12% (1/8) |
| **Overall** | | **36%** |

### Pilot Findings

1. **Dynamic range is good** — 86% vs 36% across files means the corpus has room for both ceiling and floor effects
2. **Timeout must be ≥600s** — 300s caused 10% failure rate
3. **Parse success is high** — 96% with the shared output format
4. **LLM difficulty ≠ human difficulty** — `Decimal(0)` falsy bug (rated "subtle") was caught 100% of the time; complex async logic bugs (rated "moderate") were caught 12%. Training data representation matters more than conceptual difficulty.
5. **Finding counts are stable** — config_loader: 8-10/run, payment_processor: 11-17/run, task_scheduler: 0-14/run

### Methodology Verdict
The methodology is validated. Detection rates provide meaningful dynamic range for measuring a BASELINE vs SPECIALIST treatment effect. No changes to corpus or protocol needed for the full run.

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Simplify to 2 arms | ✅ Done | BASELINE + SPECIALIST, 3rd-person prompt |
| 2. Agent-spawning runner | ✅ Done | `agent_client.py` + standalone script |
| 3. Expand corpus | ✅ Done | 32 defects, 15 distractors, 10 files |
| 4. Determinism pilot | ✅ Done | 27/30 calls, methodology validated |
| 5. Full experiment | 🔄 In progress | 4/600 calls completed. Resume via `--max-calls` batches |
| 6. Analysis pipeline | Not started | descriptive + GLMM + report |

## Decision Table (for interpreting results)

| Result | Implication |
|--------|------------|
| SPECIALIST >> BASELINE (≥5pp) | Rich specialist descriptions are worth the investment. Continue enriching persona prompts. |
| SPECIALIST > BASELINE (2-4pp) | Modest advantage — worth keeping for high-stakes review, maybe not for routine checks. |
| SPECIALIST ≈ BASELINE (<2pp) | Description richness doesn't help in Claude Code context. Simplify reviewer dispatch. |
| SPECIALIST < BASELINE | Specialist prompt is actively harmful (narrowing attention too much). Investigate. |
| Effect concentrates on moderate-difficulty | Specialist attention direction works as predicted. |
| Effect concentrates on Patrik's stated categories | Coverage specialization confirmed. |
