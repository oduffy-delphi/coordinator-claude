# Plan: Specialist Review Experiment Harness

## Context

We want to measure whether dispatching a richly-described specialist reviewer (Patrik) produces measurably better code review output than dispatching a generic reviewer. This tests the production Claude Code pattern — EM dispatches a specialist subagent — not isolated API calls.

**Research grounding** (`docs/research/2026-03-19-named-persona-performance.md`):
- Persona alone vs neutral: +0.91% (barely measurable — not the interesting comparison)
- A-HMAD specialized roles in ensemble: **4-6% accuracy gains, 30%+ error reduction**
- Jekyll & Hyde (persona + neutral, adjudicated): +9.98% ceiling with synthesis
- Persona vectors are causally real (Anthropic research) — rich behavioral descriptions genuinely steer model activations
- The active ingredient is **description richness and coverage specialization**, not naming

**Expected effect:** ~4-7pp improvement in defect detection rate for specialist vs generic reviewer. This is extrapolated from A-HMAD reasoning benchmarks; code review may show a larger effect (attention direction matters more) or smaller effect (base model already good at review). The pilot will provide an empirical estimate.

**What we're NOT testing:** Naming effects (names are for human cognitive convenience), framing effects (1st vs 3rd person), or persona-in-isolation performance. The original 5-arm 2×2 factorial is dropped in favor of a cleaner 2-arm comparison that matches how we actually use Claude Code.

## Experimental Design

### Arms

| Arm | Prompt | What it tests |
|-----|--------|---------------|
| **BASELINE** | "Review this code for bugs and issues." + shared output format | Generic reviewer — no behavioral description, no focus areas |
| **SPECIALIST** | Full production Patrik prompt (3rd person, rich description) + shared output format | Richly-described specialist with stated focus areas, review standards, adversarial framing |

The shared output format (JSON schema + coverage declaration) is identical across both arms. This ensures parseable, scoreable output regardless of treatment condition.

### Execution Environment

Reviews run via **Claude Code agent spawning** — each review is a subagent dispatch with a fresh context. This matches the production pattern (EM dispatches reviewer) and uses the existing Claude Code Max subscription.

Implications vs direct API access:
- **No temperature control** — Claude Code uses its default. This adds per-observation variance but makes the results ecologically valid for our actual usage.
- **No exact model pinning** — aliases, not dated IDs. **Mitigated by running all arms within a single calendar day** (alias resolves to the same checkpoint).
- **No token-count metadata** — can't track input/output tokens per call. Cost tracking is moot (subscription).
- **Agent context overhead** — each subagent receives some Claude Code system context beyond our experimental prompt. This is a systematic bias affecting both arms equally, so it does not confound the between-arm comparison. It does mean absolute detection rates are specific to the Claude Code context.

### Measurement Strategy

**Primary (Strategy 1): Measure raw reviewer output only.** The unit of observation is a per-defect binary detection outcome from the reviewer's findings. The EM integration step is not part of the measurement loop.

Rationale: EM integration is an amplifier/dampener of the reviewer's signal — it's unlikely to reverse the direction of the effect. Including it doubles the variance (two LLM calls) and doubles the cost. The existing scoring infrastructure is already built for raw reviewer output.

**Supplementary (Strategy 2, optional):** For a subset of runs (e.g., top-5 most interesting files, 10 runs each), run both arms through the full EM integration pipeline. Measure whether integration preserves, amplifies, or dampens the raw treatment effect. The EM integration prompt must be identical across both arms — only the reviewer dispatch changes.

### Corpus

**Target: 30+ defects across 8-10 files** (expanded from the current 5-file seed corpus with 16 defects). The defect count is the primary driver of statistical power — more defects increase generalizability, more runs increase precision on a fixed set.

