# Deep Research

> Referenced by `/deep-research` and `/structured-research`. This is a pipeline definition, not an invocable skill.

## Overview

Three pipelines for deep investigation, all using escalating model capability:

- **Repo Research** — study a repository, understand it on its own merits, optionally compare against your project. Single linear pipeline with an optional comparison phase.
- **Internet Research** — investigate a topic across web sources with multi-agent verification.
- **Structured Research** — fulfill a research spec with structured output. Input is a spec file declaring subjects, topics, acceptance criteria, output schema, and quality gates. Output is schema-conforming data, not prose.

**Core principle:** Each model tier does what it's best at. Haiku is fast and cheap for mechanical work (indexing files, filtering). Sonnet is analytical (reading deeply, evaluating architecture, comparing implementations). Opus has the highest judgment (cross-referencing, prioritizing, making architectural calls). Don't waste expensive models on cheap work; don't trust cheap models with judgment calls.

**Key design principle:** Assessment and comparison are decoupled. The assessment (Phases 0-2) is evergreen — it describes what the repo does and how, independent of your project's state. The comparison (Phase 3) is point-in-time and optional — it diffs the assessment against your current implementation. You can re-run Phase 3 cheaply as your project evolves without re-researching the reference repo. You can also skip Phase 3 entirely if there's no target repo to compare against yet.

**Announce at start:** "I'm running `/deep-research` to run [a repo assessment of X / a repo assessment + comparison of X / internet research on Y / structured research from spec Z]."

## When to Use

**Repo Research:**
- Studying an open-source repository to understand its architecture, patterns, and design decisions
- Building a reusable knowledge base about a reference implementation
- Evaluating a library or framework's internal design quality
- Auditing implementation fidelity after porting from a reference (include Phase 3)
- Investigating runtime behavior that doesn't match expectations (include Phase 3)
- Re-comparing after your project evolves significantly (re-run Phase 3 only)

**Internet Research:**
- Need verified, multi-source understanding of a technical topic
- Evaluating competing approaches or libraries with specific trade-offs
- Researching best practices where training knowledge may be outdated
- Building a knowledge base on a domain before implementation

**Not for:** Quick lookups (use Context7), single-source documentation reads, or questions answerable from one search.

**Structured Research:**
- Batch research across multiple subjects with the same topic areas and output schema
- Fulfilling a research spec with acceptance criteria and quality gates
- Incremental campaigns — research N subjects per session, resume next session
- Collecting structured data (not prose) from web sources against a known schema
- Re-verifying existing data against fresh sources

## The One-Line Bug Principle (Phase 3 — Comparison)

The highest-value comparison findings are code that **exists but is disconnected**:

1. Code that exists but is never called from the right place
2. Data that is computed but fed to the wrong downstream consumer
3. Mechanisms present in isolation but disconnected from the pipeline
4. Configuration values that agree by coincidence but have no enforcement

Surface-level research ("does our project have X? yes") cannot find these. Only comparison against a reference that implements the connected pipeline exposes the missing link.

## The Fix-Forward Default

**This is research for fixing things, not deferring things.**

With LLM-assisted implementation, the cost of doing the work is lower than the cost of carrying the debt. Every finding that survives cross-reference gets a tier and effort estimate. Nothing goes into a vague "future work" bucket.

---

# Pipeline A: Repo Research

## Phase Pipeline — STRICT SEQUENCE

```
Phase 0 → [wait] → Phase 1 → [wait for ALL] → Phase 2 → [wait for ALL] → Phase 3 (optional) → [wait for ALL] → Phase 4 → Phase 5
```

**Phases MUST run sequentially.** Each phase's output shapes the next phase's prompts.

**Phase 3 is optional.** If there's no target repo to compare against, or if comparison is deferred to a later session, skip straight from Phase 2 to Phase 4. The assessment (Phases 0-2) stands on its own.

---

### Phase 0: Scope Definition (Coordinator)

**Model:** Coordinator (Opus). **Time:** ~5 min.

1. **Read the README** — Understand the repo's purpose, scope, and architecture from its own documentation
2. **Pin the version** — Record the repo's current version (latest git tag, release number, or commit hash). This is the anchor for all future revisits — we diff from here and read release notes between versions instead of re-surveying from scratch.
3. **Survey repo structure** — 2-3 `ls` commands on the target repo
4. **Define chunk boundaries** — Split target repo into 4-6 domain-aligned chunks based on the repo's own architecture
5. **Write focus questions** — What are the key design decisions? What patterns does this repo use? What are its architectural strengths?
6. **Generate run ID** — format: `YYYY-MM-DD-HHhMM` (current timestamp). This identifies the scratch directory for all phases: `tasks/scratch/deep-research/{run-id}/`
7. **If Phase 3 will run:** Also identify comparison targets — for each chunk, list project files implementing equivalent functionality

