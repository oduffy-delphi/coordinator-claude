# Experiment Spec: Character Persona vs Role-Label vs Vanilla Code Review

**Date:** 2026-03-21
**Type:** Controlled experiment design
**Status:** Draft — awaiting PM review
**Trigger:** Persona research (2026-03-19) established mechanism (persona vectors are causal) but not magnitude for code review. No study has measured Character Personas in engineering review. This is a first-of-kind experiment.

---

## Research Question

Does a richly-described named Character Persona (e.g., "Patrik") produce measurably better code review output than (a) an identically-described unnamed role, or (b) a minimal/vanilla review prompt? If so, which variable — naming, description richness, or both — drives the effect?

## Background

The persona research synthesis (2026-03-19) established:
- **Persona vectors are causally real** — Anthropic's research proves rich behavioral descriptions genuinely steer model activations (not just style).
- **Persona alone yields +0.91% over neutral** on reasoning benchmarks (GPT-4). The +9.98% gain requires ensemble + adjudication architecture.
- **A-HMAD specialized roles**: 4-6% accuracy gains, 30%+ error reduction — but on reasoning tasks, not code review.
- **The gap**: No study has measured persona effects on code review quality. Code review is a mixed task — objective elements (is this a bug?) and subjective elements (is this architecture sound?) — making the persona effect prediction uncertain.

The novelty research (2026-03-20) classified Character Personas in engineering review as **novel application** — taxonomically unprecedented. All prior multi-agent review systems use functional role labels (tier 1 in the 2404.18231 taxonomy), not Character Personas (tier 2).

## Hypotheses

**H1 (Description richness):** A richly-described reviewer prompt finds more true defects than a minimal review prompt.
- *Prediction:* Strong effect. Supported by persona vector mechanism — richer descriptions activate more specific training data clusters.

**H2 (Naming effect):** A named Character Persona ("Patrik") finds more true defects than an identically-described unnamed role ("A rigorous code reviewer").
- *Prediction:* Weak or null effect. The literature consistently finds that behavioral description, not naming, is the active ingredient. But this has never been tested — the experiment fills a genuine gap.

**H3 (Interaction):** The combination of naming + framing produces effects beyond either alone (naming × framing interaction in the 2×2 factorial).
- *Prediction:* Possible but speculative. Names may function as "anchors" that improve description adherence, but no evidence supports this yet. The complete factorial (Arms B, B′, C, D) allows clean decomposition of this interaction.

**H4 (Sycophancy):** First-person persona framing ("I, Patrik, believe...") increases false negatives (missed real defects due to agreement bias) compared to third-person framing.
- *Prediction:* Supported by Anthropic's sycophancy vector research — roleplay framing activates sycophancy. Testable as a secondary measure.

---

## Experimental Design

### Conditions (5 arms)

| Arm | Name | Prompt Structure | Controls |
|-----|------|-----------------|----------|
| **A** | Vanilla | "Review this code for bugs and issues." | Baseline — minimal instruction |
| **B** | Rich description, unnamed, 1st person | "You are a rigorous code reviewer with 15+ years of experience. You focus on: security vulnerabilities, logic errors, performance issues, error handling gaps. You assume the author made mistakes. You are adversarial by nature. A review that finds no issues is a failed review. [Full behavioral description matching Patrik's, minus the name and backstory.]" | Isolates description richness |
| **B′** | Rich description, unnamed, 3rd person | "The reviewer is a rigorous code reviewer with 15+ years of experience. The reviewer focuses on: [identical description to B, but in third-person framing throughout.]" | Completes the factorial — unnamed × 3rd person |
| **C** | Rich description, named, 3rd person | "Patrik is a rigorous senior engineer... Patrik's review should identify... [Full Patrik prompt in third-person framing]" | Isolates naming effect (B′ vs C) |
| **D** | Rich description, named, 1st person | "You are Patrik, a rigorous senior engineer... [Full Patrik prompt in first-person framing, as currently deployed]" | Current production configuration |

### Why 5 arms: complete 2×2 factorial + baseline

Arms B, B′, C, and D form a complete 2×2 factorial crossing **naming** (unnamed/named) × **framing** (1st person/3rd person), with Arm A as an external baseline for description richness.

| | 1st person | 3rd person |
|---|---|---|
| **Unnamed** | B | B′ |
| **Named** | D | C |

This design allows clean decomposition of:
- **Naming main effect:** (C + D) vs (B + B′)
- **Framing main effect:** (B′ + C) vs (B + D)
- **Naming × framing interaction:** Does naming help more in one framing than the other?
- **Description richness:** Any of B/B′/C/D vs A

