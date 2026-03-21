# Plan: Persona Review A/B Experiment Harness

## Context

We have a detailed experiment spec (`docs/research/experiment-persona-review-ab-spec.md`) that defines *what* to measure and *why*, but no infrastructure to actually run it. The repo is a plugin specification system (Python 3.12 available, no app code) with zero experiment tooling. This plan builds the harness from scratch, designed for reuse by future experiments (sequential review, handoff, deep research).

## Directory Structure

```
experiments/
  pyproject.toml                      # Shared deps for all experiments
  persona_review/
    __init__.py
    config.py                         # Arms, model, temperature, paths
    corpus/
      manifests/
        defects.yaml                  # Seeded defect manifest
        distractors.yaml              # Known non-issues manifest
        adjudications.yaml            # Post-hoc reclassifications (created during analysis)
      files/                          # 25 code files (ts/ and py/ subdirs)
    prompts/
      shared_output_format.md         # Output format section (identical across arms)
      arm_a_vanilla.md                # Arm A: "Review this code"
      arm_b_rich_unnamed_1p.md        # Arm B: Rich description, unnamed, 1st person
      arm_bp_rich_unnamed_3p.md       # Arm B': Rich description, unnamed, 3rd person
      arm_c_rich_named_3p.md          # Arm C: Named Patrik, 3rd person
      arm_d_rich_named_1p.md          # Arm D: Full production Patrik, 1st person
    harness/
      __init__.py
      api_client.py                   # Anthropic SDK wrapper (fresh session per call)
      prompt_builder.py               # Assembles system + user messages per arm
      runner.py                       # Async orchestrator with concurrency control
      result_store.py                 # JSON-per-call persistence, resumable
    scoring/
      __init__.py
      taxonomy.py                     # Enums + dataclasses (TP, distractor FP, novel FP, valid unexpected)
      parser.py                       # Extract ReviewOutput JSON from response
      matcher.py                      # Match findings to defects (keyword + line proximity)
    analysis/
      __init__.py
      descriptive.py                  # Summary tables, per-arm recall/precision/F1
      glmm.py                        # GLMM fitting + emmeans + contrasts
      report.py                       # Markdown report with decision table
    pilots/
      determinism.py                  # 3 files x 10 calls x 1 condition
    cli.py                            # Entry point: pilot / run / score / analyze
  results/                            # .gitignored — raw API outputs + reports
```

## Implementation Phases

### Phase 1: Foundation
**Files:** `pyproject.toml`, `config.py`, `taxonomy.py`, `result_store.py`, `parser.py`

- `pyproject.toml`: deps are `anthropic`, `pyyaml`, `click`, `tqdm`, `pandas`, `scipy`. Analysis deps optional: `pymer4` (if R available) or `statsmodels` fallback.
- `config.py`: Arms enum (A, B, B_PRIME, C, D), model pinned to exact dated version (e.g., `claude-opus-4-6-20260321`) to prevent checkpoint drift across multi-day runs. Temp = 0, max_tokens = 4096, paths. The model string must be the exact dated ID, not the alias — aliases may resolve to different checkpoints over time.
- `taxonomy.py`: `FindingClassification` enum, `ScoredFinding` / `ScoredReview` dataclasses.
- `result_store.py`: Each call saves to `results/runs/{experiment_id}/{arm}/{file_stem}/run_{n}.json`. Supports `exists()` check for resumption.
- `parser.py`: Extracts the ReviewOutput JSON from LLM responses using a fallback chain:
  1. Regex-extract the first ````json` ... ``` `` block, then `json.loads()`.
  2. If that fails, attempt repair: strip trailing commas, close unclosed braces, remove control characters.
  3. If repair fails, flag as `parse_error` — store the raw response for manual inspection.
  Parse failure rate is tracked as a data quality metric. Returns `ParsedReview` with findings list + parse errors list.

### Phase 2: Prompts
**Files:** 6 prompt files under `prompts/`, `prompt_builder.py`

Extract from `plugins/coordinator/agents/patrik-code-review.md`:
- **Shared output format** (lines 85-149): Output Format + Coverage Declaration sections. Identical across all 5 arms — this ensures parseable, structured output regardless of persona treatment.
- **Arm A (vanilla):** "Review this code for bugs and issues. [shared output format]"
- **Arm B (rich, unnamed, 1st person):** Extract Patrik's Core Philosophy + Review Standards + Review Process + Communication Style, rewrite to remove "Patrik" references. Keep 1st-person framing ("You are a rigorous code reviewer...").
- **Arm B' (rich, unnamed, 3rd person):** Same content as B, rewritten in 3rd person ("The reviewer is a rigorous code reviewer...").
- **Arm C (rich, named, 3rd person):** Same content as B' but with "Patrik" name reintroduced ("Patrik is a rigorous senior engineer...").
- **Arm D (rich, named, 1st person):** Production Patrik prompt (lines 10-68 of the agent file), plus shared output format. This is the baseline production configuration.

