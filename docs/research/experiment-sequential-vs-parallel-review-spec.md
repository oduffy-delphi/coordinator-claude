# Experiment Spec: Sequential Review with Fix Gates vs Parallel+Aggregate

**Date:** 2026-03-21
**Type:** Controlled experiment design
**Status:** Draft — revised per Camelia's methodological review (2026-03-21), awaiting PM review
**Trigger:** The novelty research (2026-03-20) classified sequential multi-persona review with mandatory fix gates as **genuinely novel** — no documented prior art. The industry default is parallel+aggregate (Anthropic, CodeRabbit, Qodo, GitHub Copilot). Our architecture is built on an untested theory. Time to test it.

---

## Research Question

Does a sequential review pipeline — where Reviewer 1's findings are applied to the artifact before Reviewer 2 sees it — produce better final artifact quality than a parallel pipeline — where both reviewers see the original artifact and their findings are aggregated?

### Primary thesis

The sequential pipeline produces higher final quality because each reviewer builds on a progressively better artifact, while the parallel pipeline's aggregation step must reconcile conflicting or partially-overlapping findings. H1-H3 below are the mechanistic sub-hypotheses that explain *why* this holds (or fails).

### Mechanistic sub-hypotheses

**H1 (Overlap):** In parallel review, Reviewer 2 independently rediscovers many of the same defects as Reviewer 1, wasting review capacity on redundant findings.
- *Prediction:* Moderate-to-high overlap (Jaccard similarity >0.3 between R1 and R2 finding sets). Supported by coverage specialization literature — similar prompts attend to similar things. Note: well-differentiated personas may reduce overlap to the 0.3-0.4 range; poorly differentiated personas could push it above 0.5.
- *Metric:* Jaccard similarity (|R1 ∩ R2| / |R1 ∪ R2|) as primary. Directional rates (fraction of R2's findings that duplicate R1's, and vice versa) as secondary.

**H2 (Correction quality):** In sequential review, Reviewer 2 catches errors introduced by the corrections made in response to Reviewer 1's findings — a class of defect that parallel review structurally cannot detect.
- *Prediction:* Non-trivial. Corrections are new code written under time pressure (by the executor); they should have a defect rate comparable to any fresh code.

**H3 (Noise reduction):** Reviewer 2, seeing a clean artifact instead of a draft-with-annotations, allocates attention more effectively and finds defects that would have been masked by the noise of known issues.
- *Prediction:* Moderate effect. Supported by "lost in the middle" attention literature — LLMs have finite attention, and noise competes for it.

---

## Background

### What we do (sequential with fix gates)

```
Code → Reviewer 1 (domain) → Apply ALL fixes → Reviewer 2 (generalist) → Final artifact
```

Each reviewer sees a clean artifact. Reviewer 2 never sees Reviewer 1's notes — only the corrected code. The theory: Reviewer 2 (a) finds different things because they have a different persona/focus, (b) catches mistakes in the corrections, and (c) can focus entirely on the artifact's quality rather than triaging known issues.

### What the industry does (parallel + aggregate)

```
Code → Reviewer 1 ──┐
                     ├── Aggregate/deduplicate → Apply all fixes → Final artifact
Code → Reviewer 2 ──┘
```

Both reviewers see the original code. A synthesis step merges their findings, deduplicates, and resolves conflicts. The theory: maximum coverage in minimum wall-clock time.

### Why neither has been tested

The parallel approach optimizes for throughput (both reviews run simultaneously). The sequential approach optimizes for compounding quality. These are different optimization targets, and the industry chose throughput without measuring the quality tradeoff — likely because human review is expensive enough that parallelism is a clear win on cost. For LLM reviewers, the cost difference is negligible (minutes and tokens), making the quality question the only one that matters.

---

## Experimental Design

### Conditions (3 arms)