**Output:** Chunk table with version header (see agent-prompts.md).

---

### Phase 1: File & Directory Mapping (Haiku agents, parallel)

**Model:** Haiku. **Dispatch:** All chunks simultaneously.

Each agent reads every file in its chunk and produces:
- File path, line count, key structs/functions with signatures
- Actual numeric constant values (not just names)
- Data flow: what each function consumes, produces, who calls it
- Cross-subsystem connections

**Why Haiku:** Mechanical file reading requires no judgment. Haiku is 10x cheaper than Sonnet and the output quality is fully sufficient for directing Phase 2.

**DISPATCH:** Open `agent-prompts.md` in this directory. Copy the **Phase 1: Haiku File Mapping Prompt** template verbatim. Fill in the bracketed fields: `[REPO NAME]`, `[CHUNK LETTER]`, `[CHUNK DESCRIPTION]`, `[LIST OF DIRECTORIES/FILES]`. Dispatch that. Do NOT write a custom prompt — the template's structure (especially "completeness matters more than analysis") prevents Haiku from confabulating analysis it isn't qualified to produce.

**Scratch path:** `tasks/scratch/deep-research/{run-id}/{chunk-letter}-phase1-haiku.md`. Pass this as `[SCRATCH_PATH]` in the template. Instruct the agent in its prompt text to use the Write tool to save output here. (The Agent tool has no `tools` parameter — tool guidance goes in the prompt.)

**Scratch verification:** Before proceeding to Phase 2, verify all expected scratch files exist (`ls tasks/scratch/deep-research/{run-id}/*-phase1-haiku.md`). If any are missing, re-dispatch the failed agent once. If it fails again, skip that chunk and note the gap in the Phase 4 synthesis.

---

### Phase 2: Standalone Analysis (Sonnet agents, parallel)

**Model:** Sonnet. **Input:** Phase 1 inventory per chunk (read from `tasks/scratch/deep-research/{run-id}/{chunk-letter}-phase1-haiku.md`).

Each agent reads the repo files deeply and produces per domain area:
```
### [Area Name]
**Implementation:** [description with file:line refs, actual values]
**Design Pattern:** [what pattern is used and why it works]
**Data Flow:** [how data moves through this area, with specifics]
**Strengths:** [what this implementation does well]
**Limitations:** [trade-offs, edge cases, or constraints]
**Notable Details:** [non-obvious implementation choices worth understanding]
```

**Critical instruction:** "Research only — no code changes. Assess the repo on its own merits. Do NOT compare against any other project. Focus on: what does this code do, how does it do it, why are these design decisions good or bad?"

**DISPATCH:** Open `agent-prompts.md`. Copy the **Phase 2: Sonnet Standalone Analysis Prompt** template verbatim. Fill in `[REPO NAME]`, `[CHUNK DESCRIPTION]`, and read the Phase 1 output from the scratch file and paste it where indicated. Do NOT write a custom prompt — the template's "Rules" section encodes critical guardrails (no comparison, file:line references, actual values).

**Scratch path:** `tasks/scratch/deep-research/{run-id}/{chunk-letter}-phase2-sonnet.md`. Pass this as `[SCRATCH_PATH]` in the template. Instruct the agent in its prompt text to use the Write tool to save output here. (The Agent tool has no `tools` parameter — tool guidance goes in the prompt.)

**Output:** Domain-specific analysis reports — the raw material for synthesis.

**Scratch verification:** Before proceeding to Phase 3 (or Phase 4 if skipping comparison), verify all expected Phase 2 scratch files exist. Re-dispatch once on failure; skip chunk on second failure.

---

### Phase 3: Comparison (Sonnet agents, parallel) — OPTIONAL

**Model:** Sonnet. **Input:** Phase 2 analysis per chunk (read from `tasks/scratch/deep-research/{run-id}/{chunk-letter}-phase2-sonnet.md`) + project files to compare against.

**When to include:** When you have a target project to compare against AND comparison is in scope for this session.

**When to skip:** When you're just building a knowledge base, when there's no target project yet, or when comparison is deferred to a later session. Skip straight to Phase 4.