`prompt_builder.py`: Loads arm prompt + shared output format as system message. Loads code file as user message with "Review this code. Report all issues you find, with file location, severity, and explanation."

### Phase 3: API Harness
**Files:** `api_client.py`, `runner.py`, `cli.py` (partial)

- `api_client.py`: Thin async wrapper around `anthropic.AsyncAnthropic`. Each call creates a fresh `messages.create()` — no conversation state. Handles 429/500/529 retries with exponential backoff. Returns response text + metadata dict.
- `runner.py`: Takes config (arms, files, N runs). Builds full matrix with **randomized file order per run** (as required by the experiment spec — even though fresh sessions make this theoretically unnecessary, it satisfies the control requirement and costs nothing). Checks result_store for existing results (skip completed). Runs with **adaptive concurrency**: starts with `asyncio.Semaphore(10)`, reduces semaphore on 429 responses using `Retry-After` headers, increases back up after sustained success. Saves each result immediately. Progress bar via tqdm.
- `cli.py`: Click CLI with subcommands: `pilot`, `run`, `score`, `analyze`.

### Phase 4: Scoring Engine
**Files:** `matcher.py`

The matching algorithm (deterministic, no LLM-as-judge):

**Step 1 — Compute match scores (finding × defect cost matrix):**

For each finding in a parsed review, compute a match score against every defect in the file's manifest:

```
match_score(finding, defect) = line_score * 0.6 + keyword_score * 0.4
```

Where:
- **line_score:** 1.0 if finding's line range overlaps defect's line range (tolerance ±5 lines), 0.0 otherwise. "Overlap" means any line in `[finding.line_start, finding.line_end]` falls within `[defect.line_start - 5, defect.line_end + 5]`.
- **keyword_score:** Fraction of the defect's keywords that appear as case-insensitive substring matches in the finding text. E.g., defect has keywords `["null", "undefined", "optional chaining"]` and finding text contains "null" and "undefined" → keyword_score = 2/3 = 0.67.

A match is viable if match_score ≥ 0.4 (i.e., either line overlap alone at 0.6, or at least 2 keywords matching without line overlap at ~0.53, or a combination). Scores below 0.4 are treated as no-match.

**Step 2 — Optimal bipartite assignment:**

This is a bipartite matching problem: findings on one side, defects on the other, match_score as edge weights. Greedy matching is order-dependent and can produce suboptimal assignments. Instead, use `scipy.optimize.linear_sum_assignment` on the negated cost matrix for optimal maximum-weight matching. With ~4-8 defects and ~6-12 findings per file, this is trivially fast.

Each defect matches at most one finding; each finding matches at most one defect. Unmatched findings proceed to Step 3.

**Step 3 — Classify unmatched findings (defects take priority over distractors):**

Findings not assigned to a defect in Step 2 are checked against the distractor manifest using the same line + keyword logic. **Defect matching always takes priority** — if a finding could match both a nearby defect and a nearby distractor, the defect match wins (handled by running Step 2 first).

Remaining unmatched findings are classified as novel FP (may be reclassified via `adjudications.yaml` later).

**Step 4 — Output:**

Per-defect binary detection vector + per-finding classification using the 4-category taxonomy.

**Sensitivity testing:** During Phase 4 verification, test the match_score threshold (0.4) and the line tolerance (±5) against the seed corpus. If the matcher misclassifies any known defect or distractor in the seed corpus, adjust thresholds before proceeding to the pilot. **Acceptance criterion: 100% correct classification on the seed corpus against manual ground truth.** The seed corpus is small enough that every classification can be verified by hand.

### Phase 5: Determinism Pilot
**Files:** `determinism.py`

Before building the full corpus, run the pilot:
- Use 3 pre-built test files (1 clean, 1 moderate, 1 dense — from seed corpus)
- 10 calls per file, Arm D only = 30 calls
- Measure: per-defect agreement rate across 10 runs, Fleiss's kappa, recall variance
- Output: pilot report with recommendation for N

### Phase 6: Corpus Construction
**Files:** 25 code files + `defects.yaml` + `distractors.yaml`

