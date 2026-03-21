# Experiment Spec: Specialist Persona vs Baseline Code Review

**Date:** 2026-03-21 (revised from 5-arm factorial to 2-arm A/B)
**Type:** Controlled experiment design
**Status:** Active — harness built, corpus in progress
**Trigger:** Persona research (2026-03-19) established mechanism (persona vectors are causal) but not magnitude for code review. No study has measured Character Personas in engineering review. This is a first-of-kind experiment.

---

## Research Question

Does a richly-described Character Persona (the production "Patrik" reviewer prompt) produce measurably better code review output than a generic baseline review prompt?

### Why 2 arms, not 5

The original spec proposed a 5-arm 2×2 factorial (naming × framing) + baseline to decompose which variable drives the effect. This was revised to 2 arms (BASELINE vs SPECIALIST) because:

1. **The primary question is practical, not mechanistic.** We need to know if persona prompts work *at all* for code review before decomposing *why*. A clear SPECIALIST > BASELINE result justifies the architecture; a null result means the factorial decomposition is moot.
2. **Power.** With the corpus size (~10 files, ~32 defects), a 5-arm design spreads observations too thin. A 2-arm design concentrates power on the primary question.
3. **Cost.** 2 arms × 10 files × N runs is 20N calls. 5 arms would be 50N calls for the same N — 2.5× the cost for secondary hypotheses.
4. **Iterative design.** If the 2-arm experiment shows a clear effect, a follow-up factorial experiment can decompose naming vs framing with better-calibrated power estimates.

The naming effect (H2), framing effect (H3), and sycophancy (H4) hypotheses from the original spec are deferred to a follow-up experiment.

## Hypothesis

**H1 (Specialist description richness):** A richly-described specialist reviewer prompt (with stated focus areas, review philosophy, and adversarial framing) finds more true defects than a generic baseline prompt.

- *Prediction:* Moderate-to-strong effect. Supported by persona vector mechanism — richer descriptions activate more specific training data clusters. A-HMAD showed 4-6% accuracy gains for specialized roles on reasoning tasks; code review (more subjective) may show larger effects.

---

## Experimental Design

### Conditions (2 arms)

| Arm | Name | Prompt Structure | Controls |
|-----|------|-----------------|----------|
| **BASELINE** | Generic reviewer | "Review this code for bugs and issues." + shared output format | Minimal instruction — isolates the effect of rich description |
| **SPECIALIST** | Full Patrik prompt | Rich behavioral description: stated focus areas (security, logic, performance, error handling), adversarial review philosophy, explicit quality standards + shared output format | Current production configuration |

The shared output format (JSON schema + coverage declaration) is identical across both arms — all behavioral variation comes from the system prompt.

### Task Corpus

**Requirement:** A set of code files with known, pre-seeded defects of varying type and severity. The reviewer doesn't know which defects are seeded — they review as normal.

**Current corpus:** 10 code files (TypeScript + Python), ~32 seeded defects, with defect and distractor manifests in YAML at `experiments/corpus/persona_review/`.

**Corpus design:**
- **Language:** TypeScript and Python (high training data representation, reduces confounds from language obscurity)
- **Variable defect density** to simulate realistic review conditions
- **Defect categories:** Security, logic, performance, error handling, architecture
- **Defect difficulty:** Each defect tagged as obvious, moderate, or subtle
- **Distractor code:** Files contain code that *looks* suspicious but is actually correct

**Corpus manifests:**

1. **Defect manifest** (`manifests/defects.yaml`): Every seeded defect with: file, line range, category, severity, difficulty, keywords (for automated matching), description, and correct fix.
2. **Distractor manifest** (`manifests/distractors.yaml`): Every intentional distractor with: file, line range, description, and explanation of why it's correct.

**Scoring taxonomy for reviewer findings:**

| Category | Definition | Scoring |
|----------|-----------|---------|
| **True positive** | Matches a defect in the defect manifest | Counts toward recall and precision |
| **False positive — distractor** | Flags something documented in the distractor manifest | Counts against precision; tracked separately |
| **False positive — novel** | Flags something not in either manifest that is not a genuine issue | Counts against precision |
| **Valid unexpected finding** | Flags a genuine issue the corpus designer missed | Does NOT count against precision; requires human review of FP_novel findings |