- **Language:** TypeScript and Python (high training data representation)
- **File length:** 80-200 lines (realistic but context isn't the bottleneck)
- **Defect density:** Variable across files (clean, sparse, moderate, dense)
- **Defect difficulty distribution:** ~25% obvious, ~40% moderate, ~35% subtle. The treatment effect is expected to be strongest on moderate-difficulty defects (obvious are caught by everyone, subtle are missed by everyone).
- **Defect categories:** Security, logic, performance, error handling — distributed unevenly across files
- **Distractors:** Code that looks suspicious but is correct. No distractor within ±5 lines of a defect.

Manifests:
- `defects.yaml`: Every seeded defect with globally unique ID, file, line_range, category, severity, difficulty, keywords, description, correct_fix
- `distractors.yaml`: Every intentional distractor with file, line_range, description, explanation
- `adjudications.yaml`: Post-hoc reclassifications (created during analysis for valid unexpected findings)

### Statistical Design

**Primary analysis:** GLMM with binomial family.

```
defect_detected ~ arm + (1 | file) + (1 | defect_id)
```

- **Outcome:** Binary — did this arm detect this specific defect on this run? (1/0)
- **Fixed effect:** Arm (2 levels: BASELINE, SPECIALIST)
- **Random effects:** File (some files are inherently harder) and defect_id (some defects are inherently harder). Globally unique defect IDs mean nesting is unnecessary.
- **N = 30 runs per arm** (60 runs total). With 30+ defects, this gives ~900+ observations per arm. Simulation-based power estimate: ~80% power for a 5pp effect. The pilot will provide empirical variance estimates to confirm.

**Supplementary analyses:**
- `defect_detected ~ arm * difficulty + (1 | file) + (1 | defect_id)` — tests whether the specialist advantage concentrates on moderate-difficulty defects
- `defect_detected ~ arm * category + (1 | file) + (1 | defect_id)` — tests whether the specialist advantage concentrates on Patrik's stated focus areas (security, logic, performance)

**Implementation:** `statsmodels` GEE with binomial family as default. `pymer4` → R's `lme4::glmer` if R is available (gives random effect estimates; GEE gives population-average estimates). Both adequate.

### Controls

- **Fresh context per review** — each subagent dispatch is a clean session
- **Identical output format** — shared JSON schema across both arms
- **File order randomized per run** — controls for ordering effects (theoretically unnecessary with fresh sessions, but costs nothing)
- **All runs within one calendar day** — prevents model checkpoint drift
- **Interleave arms within runs** — don't batch all BASELINE then all SPECIALIST; run both arms on each file before moving to the next. This ensures any within-session API quality drift affects both arms equally.

### Scoring

Deterministic, no LLM-as-judge. Keyword + line proximity matching with optimal bipartite assignment:

1. **Match score:** `line_score * 0.6 + keyword_score * 0.4` (threshold ≥ 0.4)
2. **Bipartite assignment:** `scipy.optimize.linear_sum_assignment` for optimal finding→defect matching
3. **Classify unmatched:** Check against distractors, then classify remaining as novel FP
4. **Output:** Per-defect binary detection vector + per-finding 4-category classification (TP, FP_distractor, FP_novel, valid_unexpected)

### What to Watch For

- **Ceiling/floor effects:** If BASELINE already catches >80% of defects, the specialist can't show much improvement. If <30%, both arms are struggling. Target baseline detection rate: 45-70%. The pilot will reveal this — adjust corpus difficulty if needed.
- **Parse failure rates:** If one arm produces systematically more parse failures, that's informative. Track and report.
- **Valid unexpected findings:** Both arms may find genuine issues not in the manifest. These don't count against precision. Capture them in `adjudications.yaml` for corpus improvement.

## Directory Structure

```
experiments/
  pyproject.toml                      # Shared deps
  corpus/persona_review/
    manifests/
      defects.yaml                    # Seeded defect manifest (30+ defects)
      distractors.yaml                # Known non-issues manifest
      adjudications.yaml              # Post-hoc reclassifications (created during analysis)
    files/                            # 8-10 code files (ts and py)
  prompts/persona_review/
    shared_output_format.md           # Output format (identical across both arms)
    arm_baseline.md                   # Generic: "Review this code"
    arm_specialist.md                 # Production Patrik (3rd person, rich description)
  src/review_experiments/
    schemas.py                        # Pydantic models (shared across experiments)
    persona/
      config.py                       # Arms enum (BASELINE, SPECIALIST), paths
      prompt_builder.py               # Assembles system + user messages per arm
      runner.py                       # Agent-spawning orchestrator with progress tracking
      result_store.py                 # JSON-per-call persistence, crash-resumable
      parser.py                       # Extract ReviewOutput JSON from responses
      scorer.py                       # Bipartite matcher (line proximity + keywords)
      cli.py                          # Entry point: pilot / run / score / analyze
    analysis/
      descriptive.py                  # Per-arm recall/precision/F1 with CIs
      glmm.py                         # GLMM fitting + contrasts
      report.py                       # Markdown report with decision table
  results/                            # .gitignored — raw outputs + reports
```

## Implementation Phases

### Phase 1: Simplify to 2 Arms ✅ (partially done)
**What changes from current state:**
- `config.py`: Replace 5-arm enum with `BASELINE` / `SPECIALIST`
- Prompts: Keep `arm_a_vanilla.md` → rename to `arm_baseline.md`. Keep `arm_d_rich_named_1p.md` → revise to 3rd person, rename to `arm_specialist.md`. Delete arms B, B', C.
- `prompt_builder.py`: Update for 2 arms

**Existing infrastructure that carries forward unchanged:** schemas.py, result_store.py, parser.py, scorer.py, shared_output_format.md, pyproject.toml, .gitignore

### Phase 2: Agent-Spawning Runner
**Replace** the current Anthropic SDK runner with a Claude Code agent-spawning runner.

Each review becomes:
1. Build the system prompt (arm-specific prompt + shared output format)
2. Build the user message (code file + review instruction)
3. Dispatch a Claude Code subagent with the system prompt as its instruction and the user message as the task
4. Capture the subagent's response text
5. Parse the response and save to result store

Key design choices:
- **Sequential execution within a run** (not async/concurrent) — Claude Code agent spawning doesn't benefit from asyncio semaphores. Dispatch one agent at a time, or use Claude Code's native parallelism if available.
- **Crash-resumable** — check result_store.exists() before each dispatch
- **Progress tracking** — print progress after each call (tqdm or simple counter)

### Phase 3: Expand Corpus to 30+ Defects
Expand from the current 5-file seed corpus (16 defects, 9 distractors) to 8-10 files with 30+ defects and 15+ distractors.

**Difficulty targets:** ~8 obvious, ~12 moderate, ~10 subtle
**Category spread:** Security, logic, performance, error handling — not every file is a buffet

This is the creative work and the highest-value investment. The infrastructure is built; the corpus determines the experiment's power.

**Dependency:** Prompt content (Phase 1) should be finalized before corpus expansion. The specialist prompt reveals what Patrik emphasizes — this should inform distractor placement.

### Phase 4: Determinism Pilot
Run the pilot under agent-spawning conditions (not temp=0):
- 3 files × 10 calls × SPECIALIST arm only = 30 calls
- Measure: per-defect agreement rate, Fleiss's kappa, recall variance
- Estimate defect-level and file-level variance components
- Check baseline detection rate (target 45-70% — adjust corpus if outside range)
- Output: pilot report with empirical N recommendation

### Phase 5: Full Experiment Run
- 30 runs × 2 arms × 8-10 files = 480-600 calls
- All within a single calendar day
- Interleave arms within each run
- Save each result immediately (crash-resume)

### Phase 6: Analysis Pipeline
- `descriptive.py`: Per-arm recall, precision, F1 with bootstrap CIs. Breakdowns by difficulty and category.
- `glmm.py`: Fit primary model + supplementary interaction models. Report odds ratio with CI.
- `report.py`: Markdown report mapping results to the decision table.

**Decision table:**

| Result | Implication |
|--------|------------|
| SPECIALIST >> BASELINE (≥5pp) | Rich specialist descriptions are worth the investment. Continue enriching persona prompts. |
| SPECIALIST > BASELINE (2-4pp) | Modest advantage — worth keeping for high-stakes review, maybe not for routine checks. |
| SPECIALIST ≈ BASELINE (<2pp) | Description richness doesn't help in Claude Code context. Simplify reviewer dispatch. |
| SPECIALIST < BASELINE | Specialist prompt is actively harmful (possible if it narrows attention too much). Investigate and fix. |
| Effect concentrates on moderate-difficulty defects | Specialist attention direction works as predicted — helps most where it matters most. |
| Effect concentrates on Patrik's stated categories | Coverage specialization confirmed — personas direct attention to their focus areas. |

## Build Order

| Order | What | Enables | Effort |
|-------|------|---------|--------|
| 1 | Simplify to 2 arms (config, prompts) | Everything | Small |
| 2 | Agent-spawning runner | Running calls | Medium |
| 3 | Expand corpus (8-10 files, 30+ defects) | Statistical power | Large (creative) |
| 4 | Determinism pilot (30 calls) | Variance estimates, N confirmation | Small |
| 5 | Full experiment (480-600 calls) | Results | Small (execution) |
| 6 | Analysis pipeline (GLMM, report) | Interpretation | Medium |

Phases 1-2 adapt existing infrastructure. Phase 3 is the bottleneck. Phase 4 validates the methodology before the full investment. Phase 5 is execution. Phase 6 interprets.

## Verification

- **Phase 1:** Print assembled prompts for both arms. Confirm shared output format is byte-identical.
- **Phase 2:** Run 2 calls (1 per arm × 1 file). Verify agent spawning works, response is captured, parsed, and saved correctly.
- **Phase 3:** Validate expanded manifests — all defect IDs globally unique, no distractor within ±5 lines of defect, difficulty distribution matches targets. Score a synthetic review to verify matcher works on new corpus.
- **Phase 4:** Pilot output confirms variance characteristics, baseline detection rate in target range, and N estimate.
- **Phase 6:** Run analysis on pilot data. Verify GLMM fits and produces sensible odds ratio.

## What's Already Built

The existing infrastructure from the prior implementation covers most of the foundation:

- **schemas.py**: Pydantic models for defects, distractors, findings, scoring, API records ✅
- **result_store.py**: JSON-per-call persistence with crash-resume ✅
- **parser.py**: Extract ReviewOutput JSON with fallback chain ✅
- **scorer.py**: Bipartite matcher with line proximity + keywords ✅
- **prompt_builder.py**: Loads arm prompt + shared format (needs 2-arm update) ✅
- **Seed corpus**: 5 files, 16 defects, 9 distractors (needs expansion) ✅
- **Prompts**: Shared output format + arm-specific prompts (needs simplification) ✅
- **pyproject.toml, .gitignore**: Configured ✅
- **19 passing tests** ✅

What needs to be built or changed:
- Config and prompts simplified to 2 arms
- Runner rewritten for Claude Code agent spawning (replaces Anthropic SDK runner)
- Corpus expanded to 30+ defects
- Analysis pipeline (descriptive, GLMM, report)