**Dependency:** Prompt content (Phase 2) must be finalized before corpus construction. The prompts reveal what the persona emphasizes (e.g., Patrik's focus on documentation, error handling) — this should inform distractor placement. Distractors placed in areas the persona explicitly targets test false positive behavior; distractors placed in areas outside the persona's stated focus test whether the reviewer strays beyond its mandate.

This is the creative work. Build iteratively:
- Start with 5 files (covering all density levels) during Phase 2 as test corpus
- Expand to full 25 after the pilot validates the methodology
- Each file: write clean code, then seed defects per the spec's distribution
- Manifest entries: `defect_id` (globally unique, e.g., `auth_middleware_null_deref`), file, line_range, defect_type, severity, difficulty, keywords, description
- **Distractor placement constraint:** No distractor may be placed within ±5 lines of a defect. This prevents ambiguous matches where the scorer cannot distinguish "found the defect" from "flagged the distractor." If a natural distractor happens to be near a defect, move one of them.

### Phase 7: Analysis Pipeline
**Files:** `descriptive.py`, `glmm.py`, `report.py`

- `descriptive.py`: Per-arm recall, precision, F1 with confidence intervals. Per-category and per-difficulty breakdowns.
- `glmm.py`: Fit `defect_detected ~ condition + (1|file) + (1|defect_id)` using pymer4 (if R available) or statsmodels GEE with binomial family as fallback. Compute emmeans and pre-registered contrasts. **Note on random effects notation:** `defect_id` must be globally unique across files (e.g., `auth_middleware_null_deref`, not just `null_deref`). With globally unique IDs, `(1|file) + (1|defect_id)` is correct — nesting (`(1|file/defect_id)`) is unnecessary because `defect_id` already implies its file. This convention is enforced during corpus construction in the manifest schema.
- `report.py`: Markdown report mapping results to the decision table from the spec.

## Key Design Decisions

1. **Deterministic scoring (no LLM-as-judge).** Keyword + line proximity matching is reproducible and auditable. The adjudication step handles edge cases humanly. Using an LLM to score another LLM's output introduces circular dependency and variance.

2. **YAML manifests.** Human-authored corpus metadata needs comments, multi-line descriptions, and readability. YAML is friendlier for this than JSON. The scoring engine loads it once — parse performance is irrelevant.

3. **Async with adaptive concurrency.** API calls are I/O-bound. The Anthropic SDK supports async natively. Starts with semaphore at 10 concurrent, adapts downward on rate limit responses (429) using `Retry-After` headers, and recovers upward after sustained success. This avoids both under-utilization and rate limit storms.

4. **Crash-resumable runner.** Each API call result is saved to disk immediately. On restart, the runner checks which (arm, file, run) tuples already have results and skips them. 625+ API calls will take ~10 minutes; crashes shouldn't require full reruns.

5. **Shared output format across all arms.** The experiment varies the persona/description portion of the prompt. The output format (JSON schema + coverage declaration) is identical across all 5 arms. This ensures parseable, scoreable output regardless of treatment condition.

6. **R dependency is optional.** The gold-standard GLMM uses `pymer4` → R's `lme4::glmer`. If R isn't installed, fall back to statsmodels GEE. Both are adequate; pymer4 gives random effect estimates, GEE gives population-average estimates.

## Build Order

| Order | What | Enables | Effort |
|-------|------|---------|--------|
| 1 | Foundation (config, taxonomy, store, parser) | Everything | Small |
| 2 | Prompts (extract from Patrik, create 5 arms) | API calls | Small |
| 3 | Seed corpus (5 test files + manifests) | Testing the pipeline | Medium |
| 4 | API harness (client, runner, CLI) | Running calls | Medium |
| 5 | Scoring engine (matcher) | Evaluating results | Medium |
| 6 | Determinism pilot (run + analyze) | Finalizing N | Small |
| 7 | Full corpus (expand to 25 files) | Full experiment | Large (creative) |
| 8 | Analysis pipeline (GLMM, report) | Interpreting results | Medium |

Phases 1-5 can be built and tested with the seed corpus (5 files). Phase 6 validates the methodology end-to-end. Only after the pilot confirms the approach do we invest in the full 25-file corpus (Phase 7).

## Verification

- **Phase 1-2:** Print assembled prompts for each arm. Confirm output format section is byte-identical across arms. Verify model string is an exact dated ID, not an alias.
- **Phase 3:** Run 5 calls (1 arm × 1 file × 5 runs). Verify JSON saved correctly, results are resumable (kill and restart), and parse fallback chain handles at least one malformed response correctly.
- **Phase 4:** Score the 5 test results against the seed manifest. **Acceptance criterion: 100% correct classification on the seed corpus against manual ground truth.** Every TP, distractor FP, novel FP, and undetected defect must match human judgment. If the matcher disagrees with manual scoring on any finding, adjust thresholds or matching logic before proceeding. Sensitivity-test the match_score threshold (try 0.3, 0.4, 0.5) and line tolerance (try ±3, ±5, ±7) to confirm the chosen values are not fragile.
- **Phase 5:** Pilot output confirms variance characteristics and required N.
- **Phase 8:** Run analysis on pilot data. Verify GLMM fits, emmeans produce sensible per-arm detection probabilities, and pre-registered contrasts execute without error.

## Critical Files

- `plugins/coordinator/agents/patrik-code-review.md` — source for prompt extraction (lines 10-149)
- `.python-version` — confirms 3.12
- `.gitignore` — needs `experiments/results/` added (do this in Phase 1, not later)
- `docs/research/experiment-persona-review-ab-spec.md` — the experiment spec this harness implements