### Procedure

For each condition × each file (2 × 10 = 20 reviews per run, N runs):

1. Start a fresh Claude Code session via agent spawning (`claude --print --bare`) — no prior context
2. Inject the condition-specific system prompt
3. Present the code file with: "Review this code. Report all issues you find, with file location, severity, and explanation."
4. Collect the review output
5. Score against both manifests using the bipartite matching scorer

### Execution mode

Reviews are dispatched via Claude Code agent spawning (`subprocess.run(["claude", "--print", "--bare", ...])`) for ecological validity — this matches how production reviews are dispatched. The trade-off: no direct control over temperature, token counts, or cost tracking. Duration is tracked per-call.

### Measures

**Primary (defect detection — per-defect binary outcome):**
- **Defect detected (yes/no):** The fundamental unit of observation. Each seeded defect × condition × run produces one binary outcome. This is the input to the GLMM.
- **Recall (derived):** Fraction of seeded defects correctly identified, aggregated per condition.
- **Precision (derived):** Fraction of reported issues that are genuine (seeded defects OR valid unexpected findings). Requires human review of FP_novel findings before computation.
- **F1 score (derived):** Harmonic mean of recall and precision.
- **Detection by category:** Recall broken down by defect type and difficulty.

**Secondary (review quality):**
- **False positive rate:** Broken down by distractor FPs and novel FPs.
- **Severity accuracy:** For true positives, does the reviewer correctly assess severity?
- **Explanation quality:** Blind-rated by 2 independent human evaluators using an anchored rubric. Three sub-dimensions rated separately on a 1-5 scale: (a) root cause identification, (b) fix validity, (c) severity assessment.

### Controls

- **Model:** Agent spawning uses the default model alias — production-equivalent. Both arms use the same model.
- **Context:** Fresh session per review — no cross-contamination (`--bare` flag skips hooks, plugins, CLAUDE.md).
- **File order:** Randomized per run to control for ordering effects.
- **Runs:** N determined by determinism pilot. Preliminary estimate: N ≥ 10 runs.
- **Output format:** Identical JSON schema across both arms — shared output format appended to both prompts.

### Evaluation Protocol

1. **Automated scoring** using bipartite matching scorer (`review_experiments.scorer.score_review`). Produces per-defect binary detection data.
2. **Human review** of all FP_novel findings to reclassify genuine issues as valid_unexpected. Hard prerequisite before computing precision.
3. **Blind human scoring** for explanation quality — 2 independent evaluators using anchored rubric. Inter-rater reliability via ICC.

**Explanation quality anchored rubric:**

| Score | Root Cause Identification | Fix Validity | Severity Assessment |
|-------|--------------------------|-------------|-------------------|
| **5** | Precisely identifies the root cause with correct technical explanation | Suggests a fix that would fully resolve the issue with no side effects | Severity matches manifest exactly |
| **4** | Identifies the root cause but explanation has minor imprecision | Fix would resolve the issue but has minor suboptimalities | Severity within one level of manifest |
| **3** | Identifies the general area of the problem but misses the precise mechanism | Fix addresses the symptom but not the root cause, or introduces minor issues | Severity directionally correct but off by two levels |
| **2** | Vaguely gestures at the problem domain but misidentifies the specific cause | Fix would not resolve the issue or introduces new problems | Severity significantly misjudged |
| **1** | Completely misidentifies the root cause | No fix suggested, or suggested fix is irrelevant/harmful | Severity completely wrong |

Three sub-dimensions are reported separately (not averaged or summed). Pre-registered.

### Analysis Plan

**Primary analysis:** Generalized linear mixed model (GLMM) with binomial family.

```
defect_detected ~ condition + (1 | defect_id)
```

- **Outcome:** Binary — did this condition detect this specific defect on this run? (1/0)
- **Fixed effect:** Condition (2 levels: BASELINE, SPECIALIST)
- **Random effects:** Defect (accounts for some defects being inherently harder). Defect_ids are globally unique, implicitly capturing file-level variance.
- **Link function:** Logit (default for binomial in lme4::glmer). Pre-registered.
- **Post-hoc:** Single pre-registered contrast: SPECIALIST vs BASELINE.