Each agent reads the **project files** (not the reference — Phase 2 already analyzed that) and compares:
```
### [Area Name]
**[Reference]:** [from Phase 2 analysis — architecture, patterns, values]
**[Project]:** [from project files — with file:line refs, actual values]
**Gap Assessment:** [specific divergence]
**Risk Level:** [LOW/MEDIUM/HIGH/CRITICAL] — [why]
```

**Critical instruction:** "Research only — no code changes. Read project files thoroughly. Find actual constants. State explicitly when a mechanism is absent. Use the Phase 2 analysis as your reference for the target repo — don't re-read the reference repo source files."

**DISPATCH:** Open `agent-prompts.md`. Copy the **Phase 3: Sonnet Comparison Prompt** template verbatim. Fill in `[REPO NAME]`, `[PROJECT NAME]`, `[CHUNK DESCRIPTION]`, read the Phase 2 output from the scratch file and paste it, and list the project files. Do NOT write a custom prompt — the template's "Look specifically for" checklist (disconnected code, wrong consumers, coincidental values) encodes the One-Line Bug Principle.

**Scratch path:** `tasks/scratch/deep-research/{run-id}/{chunk-letter}-phase3-sonnet.md`. Pass this as `[SCRATCH_PATH]` in the template. Instruct the agent in its prompt text to use the Write tool to save output here. (The Agent tool has no `tools` parameter — tool guidance goes in the prompt.)

**Scratch verification:** If Phase 3 ran, verify all expected Phase 3 scratch files exist before proceeding to Phase 4. Re-dispatch once on failure; skip chunk on second failure.

---

### Phase 4: Synthesis (Opus, single agent)

**Model:** Opus. **Input:** ALL Phase 2 reports (read from `tasks/scratch/deep-research/{run-id}/*-phase2-sonnet.md`) and Phase 3 reports if they exist (read from `*-phase3-sonnet.md`).

**If assessment only (no Phase 3):**

Cross-references all domain analyses and produces a comprehensive standalone assessment:
- **Architecture overview** — how the system is structured and why
- **Key patterns** — recurring design decisions and their rationale
- **Data flow map** — how data moves through the system end-to-end
- **Strengths** — what this repo does well and why
- **Limitations** — trade-offs, constraints, known weaknesses
- **Notable implementation details** — non-obvious choices worth understanding

**Output:** `<REPO>-ASSESSMENT.md` — an evergreen document describing the repo on its own terms, with the assessed version pinned in the header.

**If comparison included (Phase 3 ran):**

Also cross-references comparison findings, deduplicates, validates risk levels, and prioritizes into tiers:
- **Tier 0 (hours):** Actively wrong. Trivial fixes.
- **Tier 1 (days):** High-impact architecture additions.
- **Tier 2 (weeks):** Fidelity gaps for production quality.
- **Tier 3 (sprint):** Foundational infrastructure.

**Output:** `<REPO>-ASSESSMENT.md` (evergreen, version-pinned) + `<REPO>-GAP-ANALYSIS.md` (point-in-time comparison, version-pinned). Both documents are produced — the assessment is never merged into the gap analysis.

**DISPATCH:** Open `agent-prompts.md`. Copy the appropriate **Phase 4** template (assessment-only or with-comparison). Fill in `[N]`, `[REPO NAME]`, `[PROJECT NAME]`, and paste all Phase 2/3 reports. Do NOT write a custom synthesis prompt — the template's tier definitions and "do NOT classify as could defer" rule prevent the most common Opus failure mode (over-softening findings).

---

### Phase 5: Coordinator Discussion (EM + PM)

The coordinator (EM) presents findings to the PM for discussion:

- **Assessment summary** — what did we learn about this repo?
- **Key architectural insights** — patterns worth adopting, approaches worth studying
- **If comparison ran:** prioritized gap findings with tiers and effort estimates
- **Recommended next steps** — what to implement, what to investigate further, what to defer

This is a conversation, not an automated step. The PM makes scope and prioritization decisions. The EM proposes; the PM disposes.

---

### Phase 5.5: Scratch Triage (Coordinator)

After synthesis is complete and the PM discussion has concluded:

1. **Default: DELETE all scratch files.** Phase 1 (Haiku) output was consumed by Phase 2. Phase 2 (Sonnet) was consumed by Phase 4. Phase 3 (Sonnet) was consumed by Phase 4. The durable artifacts are the assessment and gap analysis documents.