### Task Corpus

**Requirement:** A set of code files with known, pre-seeded defects of varying type and severity. The reviewer doesn't know which defects are seeded — they review as normal.

**Corpus design:**
- **N = 25 code files**, each 80-200 lines (long enough to be realistic, short enough that context isn't the bottleneck)
- **Language:** TypeScript or Python (high training data representation, reduces confounds from language obscurity)
- **Variable defect density** to simulate realistic review conditions:
  - 5 files with **0 defects** (clean) — pure false positive measurement
  - 5 files with **1-2 defects** (sparse) — tests detection in low-signal environments
  - 10 files with **3-5 defects** (moderate) — the typical case
  - 5 files with **6-8 defects** (dense) — tests whether reviewers saturate or maintain attention
- **Defect categories** (distributed unevenly across files — not every file is a uniform buffet):
  - Security (SQL injection, XSS, auth bypass)
  - Logic errors (off-by-one, wrong comparison, missing edge case)
  - Performance (N+1 queries, unnecessary allocation, missing memoization)
  - Error handling (swallowed exceptions, missing validation, race conditions)
- **Category distribution varies per file.** Some files are security-heavy, some have no security defects at all. This prevents reviewers from implicitly "expecting" every category in every file.
- **Defect difficulty:** Each defect tagged as obvious (any reviewer should catch), moderate (requires attention), or subtle (requires domain expertise). Distribution across the corpus: ~30% obvious, ~40% moderate, ~30% subtle.
- **Distractor code:** Files contain code that *looks* suspicious but is actually correct.

**Corpus manifests (two documents):**

1. **Defect manifest:** Every seeded defect with: file, line, type, category, severity, difficulty, description, and the correct fix.
2. **Distractor manifest:** Every intentional distractor with: file, line, description, and explanation of why it's actually correct.

**Scoring taxonomy for reviewer findings:**

| Category | Definition | Scoring |
|----------|-----------|---------|
| **True positive** | Matches a defect in the defect manifest | Counts toward recall and precision |
| **False positive — distractor** | Flags something documented in the distractor manifest | Counts against precision; tracked separately |
| **False positive — novel** | Flags something not in either manifest that is not a genuine issue | Counts against precision |
| **Valid unexpected finding** | Flags a genuine issue the corpus designer missed | Does NOT count against precision; added to a supplementary manifest for subsequent runs. Corpus imperfection is expected. |

**Corpus construction:**
1. Write clean, correct code files (including the 5 intentionally clean files)
2. Seed specific defects and document in the defect manifest
3. Seed distractors and document in the distractor manifest
4. Have a human expert verify both manifests (confirm defects are real, confirm distractors are correct, confirm clean files are actually clean)
5. Randomize defect placement across files

### Procedure

For each condition × each file (5 × 25 = 125 reviews per run, N runs):

1. Start a fresh Claude API session (no prior context)
2. Inject the condition-specific system prompt
3. Present the code file with: "Review this code. Report all issues you find, with file location, severity, and explanation."
4. Collect the review output
5. Score against both manifests using the scoring taxonomy

### Measures

**Primary (defect detection — per-defect binary outcome):**
- **Defect detected (yes/no):** The fundamental unit of observation. Each seeded defect × condition × run produces one binary outcome. This is the input to the GLMM (see Analysis Plan below).
- **Recall (derived):** Fraction of seeded defects correctly identified, aggregated per condition. Reported for interpretability but the statistical test operates on the binary per-defect data.
- **Precision (derived):** Fraction of reported issues that are genuine issues (seeded defects OR valid unexpected findings). Novel false positives and distractor false positives count against precision; valid unexpected findings do not. This avoids penalizing thoroughness.
- **F1 score (derived):** Harmonic mean of recall and precision.
- **Detection by category:** Recall broken down by defect type (security, logic, performance, error handling) and by defect difficulty (obvious, moderate, subtle). Tests whether persona description directs attention to specific categories or difficulty levels.

**Secondary (review quality):**
- **False positive rate:** Broken down by type: distractor FPs (flagged documented distractors) and novel FPs (flagged non-issues not in either manifest). Tracked separately — distractor FPs indicate sensitivity to suspicious-looking code; novel FPs indicate noise.
- **Severity accuracy:** For true positives, does the reviewer correctly assess severity? (Compare reviewer's severity rating to manifest severity.)
- **Explanation quality:** Blind-rated by **2 independent human evaluators** using an anchored rubric (see Evaluation Protocol below). Three sub-dimensions rated separately on a 1-5 scale: (a) root cause identification, (b) fix validity, (c) severity assessment. Reported as three separate scores, not averaged.
- **Coverage declaration:** Does the reviewer explicitly state what they did and didn't review? (Binary — present or absent.)

**Tertiary (sycophancy/framing):**
- **False negative rate on obvious defects:** The cleanest sycophancy signal. A sycophantic reviewer misses fewer *subtle* defects (appropriate caution) but should not miss *obvious* defects. If first-person framing (D) has a higher miss rate on obvious defects than third-person framing (C), that's sycophancy, not calibration.
- **Hedging conditional on difficulty:** Hedging language frequency ("might be," "could potentially," "consider whether") counted per finding and analyzed conditional on defect difficulty. Hedging on subtle defects is good calibration; hedging on obvious defects is a sycophancy signal. Raw unconditional hedging counts are not interpretable.
- **Confidence calibration:** For each finding, does the reviewer express appropriate confidence given the defect's difficulty level?

### Controls

- **Model:** Claude Opus 4.6, pinned to dated checkpoint `claude-opus-4-6-20250115` (current production reviewer model — production Patrik runs on Opus). Single model across all conditions. Pinning to a dated checkpoint ensures reproducibility — model aliases may resolve to different checkpoints over time. Note: if results are positive, a follow-up experiment on Sonnet could test whether the effect transfers to cheaper models.
- **Temperature:** 0 (lowest available). Note: temp=0 does **not** guarantee deterministic output — infrastructure-level non-determinism (batching, floating-point variance) produces variation across calls. The determinism pilot (see Prerequisites) will measure actual variance to inform the required number of runs.
- **Token budget:** Same max_tokens across all conditions.
- **Context:** Fresh API session per review — no cross-contamination.
- **File order:** Randomized per run to control for ordering effects.
- **Runs:** N determined by determinism pilot. Preliminary estimate: N ≥ 5 runs (all 125 reviews per run), adjusted upward if the pilot reveals non-trivial variance. With 25 files as the blocking factor, the file-level variance is the primary driver of generalizability.

### Evaluation Protocol

1. **Automated scoring** against both manifests using the scoring taxonomy (TP, distractor FP, novel FP, valid unexpected finding). Produces per-defect binary detection data for the GLMM.
2. **Blind human scoring** for explanation quality — 2 independent evaluators, each sees review output only, not which condition produced it. Each evaluator rates using the anchored rubric below. Inter-rater reliability reported via ICC (intraclass correlation coefficient).

**Explanation quality anchored rubric:**

| Score | Root Cause Identification | Fix Validity | Severity Assessment |
|-------|--------------------------|-------------|-------------------|
| **5** | Precisely identifies the root cause with correct technical explanation | Suggests a fix that would fully resolve the issue with no side effects | Severity matches manifest exactly |
| **4** | Identifies the root cause but explanation has minor imprecision | Fix would resolve the issue but has minor suboptimalities | Severity within one level of manifest |
| **3** | Identifies the general area of the problem but misses the precise mechanism | Fix addresses the symptom but not the root cause, or introduces minor issues | Severity directionally correct but off by two levels |
| **2** | Vaguely gestures at the problem domain but misidentifies the specific cause | Fix would not resolve the issue or introduces new problems | Severity significantly misjudged |
| **1** | Completely misidentifies the root cause | No fix suggested, or suggested fix is irrelevant/harmful | Severity completely wrong |

Three sub-dimensions are reported separately (not averaged or summed). Pre-registered.

3. **Statistical analysis:** See Analysis Plan below.

### Analysis Plan

**Primary analysis:** Generalized linear mixed model (GLMM) with binomial family.

```
defect_detected ~ condition + (1 | defect_id)
```

- **Outcome:** Binary — did this condition detect this specific defect on this run? (1/0)
- **Fixed effect:** Condition (5 levels: A, B, B′, C, D)
- **Random effects:** Defect (accounts for some defects being inherently harder). Note: defect_ids are globally unique, so this random intercept implicitly captures file-level variance (each defect belongs to exactly one file). A separate `(1 | file)` random effect would be redundant and cause identifiability issues.
- **Link function:** Logit (the default for binomial family in lme4::glmer). Pre-registered — no researcher degrees of freedom.
- **Post-hoc:** Estimated marginal means (emmeans) with Tukey adjustment for pairwise comparisons. Pre-registered contrasts:
  - H1: Any of {B, B′, C, D} vs A (description richness)
  - H2: (C + D) vs (B + B′) (naming main effect)
  - H3: (B′ + C) vs (B + D) (framing main effect)
  - H4: Naming × framing interaction within the 2×2 factorial

**Secondary analyses:**
- Category-specific detection: Add defect_category as a fixed effect interaction term to test whether personas differentially direct attention.
- Difficulty-specific detection: Add defect_difficulty as a fixed effect interaction term. The sycophancy hypothesis predicts condition × difficulty interaction (first-person framing underperforms on obvious defects).
- Explanation quality: Linear mixed model with rater as a random effect, condition as fixed effect. Separate models for each sub-dimension.

**Implementation:** R with `lme4` (GLMM) and `emmeans` (post-hoc contrasts + equivalence tests). Python alternative: `pymer4` wrapper (note: `statsmodels.MixedLM` is linear only — cannot fit binomial GLMM).

**Human review step for FP_novel findings:** Before computing precision for any arm, all findings classified as `FP_novel` by the automated scorer must be reviewed by a human to reclassify genuine issues as `valid_unexpected`. The automated scorer cannot assign `valid_unexpected` — it requires human judgment. This is a hard prerequisite before analysis; precision computed without this step will be biased downward.

### Power Analysis (simulation-based)

The classical Cohen's d framework does not apply to a GLMM with crossed random effects. Power must be estimated via simulation.

**Approach:** Simulate datasets under the GLMM structure with assumed parameters, fit the model, and check whether the condition effect is detected. Repeat 1000 times per parameter configuration.

**Assumed parameters (informed by literature):**
- Baseline detection rate (Arm A): ~60% (vanilla reviewer catches ~60% of seeded defects — to be refined by pilot)
- Description richness effect (B/B′/C/D vs A): +10-15 percentage points (based on A-HMAD's 4-6% accuracy gains, adjusted upward because code review is more subjective than reasoning benchmarks)
- Naming effect (C/D vs B/B′): +0-3 percentage points (literature suggests near-zero; we're powered to detect ≥5pp if it exists)
- Framing effect (B′/C vs B/D): +0-5 percentage points (speculative; sycophancy literature suggests measurable but small)
- Defect-level variance (σ²_defect): To be estimated from pilot

**Key insight:** With 25 files (the primary unit of generalization) and ~100 total seeded defects, we have ~100 binary observations per condition per run. For the description richness effect (expected large), power should be very high. For the naming effect (expected small-to-null), we are explicitly acknowledging limited power — a well-powered test of H2 would require ~1000+ observations per arm for a 3pp effect at 80% power.

**Equivalence testing for H2 (naming effect):** A non-significant naming contrast is not evidence that naming has no effect — it could reflect insufficient power. To make a null H2 interpretable, we pre-register a **TOST (Two One-Sided Tests)** procedure:
- **Smallest effect size of interest (SESOI):** 5 percentage points in recall (effects smaller than this do not justify architectural changes)
- **Procedure:** After fitting the GLMM, compute the 90% CI for the naming contrast (C+D) vs (B+B′) on the probability scale. If the entire 90% CI falls within [−5pp, +5pp], conclude practical equivalence. If the CI is wide (includes both meaningful positive and negative effects), conclude "inconclusive" — not "no effect."
- This applies to H2 only. H1 (description richness) is expected to show a clear effect; H3 (framing) uses standard NHST since a non-significant result there is less decision-relevant.

**The determinism pilot will provide the empirical variance estimates needed to run the simulation and finalize N.**

---

## Expected Outcomes and Implications

| Result | Implication for our architecture |
|--------|--------------------------------|
| {B,B′,C,D} >> A (rich description >> vanilla) | Validates investment in behavioral descriptions. Keep enriching persona prompts. |
| (C+D) ≈ (B+B′) — naming main effect null | Names are for human ergonomics, not model performance. Keep names for calibration benefit, but don't over-invest in naming. |
| (C+D) > (B+B′) — naming main effect positive | Surprising — would suggest names activate additional training data clusters. Investigate mechanism. |
| (B′+C) > (B+D) — 3rd person > 1st person | Confirms sycophancy risk from 1st-person framing. Migrate all persona prompts to 3rd-person framing. |
| (B′+C) ≈ (B+D) — framing main effect null | Current 1st-person framing is fine. No migration needed. |
| Naming × framing interaction significant | The effect of naming depends on framing (or vice versa). Examine cell means to determine the optimal combination. |
| D specifically underperforms on obvious defects | Strong sycophancy signal in production configuration. Prioritize framing migration. |

---

## Prerequisites

### Determinism Pilot

Before finalizing the experimental parameters, run a determinism pilot to measure actual API variance at temp=0:

1. Select 3 representative files from the corpus (1 clean, 1 moderate, 1 dense)
2. Select 1 condition (Arm D — production configuration)
3. Run 10 identical API calls per file (30 calls total)
4. Measure: Do the outputs differ? If so, how much? Specifically:
   - Do the *same defects* get flagged across calls? (Binary agreement per defect)
   - Does the *number* of findings vary? (Range and variance)
   - Does the *wording* differ while the findings stay stable? (Substantive vs cosmetic variance)
5. **If outputs are near-identical (≥90% defect-level agreement):** N = 5 runs is sufficient. Variance is cosmetic.
6. **If outputs vary meaningfully (<90% agreement):** Use the observed variance to parameterize the power simulation and determine the required N.

**Cost:** ~30 API calls. Negligible. **This is a hard prerequisite — do not skip it.**

---

## Cost Estimate

- 125 reviews per run × N runs (estimated 5-7) = 625-875 API calls
- Each review: ~2000 input tokens (system prompt + code file) + ~1500 output tokens (review) = ~3500 tokens per call
- Total: ~2.2M-3.1M tokens at Opus pricing ≈ $30-45
- Determinism pilot: 30 calls ≈ $1
- Human evaluation: 2 raters × ~8 hours each for blind scoring of explanation quality across 625-875 review outputs
- Corpus construction: ~8 hours (write 25 files, seed defects + distractors, create both manifests, expert verification)

**Total estimated cost:** ~$45 API + ~24 hours human time

---

## Limitations

1. **Seeded defects aren't natural defects.** Real code has defects that emerge from misunderstanding requirements, copy-paste errors, and conceptual confusion — harder to simulate than "insert a missing null check." Mitigate by including subtle, realistic defects and varying density/category distribution across files. The variable density design (including clean files) partially addresses this.
2. **Single model.** Results may not generalize across model families. But we only need to know if it works with our production model (Opus). A follow-up experiment on Sonnet could test transfer.
3. **No ensemble/adjudication.** This tests single-pass review. The literature suggests the big gains come from ensemble architectures — but we need to know the single-pass baseline before testing ensembles.
4. **Artificial isolation.** In production, Patrik reviews code with project context, CLAUDE.md instructions, and prior review history. This experiment strips all of that. The persona effect may be larger or smaller in context.
5. **Temperature 0 reduces variance but also reduces ecological validity.** Production reviews run at default temperature. The determinism pilot will characterize how much variance temp=0 actually eliminates.
6. **Corpus construction is imperfect.** The "valid unexpected finding" category in the scoring taxonomy acknowledges this — reviewers may find genuine bugs we didn't intend to seed. The supplementary manifest mechanism captures these for subsequent runs, improving corpus quality over time.

---

## Relationship to Other Experiments

- **Sequential vs Parallel Review experiment** (separate spec) tests architectural claims that build on top of this one. If persona review shows no benefit over vanilla, the sequential review experiment's premise weakens (but doesn't collapse — sequential review has independent benefits from noise reduction).
- **Handoff vs Compaction experiment** (2026-03-21 addendum) tests continuity mechanisms. Orthogonal to this experiment but could be run on the same corpus infrastructure.

---

## Next Steps

1. [ ] PM review and approve/modify this spec
2. [ ] **Determinism pilot** — 3 files × 10 calls × 1 condition. Hard prerequisite for finalizing N.
3. [ ] **Power simulation** — using pilot variance estimates, simulate GLMM to determine required N runs.
4. [ ] Build the defect corpus (25 files + defect manifest + distractor manifest)
5. [ ] Extract and formalize the 5 condition prompts from production Patrik configuration
6. [ ] Build the automated scoring harness (per-defect binary matching + scoring taxonomy)
7. [ ] Recruit and brief 2 evaluators for explanation quality scoring; provide anchored rubric
8. [ ] Run methodology pilot (3 files × 5 conditions × 1 run) to validate the full pipeline
9. [ ] Full run
10. [ ] Fit GLMM, compute emmeans, run pre-registered contrasts
11. [ ] Inter-rater reliability check (ICC) on explanation quality scores
12. [ ] Analysis write-up with decision table outcomes