**Secondary analyses:**
- Category-specific detection: Add defect_category as a fixed effect interaction term.
- Difficulty-specific detection: Add defect_difficulty as a fixed effect interaction term.
- Explanation quality: Linear mixed model with rater as a random effect, condition as fixed effect. Separate models for each sub-dimension.

**Implementation:** R with `lme4` (GLMM) and `emmeans` (contrasts). Python alternative: `pymer4` wrapper (note: `statsmodels.MixedLM` is linear only — cannot fit binomial GLMM).

**Human review step for FP_novel findings:** Before computing precision for any arm, all findings classified as `FP_novel` by the automated scorer must be reviewed by a human to reclassify genuine issues as `valid_unexpected`. This is a hard prerequisite before analysis.

### Power Analysis

With ~32 defects across 10 files, 2 arms, and N runs, we have ~32 binary observations per arm per run. For a 2-arm comparison with a 10-15pp effect size (informed by A-HMAD literature), N=10 runs gives ~320 observations per arm — adequate for detecting moderate effects. The determinism pilot will provide empirical variance estimates to confirm.

**The determinism pilot will provide the empirical variance estimates needed to finalize N.**

---

## Expected Outcomes and Implications

| Result | Implication for our architecture |
|--------|--------------------------------|
| SPECIALIST >> BASELINE | Validates investment in rich persona descriptions. The production Patrik prompt adds measurable value. |
| SPECIALIST ≈ BASELINE | Rich descriptions don't help for code review specifically. Simplify prompts — the persona is ergonomic, not functional. |
| SPECIALIST < BASELINE (surprising) | Rich descriptions actively hurt — possibly by constraining attention. Investigate and consider prompt simplification. |

---

## Prerequisites

### Determinism Pilot

Before finalizing the experimental parameters, run a determinism pilot to measure actual variance via agent spawning:

1. Select 3 representative files from the corpus (1 sparse, 1 moderate, 1 dense)
2. Select 1 condition (SPECIALIST — production configuration)
3. Run 10 identical calls per file (30 calls total)
4. Measure variance in findings across calls
5. Use observed variance to determine required N runs

**Cost:** ~30 agent-spawned calls. **This is a hard prerequisite — do not skip it.**

---

## Cost Estimate

- 20 reviews per run × N runs (estimated 10) = 200 agent-spawned calls
- Determinism pilot: 30 calls
- Human evaluation: 2 raters × explanation quality scoring
- Total: ~230 calls + human evaluation time

---

## Limitations

1. **Seeded defects aren't natural defects.** Mitigate with realistic, varied defects and variable density.
2. **2-arm design cannot decompose naming vs framing.** By design — this is the first step. Follow-up factorial experiment if results warrant.
3. **Agent spawning removes temperature/token control.** Ecological validity trade-off. Agent spawning matches production; direct API would give more control.
4. **No ensemble/adjudication.** Tests single-pass review only.
5. **Artificial isolation.** No project context, no CLAUDE.md, no prior history.
6. **Corpus construction is imperfect.** The valid_unexpected category acknowledges this.

---

## Relationship to Other Experiments

- **Sequential vs Parallel Review experiment** (separate spec) tests architectural claims that build on top of this one.
- **Follow-up factorial experiment** — if SPECIALIST > BASELINE, decompose the effect with a 4-arm factorial (naming × framing) using the same corpus and power estimates from this experiment's results.

---

## Next Steps

1. [x] Build shared experiment harness (scorer, parser, storage, corpus, CLI)
2. [x] Build persona-specific pipeline + agent client
3. [ ] Expand corpus to target size (currently 10 files, 32 defects)
4. [ ] **Determinism pilot** — 3 files × 10 calls × SPECIALIST. Hard prerequisite.
5. [ ] Full experiment run
6. [ ] Human review of FP_novel findings
7. [ ] GLMM analysis
8. [ ] Analysis write-up with decision table outcomes