2. **Exception — keep Phase 2 if assessment-only and comparison deferred:** If Phase 3 was skipped and comparison will happen in a future session, keep Phase 2 files (move to `tasks/scratch/deep-research/kept/` with a header noting the expiry: 30 days). The 30-day expiry is advisory — the next deep-research run for the same repo should check `kept/` and clean up expired files. No automated enforcement exists.

3. **Clean up:** `rm -rf tasks/scratch/deep-research/{run-id}/` (or move kept files first).

---

# Pipeline B: Internet Research

## Phase Pipeline — STRICT SEQUENCE

```
Phase 0 → [wait] → Phase 1 → [wait for ALL] → Phase 2 → [wait for ALL] → Phase 3
```

---

### Phase 0: Research Framing (Coordinator, ~5 min)

1. **Define the research question** — What specifically do we need to know? What will we do with the answer?
2. **Identify search domains** — 3-6 topic areas to investigate (these become the chunks)
3. **List known sources** — Documentation, libraries, prior art already known
4. **Write focus questions** — What trade-offs matter? What constraints does our project have? What claims need verification?

**Output:** Research brief (use the **Research Brief Template** from `agent-prompts.md`).

### Phase 1: Broad Discovery (Haiku agents, parallel)

**Model:** Haiku. **Tools:** WebSearch, WebFetch, Context7.
**Dispatch:** One agent per topic area, all simultaneously.

Each agent:
- Runs 3-5 web searches per topic area using varied search terms
- Skims results and catalogs what's available
- Filters for relevance and quality (official docs > blog posts > forums)
- Notes which sources contradict each other
- Flags sources that need deeper reading by Sonnet

**DISPATCH:** Open `agent-prompts.md`. Copy the **Phase 1: Haiku Broad Discovery Prompt** template verbatim. Fill in `[TOPIC AREA LETTER]`, `[TOPIC DESCRIPTION]`, `[ANY KNOWN URLS/DOCS]`, `[WHAT SPECIFICALLY DO WE NEED TO KNOW]`. The template's "You are FILTERING, not analyzing" instruction prevents Haiku from producing unverified analysis. Do NOT write a custom prompt.

**Scratch path:** `tasks/scratch/deep-research/{run-id}/{topic-letter}-phase1-haiku.md`. Pass this as `[SCRATCH_PATH]` in the template. Instruct the agent in its prompt text to use the Write tool to save output here. (The Agent tool has no `tools` parameter — tool guidance goes in the prompt.)

**Output per agent:**
```
### [Topic Area]
**Sources found:** [ranked list with URLs and 1-line descriptions]
**Key claims (unverified):** [bullet list of notable findings]
**Contradictions:** [where sources disagree]
**Recommended for deep read:** [top 3-5 sources that need Sonnet analysis]
**Search terms used:** [for reproducibility]
```

**Scratch verification:** Before proceeding to Phase 2, verify all expected Phase 1 scratch files exist. Re-dispatch once on failure; skip that topic on second failure.

#### Phase 1.5: Scout Output Quality Gate (Haiku agents, parallel)

After scratch verification passes, dispatch a **Haiku agent per topic** to verify the quality of Phase 1 scout output before Sonnet invests in deep reads. Each Haiku agent reads its topic's Phase 1 file and checks:

1. **Source count** — does the file list ≥3 distinct sources? (Fewer suggests shallow or failed searches)
2. **Template compliance** — does it have the required sections (Sources found, Key claims, Contradictions, Recommended for deep read)?
3. **Contradiction flagging** — are contradictions explicitly noted, or is the output a flat list with no critical assessment?
4. **URL validity** — are the "Recommended for deep read" entries actual URLs, not hallucinated references?

**Verdicts per topic:**
- **PASS** — proceed to Phase 2
- **THIN** — fewer than 3 sources or missing sections; re-dispatch the Phase 1 Haiku scout with revised search terms, then re-check
- **FAIL** — empty, garbled, or entirely hallucinated output; re-dispatch Phase 1 scout once, skip topic on second failure

**Why:** Phase 1 Haiku scouts can produce shallow or hallucinated output silently. Without this gate, Sonnet Phase 2 agents waste tokens reading bad input and producing unreliable analysis. The gate costs ~1 minute of Haiku time per topic and catches the ~1-in-4 failure rate observed in AI-generated content.

#### Phase 1.5b: Cross-Pollination (Coordinator)

After all Phase 1 topics pass the quality gate, the coordinator reads ALL Phase 1 outputs and performs cross-pollination before dispatching Phase 2:

1. **Cross-topic findings:** Identify findings from Topic X that should change the focus for Topic Y's Phase 2 deep-read. Example: if Topic A's discovery reveals that a library was deprecated, Topic B's Phase 2 should know this before deep-reading sources that reference it.

2. **Shared search terms:** Note search terms discovered in one topic that are relevant to another. Include these as "additional search terms to try" in the Phase 2 dispatch for the relevant topic.

3. **Cross-topic contradictions:** Flag where different topics' Phase 1 outputs contradict each other. Add these as explicit contradiction-resolution tasks in the relevant Phase 2 dispatches.

4. **Adjust Phase 2 prompts accordingly:** When dispatching Phase 2 agents, append a "Cross-Pollination Context" section to each agent's prompt with the relevant findings from other topics. Format:

```
## Cross-Pollination Context (from other topic areas)
- [Topic X] found that [relevant finding] — consider this when evaluating [specific aspect]
- [Topic Y] and [Topic Z] contradict on [specific claim] — try to resolve from your sources
```

**Cost:** Near-zero. The coordinator already reads all Phase 1 outputs for the quality gate. This extends that read to also inform Phase 2 dispatch. No additional agent dispatches needed.

### Phase 2: Analytical Deep-Read (Sonnet agents, parallel)

**Model:** Sonnet. **Tools:** WebFetch, Context7, Read.
**Input:** Phase 1 discovery report per topic (read from `tasks/scratch/deep-research/{run-id}/{topic-letter}-phase1-haiku.md`).

Each agent:
- Reads the recommended sources in full (WebFetch for web pages, Context7 for library docs)
- Extracts specific facts, code patterns, API signatures, configuration values
- Verifies or refutes the claims Haiku flagged
- Notes consensus vs. minority positions

**Output per agent:**
```
### [Topic Area]
**Verified findings:** [specific, cited facts]
**Refuted claims:** [what Phase 1 flagged that turned out wrong, and why]
**Key insights:** [non-obvious learnings]
**Recommendations:** [specific actions for our project]
**Confidence level:** [HIGH/MEDIUM/LOW per finding — based on source quality and consensus]
**Sources cited:** [URLs with specific sections referenced]
```

**Critical instruction:** "Verify, don't trust. If Phase 1 flagged a claim, find the primary source. If sources disagree, say so explicitly with the evidence each side presents. Do not average contradictions into a vague 'it depends.'"

For complex topics (5+ sources or contradictions present), Phase 2 agents also produce a
structured claims table. This gives Phase 3 Opus structured data to work with rather than
only prose paragraphs, improving synthesis rigor for topics where source quality varies.

**DISPATCH:** Open `agent-prompts.md`. Copy the **Phase 2: Sonnet Analytical Deep-Read Prompt** template verbatim. Fill in `[TOPIC DESCRIPTION]`, read Phase 1 output from the scratch file and paste it, add project context. Do NOT write a custom prompt — the template's verification structure (verified/refuted/contradictions resolved) is the core value of Phase 2.

**Scratch path:** `tasks/scratch/deep-research/{run-id}/{topic-letter}-phase2-sonnet.md`. Pass this as `[SCRATCH_PATH]` in the template. Instruct the agent in its prompt text to use the Write tool to save output here. (The Agent tool has no `tools` parameter — tool guidance goes in the prompt.)

**Scratch verification:** Before proceeding to Phase 3, verify all expected Phase 2 scratch files exist. Re-dispatch once on failure; skip that topic on second failure.

### Phase 3: Research Synthesis (Opus, single agent)

**Model:** Opus. **Input:** ALL Phase 2 reports (read all Phase 2 reports from scratch files: `tasks/scratch/deep-research/{run-id}/*-phase2-sonnet.md`).

1. **Cross-references** findings across topic areas — identifies reinforcing or contradictory evidence
2. **Evaluates source quality** — primary docs > peer-reviewed > well-maintained OSS > blog posts > forums
3. **Resolves contradictions** — when sources disagree, makes a judgment call with reasoning
4. **Produces actionable recommendations** prioritized by confidence and impact
5. **Identifies knowledge gaps** — what we still don't know and how to find out

**Output:** `<TOPIC>-RESEARCH-SYNTHESIS.md` with:
- Executive summary (3-5 sentences)
- Findings organized by topic area
- Recommendations with confidence levels
- Open questions and suggested next steps
- Full source bibliography