| Arm | Name | Pipeline | Description |
|-----|------|----------|-------------|
| **A** | Parallel + aggregate | R1 ‖ R2 → merge → apply | Industry standard. Both reviewers see original artifact. Findings merged by a synthesis agent. All fixes applied at once. |
| **B** | Sequential + fix gates | R1 → fix → R2 → fix | Our architecture. R1 reviews, fixes applied, R2 reviews the corrected artifact, fixes applied. |
| **C** | Sequential, no fix gates | R1 → R2 (with R1's notes) → apply all | Controls for *sequencing* vs *fix gates specifically*. R2 sees both the original code and R1's findings but the code hasn't been corrected yet. Findings combined, then all fixes applied. |

### Why 3 arms

Arm C isolates the fix-gate mechanism. If B > A but C ≈ A, the fix gate (applying corrections before the next review) is the active ingredient, not the sequencing. If B ≈ C > A, then sequencing alone is sufficient and the fix gate is incidental.

**Known confound in Arm C:** R2 in Arm C is explicitly told "a prior reviewer found these issues" and asked to report additional issues and disagreements. This anchors R2 to R1's frame — an effect absent from Arms A (independent review) and B (corrected artifact, no notes). Arm C therefore conflates two variables: sequencing and anchoring. If Arm C underperforms Arm B, the anchoring effect may be partially responsible, not just the absence of fix gates. This confound should be acknowledged when interpreting results. A cleaner variant — where R2 reviews the original code sequentially but without seeing R1's output — would isolate pure sequencing, but adds a 4th arm. We accept the confound in the current design and note it in the analysis.

### Reviewer Configuration

- **Reviewer 1:** Domain-focused persona (security + logic emphasis). Equivalent to "Sid" or domain-expert Patrik.
- **Reviewer 2:** Generalist persona (broad coverage — architecture, error handling, maintainability). Equivalent to generalist Patrik.
- **Synthesis agent (Arm A only):** Reads both review outputs, deduplicates, resolves conflicts, produces a unified findings list.
- **Fix executor:** Applies review findings to the code. Same executor across all arms — the quality of fix execution is a controlled variable.
- **Model:** Claude 3.5 Sonnet for all reviewers and the executor. Same model, same temperature, same token budget per review pass.

### Task Corpus

**Requirement:** Code files with a sufficient density of defects that both reviewers have plenty to find, and defects span multiple categories so that coverage differences are visible.

**Corpus design:**
- **N = 24 code files**, each 150-300 lines. (The effective sample size is the number of unique files, not files × runs. With N=24 and paired tests, we can detect effects of d≈0.6 at 80% power — reasonable for a methodological improvement. The pilot run should be used to estimate actual variance and confirm this is sufficient.)
- **Language:** TypeScript or Python
- **Each file contains 8-12 seeded defects** across categories:
  - Security (R1's expected strength) — 2-3 per file
  - Logic errors (R1's expected strength) — 2-3 per file
  - Performance — 1-2 per file
  - Error handling — 1-2 per file
  - Architecture/maintainability (R2's expected strength) — 1-2 per file
  - Subtle integration issues — 1 per file (the hardest class — requires understanding how components interact)
- **Defect difficulty distribution:** 30% obvious, 40% moderate, 30% subtle
- **No "trick" defects:** Every seeded defect is a genuine problem that a competent reviewer should flag. No gotchas designed to fool the reviewer.

**Defect seeding process:**
- Corpus files should be created blind to which arm is expected to benefit — the creator should focus on realistic, varied defects without optimizing for sequential or parallel detection.
- Each defect's category and difficulty rating should be independently classified by two people. Use the agreed classification; resolve disagreements by discussion. Document the inter-rater agreement rate.
- Difficulty classification should be validated against pilot data — an "obvious" defect to a human may not be obvious to an LLM, and vice versa. Adjust difficulty labels after the pilot if needed.

**Critical addition — correction quality audit (ALL arms):**
After every executor fix step (in every arm), audit corrections against a secondary manifest. This audit runs for ALL arms, not just Arm B, so that review quality and fix quality can be decomposed independently. For each fix step, record:
- **(a) Fix attempted:** Was a correction made for this defect?
- **(b) Fix succeeded:** Did the correction fully resolve the defect?
- **(c) Regression introduced:** Did the correction introduce a new defect?
- **(d) Fix quality:** Is the correction correct but suboptimal?

This lets us decompose the primary outcome (residual defect count) into two components: *review effectiveness* (did the reviewers find it?) and *fix effectiveness* (did the executor resolve it correctly?). Without this decomposition, a win for Arm B could be attributed to either better reviewing or easier fix application — and we wouldn't know which.

For Arm B specifically, the audit also measures H2: can Reviewer 2 catch problems in the corrections applied after Reviewer 1?

**Scoring mechanism:**
- **Automated checks where possible:** For each seeded defect, create a test assertion or static analysis check that detects whether the defect is still present. This is the primary scoring method.
- **Human review for ambiguous cases:** When automated checks are inconclusive (e.g., architectural improvements, code clarity), use human judgment. Two independent scorers evaluate each ambiguous case; report inter-rater agreement (Cohen's kappa).
- **Regression detection:** Run the full test suite on corrected artifacts. Any new test failure indicates a regression. Manual review of diffs for regressions not caught by tests.

### Procedure

**Arm A (Parallel + aggregate):**
1. Fresh session. Present code file to Reviewer 1 with domain persona. Collect findings.
2. Fresh session. Present *same original code file* to Reviewer 2 with generalist persona. Collect findings.
3. Fresh session. Present both sets of findings to synthesis agent. Produce merged findings list.
4. Fresh session. Executor applies all merged findings to the code. Produce corrected artifact.
5. Score corrected artifact against defect manifest.

**Arm B (Sequential + fix gates):**
1. Fresh session. Present code file to Reviewer 1 with domain persona. Collect findings.
2. Fresh session. Executor applies Reviewer 1's findings. Produce intermediate artifact.
3. Audit intermediate artifact for correction quality (secondary manifest).
4. Fresh session. Present *intermediate artifact only* (not original, not R1's notes) to Reviewer 2 with generalist persona. Collect findings.
5. Fresh session. Executor applies Reviewer 2's findings. Produce final artifact.
6. Score final artifact against defect manifest.

**Arm C (Sequential, no fix gates):**
1. Fresh session. Present code file to Reviewer 1. Collect findings.
2. Fresh session. Present *original code file + Reviewer 1's findings* to Reviewer 2. Instruct: "A prior reviewer found the following issues. Review the code, considering their findings. Report any additional issues and any disagreements with their findings."
3. Fresh session. Executor applies combined findings. Produce corrected artifact.
4. Score corrected artifact against defect manifest.

### Measures

**Primary (final artifact quality):**
- **Residual defect count:** Number of seeded defects still present in the final artifact. Lower is better. *This is the headline number.*
- **Defect resolution rate:** Fraction of seeded defects that are correctly resolved in the final artifact.
- **Regression count:** New defects introduced by corrections that survive to the final artifact. Lower is better.

**Secondary (review process):**
- **Unique finding count (per reviewer):** How many distinct true defects each reviewer found.
- **Finding overlap (Arm A):** Jaccard similarity (|R1 ∩ R2| / |R1 ∪ R2|) as the primary overlap metric. Directional rates (fraction of R2's findings duplicating R1's, and vice versa) reported as secondary. Measures H1.
- **Correction quality (all arms):** For each executor fix step: fix attempt rate, fix success rate, regression rate. Decomposes the primary outcome into review effectiveness vs fix effectiveness. See correction quality audit above.
- **Correction-error detection rate (Arm B):** Fraction of executor mistakes caught by R2 in the second review pass. Measures H2.
- **Category coverage:** Which defect categories did each reviewer find? Measures whether the domain/generalist split actually produces complementary coverage.
- **False positive rate per reviewer:** Noise generated by each review pass.

**Tertiary (cost):**
- **Total token usage:** Input + output tokens across all steps in the pipeline.
- **Wall-clock time:** End-to-end time for the full pipeline.
- **Review passes:** Total number of model invocations per pipeline.

**H3 measurement (noise reduction):**
- Compare R2's recall in Arm A (seeing original code) vs Arm B (seeing corrected code) vs Arm C (seeing original + R1's notes). If H3 is correct, R2's recall should be highest in Arm B, where the artifact is cleanest.

### Controls

- **Model:** Claude 3.5 Sonnet for all reviewers, synthesis agent, and executor.
- **Temperature:** 0 (or lowest available). Note: temperature 0 does not guarantee deterministic outputs due to GPU floating-point non-determinism — this is why we run multiple repetitions. Consider whether a small positive temperature (0.2-0.3) better represents production conditions; if the production pipeline uses a higher temperature, match it for ecological validity. At temperature 0, both reviewers are pushed toward the same most-likely outputs, which may artificially inflate overlap in Arm A.
- **Reviewer prompts:** Identical persona descriptions across arms — only the *artifact presented* differs.
- **Executor prompt:** Identical across arms — "Apply these review findings to the code. Make minimal changes to resolve each issue."
- **File order:** Randomized per run. Additionally, randomize arm order per file within each run to control for any sequential processing effects.
- **Runs:** N ≥ 3 complete runs. Each run processes all 24 files × 3 arms = 72 pipeline executions per run. (With 24 unique files, 3 runs provides 72 paired observations — sufficient for the target effect size. Use the pilot to determine whether additional runs are needed based on observed within-file variance.)

---

## Expected Outcomes and Implications

| Result | Implication |
|--------|------------|
| B significantly fewer residual defects than A | Validates our architecture. Sequential + fix gates produces better final quality. |
| B ≈ A | Our architecture doesn't hurt, but the fix-gate overhead isn't justified by quality. Consider switching to parallel for throughput. |
| B < A | Our architecture is actively worse. The synthesis/aggregation step in parallel review is more valuable than compounding. Rethink. |
| C ≈ B > A | Sequencing matters, but fix gates don't. Simplify: let R2 see R1's notes without applying fixes first. |
| C ≈ A < B | Fix gates are the active ingredient, not sequencing. The intermediate correction step is what creates compounding quality. |
| High overlap in A (Jaccard >0.3) | Confirms H1 — parallel review wastes significant capacity on redundant findings. |
| R2 catches correction errors in B | Confirms H2 — this is a unique benefit of sequential review that parallel structurally cannot provide. |
| R2 recall higher in B than A or C | Confirms H3 — clean artifacts improve reviewer attention allocation. |

---

## Cost Estimate

Per run (24 files):
- Arm A: 4 sessions per file (R1, R2, synthesis, executor) × 24 files = 96 API calls
- Arm B: 4 sessions per file (R1, executor, R2, executor) × 24 files = 96 API calls. (The correction audit is human/automated scoring, not an API call.)
- Arm C: 3 sessions per file (R1, R2-with-notes, executor) × 24 files = 72 API calls
- Total per run: 264 API calls

3 runs × 264 calls = 792 API calls
- Each call: ~4000-7000 tokens in (a 200-line file is 3000-5000 tokens + 500-1500 prompt), ~1000-2000 tokens out
- Total: ~5-6M tokens ≈ $15-25 at Sonnet pricing

Human evaluation:
- Scoring 24 final artifacts × 3 arms × 3 runs = 216 artifact evaluations (largely automated via test assertions; human review for ambiguous cases)
- Correction quality auditing across all arms: ~6 hours
- Total human time: ~12 hours evaluation

**Total estimated cost:** ~$25 API + ~20 hours human time (including corpus construction for 24 files)

---

## Statistical Analysis Plan

### Primary analysis

Residual defect count is bounded count data (k defects remaining out of n seeded per file) with a hierarchical structure (defects nested within files, files crossed with arms and runs). The primary model is a **generalized linear mixed model (GLMM)** with:
- **Response:** Residual defects out of total seeded — binomial family (cbind(residual, fixed) ~ ...). Binomial is correct because counts are bounded by the number of seeded defects per file; Poisson assumes unbounded counts and would produce nonsensical predictions exceeding the maximum.
- **Link function:** Logit (default for binomial in lme4::glmer). Pre-registered.
- **Fixed effect:** Arm (A, B, C)
- **Random effects:** File (intercept) and Run (intercept), crossed

### Pre-registered contrasts

1. **Primary contrast:** B vs A (does our architecture beat the industry standard?)
2. **Secondary contrasts:** B vs C (do fix gates matter beyond sequencing?) and A vs C (does sequencing alone help?)
3. **Correction:** Holm-Bonferroni for the 3 pairwise comparisons
4. **Alpha:** 0.05 (two-tailed)

### Secondary analyses

- H1 (overlap): Jaccard similarity computed per file in Arm A, reported as mean ± SD across files and runs
- H2 (correction detection): Proportion of executor errors caught by R2 in Arm B, with 95% CI
- H3 (noise reduction): Compare R2's recall across arms using a GLMM with arm as fixed effect, file and run as random effects
- Correction quality decomposition: Compare fix success rate across arms to determine whether review quality or fix quality drives the primary outcome

### Power analysis

With N=24 unique files, 3 runs, and a paired design (file-level means), a paired t-test on file-level residual defect means has approximately 80% power to detect an effect of d≈0.6 at alpha=0.05. The GLMM will be more powerful than this conservative estimate because it models the full data structure. The pilot run (4 files × 3 arms × 1 run) should be used to estimate the actual variance components and confirm adequacy.

### Minimum detectable effect

We consider a clinically meaningful effect to be a reduction of ≥1.5 residual defects per file (out of 8-12 seeded). Effects smaller than this, while statistically interesting, may not justify the throughput cost of sequential review in practice.

---

## Limitations

1. **Executor quality is a confound.** If the executor applies fixes poorly, Arm B benefits (R2 catches the bad fixes) while Arm A doesn't get that chance. This is arguably a *feature* of the sequential design, not a confound — but it means the experiment conflates "sequential review is better" with "correction auditing is valuable." Arm C helps disentangle this.

2. **Synthesis agent quality affects Arm A.** A poor synthesis agent makes parallel review look worse than it could be. Mitigate by using a well-prompted synthesis agent and documenting its merge logic.

3. **Seeded defects, not natural ones.** Same limitation as the persona experiment. Mitigate with realistic, varied defects.

4. **Two reviewers only.** Our production pipeline sometimes uses 3+ reviewers (domain → generalist → ambition backstop). This experiment tests the 2-reviewer case. Extensions to 3+ are future work.

5. **No project context.** Production reviews happen with CLAUDE.md, prior history, and project knowledge. This experiment strips all of that. The sequential advantage may be larger or smaller in context — larger if context compounds across review passes, smaller if context itself provides the "clean artifact" benefit H3 posits.

6. **Arm C anchoring confound.** R2 in Arm C is explicitly shown R1's findings, which anchors R2 to R1's frame. This effect is absent from Arms A and B. Arm C therefore conflates sequencing with anchoring. See the "Why 3 arms" section for discussion. A cleaner 4th arm (R2 reviews original code sequentially, without R1's output) would isolate pure sequencing but is deferred for this iteration.

7. **Defect difficulty construct validity.** The 30/40/30 obvious/moderate/subtle split is experimenter-judged. An "obvious" defect to a human may not be obvious to an LLM. Pilot data should be used to validate and adjust difficulty labels.

---

## Relationship to Other Experiments

- **Persona Review A/B experiment** (separate spec) should run first. If persona review shows no benefit over vanilla, the reviewer quality in *this* experiment is the same across arms — which is fine (the arms test architecture, not persona quality). But if persona review shows a large effect, this experiment's results become more interesting because the reviewers are finding more, creating more room for overlap and correction effects.
- **Handoff vs Compaction experiment** (2026-03-21 addendum) is orthogonal but could share corpus infrastructure.

---

## Next Steps

1. [ ] PM review and approve/modify this spec
2. [ ] Build the defect corpus (24 files + primary manifest, with independent dual-classification of defect category and difficulty)
3. [ ] Design the correction-quality audit template (runs for all arms)
4. [ ] Build automated scoring harness (test assertions per seeded defect + regression detection)
5. [ ] Build the synthesis agent prompt (Arm A)
6. [ ] Build the executor prompt (shared across arms)
7. [ ] Run pilot (4 files × 3 arms × 1 run) to validate methodology, estimate variance components, and calibrate difficulty labels
8. [ ] Formal power analysis from pilot variance estimates — confirm N=24 is sufficient or adjust
9. [ ] Full run (3 runs × 24 files × 3 arms)
10. [ ] Analysis per pre-registered statistical plan and write-up