**DISPATCH:** Open `agent-prompts.md`. Copy the **Phase 3: Opus Research Synthesis Prompt** template verbatim. Fill in `[N]`, `[RESEARCH QUESTION]`, read all Phase 2 reports from scratch files and paste them, add project context. Do NOT write a custom prompt.

---

### Phase 3.5: Scratch Triage (Coordinator)

After synthesis is complete and the PM discussion has concluded:

1. **Default: DELETE all scratch files.** Phase 1 (Haiku) output was consumed by Phase 2. Phase 2 (Sonnet) was consumed by Phase 3. The durable artifact is the research synthesis document.

2. **Clean up:** `rm -rf tasks/scratch/deep-research/{run-id}/`

---

# Pipeline C: Structured Research

> Pipeline C is documented in `PIPELINE-C.md` in this directory. Referenced by `/structured-research`.

---

# Common Failure Modes

| Failure | Pipeline | Prevention |
|---------|----------|------------|
| Running phases in parallel | Both | Each phase shapes the next. Sequential = cheaper AND better. |
| Mixing assessment and comparison in Phase 2 | Repo | Phase 2 is standalone analysis. No references to your project. Comparison is Phase 3. |
| Skipping Phase 2 and going straight to comparison | Repo | Assessment is always the foundation. You cannot compare well without understanding first. |
| Over-softening findings | Repo | Every real finding gets a tier + effort. Nothing deferred without a tier. |
| Scope too narrow | Both | Best findings are often in unexpected domains. Survey broadly. |
| Not reading project files in Phase 3 | Repo | "Read project files. Find actual constants. State explicitly when absent." |
| Trusting Haiku's claims | Internet | Haiku filters — it does NOT verify. Sonnet verifies. |
| Averaging contradictions | Internet | "Sources A and B disagree" is better than a false synthesis. |
| Opus says "could defer" | Repo | Tier 2 (weeks) ≠ defer. Tiers are sequencing, not filtering. |
| Re-reading reference repo in Phase 3 | Repo | Use the Phase 2 analysis as input. Don't re-read source files. |
| Writing custom dispatch prompts | Both | Templates in `agent-prompts.md` are tested infrastructure. Copy verbatim, fill blanks. Custom prompts lose guardrails silently — Haiku confabulates, Sonnet scope-bleeds, Opus over-softens. |
| Agreeing to use templates then not using them | Both | The EM has been observed agreeing 5 times then writing custom prompts anyway. The DISPATCH blocks at each phase are not suggestions. |

**Pipeline C failure modes:** See `PIPELINE-C.md` — Common Failure Modes section.

# Cost Profile

| Pipeline | Phases | Agents | Wall-Clock |
|----------|--------|--------|------------|
| Repo (assessment only, Phases 0-2-4-5) | 4 | ~4-8 Haiku + 4-6 Sonnet + 1 Opus | ~20 min |
| Repo (with comparison, Phases 0-3-4-5) | 5 | ~4-8 Haiku + 8-12 Sonnet + 1 Opus | ~30 min |
| Repo (re-run comparison only, Phases 3-4-5) | 3 | ~4-6 Sonnet + 1 Opus | ~15 min |
| Internet Research (Phases 0-3) | 4 | ~4-8 Haiku + 4-6 Sonnet + 1 Opus | ~20 min |

**Pipeline C cost profile:** See `PIPELINE-C.md` — Cost Profile section.

Phase 3 (comparison) is cheaper in practice because Sonnet agents have the Phase 2 analysis pre-digested — they don't need to understand the reference repo from scratch.

# Integration

- **REQUIRED BACKGROUND:** coordinator:dispatching-parallel-agents for Phase 1, 2, and 3 dispatch
- Phase 4 output feeds directly into coordinator:writing-plans for implementation planning
- `<REPO>-ASSESSMENT.md` is evergreen and can be shared across projects — version-pinned so revisits start from `git diff v1.2..v1.5` + release notes, not a full re-survey
- `<REPO>-GAP-ANALYSIS.md` is point-in-time — re-run Phase 3+4 when your project evolves
- Phase 3 can be run in a later session using an existing assessment as input
- **All dispatch prompts use templates from `agent-prompts.md` — verbatim, with blanks filled in.** The templates are tested infrastructure, not suggestions. Writing custom prompts discards guardrails that prevent known failure modes (Haiku confabulation, missing file:line refs, scope bleed between phases). If a template genuinely doesn't fit, say so explicitly before deviating.
- **Pipeline C integration:** See `PIPELINE-C.md` — Integration section.
