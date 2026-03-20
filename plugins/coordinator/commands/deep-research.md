---
description: "Run a deep research pipeline on a repository (Pipeline A) or a topic across internet sources (Pipeline B). Use for studying codebases, building knowledge bases, evaluating libraries, or investigating multi-source technical topics with verified findings. For structured research with batch subjects and output schemas, use /structured-research instead."
allowed-tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent", "WebSearch", "WebFetch"]
argument-hint: "'repo' <repo-path> [--compare <project-path>] | 'web' <topic>"
---

# Deep Research — Pipelines A and B

Deep investigation via escalating model capability: Haiku for mechanical work, Sonnet for analysis, Opus for synthesis. Two pipelines:

- **Pipeline A (Repo Research)** — study a repository on its own merits, optionally compare against your project
- **Pipeline B (Internet Research)** — investigate a topic across web sources with multi-agent verification

**Not for:** Quick lookups (use Context7), single-source documentation reads, or structured batch research across many entities (use `/structured-research`).

**Reference:** Full pipeline design in `plugins/coordinator/pipelines/deep-research/PIPELINE.md`. Agent prompt templates in the same directory's `agent-prompts.md`.

**Announce at start:** "I'm running `/deep-research` to run [a repo assessment of X / a repo assessment + comparison of X against Y / internet research on Z]."

---

## Arguments

`$ARGUMENTS` determines the pipeline and mode.

### Explicit sub-commands

**`/deep-research repo <repo-path> [--compare <project-path>]`**
Run Pipeline A. `<repo-path>` is the path to the repository root. Optional `--compare <project-path>` enables Phase 3 comparison against your project.

**`/deep-research web <topic>`**
Run Pipeline B. `<topic>` is the research question or topic string.

### Auto-detection (no sub-command)

**`/deep-research <argument>`** with no explicit sub-command:
- If `<argument>` is a path that exists on disk → **repo mode** (Pipeline A, no comparison)
- Otherwise → **web mode** (Pipeline B, treating the argument as the topic)

### Examples

```
/deep-research repo /repos/onnxruntime
/deep-research repo /repos/onnxruntime --compare /projects/myengine/src
/deep-research web "transformer inference optimization techniques"
/deep-research /repos/langchain               # auto-detected: repo
/deep-research gRPC streaming backpressure    # auto-detected: web
```

---

## Pipeline A: Repo Research

### Phase sequence (STRICT)

```
Phase 0 → [wait] → Phase 1 → [wait for ALL] → Phase 2 → [wait for ALL] → Phase 3 (optional) → [wait for ALL] → Phase 4 → Phase 5 → Phase 5.5
```

**Phases MUST run sequentially.** Each phase's output shapes the next phase's prompts. Do not begin the next phase until all agents in the current phase have completed and their scratch files verified.

---

### Phase 0: Scope Definition (Coordinator, ~5 min)

1. **Read the README** — understand the repo's purpose, scope, and architecture
2. **Pin the version** — record the repo's current version (latest git tag, release number, or commit hash). This is the baseline for all future revisits.
3. **Survey repo structure** — 2-3 `ls` commands on the target repo
4. **Define chunk boundaries** — split the repo into 4-6 domain-aligned chunks based on its own architecture
5. **Write focus questions** — what are the key design decisions? what patterns does this repo use? what are its architectural strengths?
6. **Generate run ID** — format: `YYYY-MM-DD-HHhMM`. This names the scratch directory: `.claude/scratch/deep-research/{run-id}/`
7. **If Phase 3 will run:** also identify comparison targets — for each chunk, list the project files implementing equivalent functionality

**Output:** Chunk table using the **Chunk Table Template** from `agent-prompts.md`:

> **Repo:** [name] | **Version:** [tag/release/commit hash] | **Date:** [YYYY-MM-DD]

| Chunk | Target Repo Scope | Focus Question |
|-------|-------------------|----------------|
| A | [directories/files] | [what are we looking at?] |

If comparison will run, add a "Project Comparison Target" column.

---

### Phase 1: File & Directory Mapping (Haiku agents, parallel)

**Model:** Haiku. **Dispatch:** All chunks simultaneously.

**DISPATCH:** Open `agent-prompts.md`. Find **"Phase 1: Haiku File Mapping Prompt"**. Copy verbatim. Fill in:
- `[REPO NAME]` — repository name
- `[CHUNK LETTER]` — A, B, C, etc.
- `[CHUNK DESCRIPTION]` — from Phase 0 chunk table
- `[LIST OF DIRECTORIES/FILES]` — from Phase 0 chunk table
- `[SCRATCH_PATH]` — `.claude/scratch/deep-research/{run-id}/{chunk-letter}-phase1-haiku.md`

Include `Write` in each agent's tool list. Dispatch with `run_in_background: true`. Do NOT write custom prompts — the template's "completeness matters more than analysis" instruction prevents Haiku confabulation.

**Scratch verification:** Before proceeding to Phase 2, verify all expected files exist (`ls .claude/scratch/deep-research/{run-id}/*-phase1-haiku.md`). Re-dispatch the failed agent once on missing files. If it fails again, skip that chunk and note the gap for Phase 4.

---

### Phase 2: Standalone Analysis (Sonnet agents, parallel)

**Model:** Sonnet. **Input:** Phase 1 inventory per chunk (read from scratch).

**DISPATCH:** Open `agent-prompts.md`. Find **"Phase 2: Sonnet Standalone Analysis Prompt"**. Copy verbatim. Fill in:
- `[REPO NAME]`
- `[CHUNK DESCRIPTION]` — from Phase 0 chunk table
- `[PASTE PHASE 1 OUTPUT HERE]` — read from `.claude/scratch/deep-research/{run-id}/{chunk-letter}-phase1-haiku.md`
- `[SCRATCH_PATH]` — `.claude/scratch/deep-research/{run-id}/{chunk-letter}-phase2-sonnet.md`

Include `Write` in each agent's tool list. Dispatch with `run_in_background: true`. Do NOT write custom prompts — the template's "Rules" section encodes critical guardrails (no comparison, file:line references, actual constant values).

**Critical:** Phase 2 is assessment only. Agents must NOT compare against any other project. Comparison is Phase 3.

**Scratch verification:** Before proceeding to Phase 3 (or Phase 4 if skipping comparison), verify all expected Phase 2 files exist. Re-dispatch once on failure; skip chunk on second failure.

---

### Phase 3: Comparison (Sonnet agents, parallel) — OPTIONAL

**When to include:** When `--compare <project-path>` was provided and comparison is in scope.
**When to skip:** No target project, or comparison deferred to a later session. Skip straight to Phase 4.

**Model:** Sonnet. **Input:** Phase 2 analysis per chunk + project files to compare against.

**DISPATCH:** Open `agent-prompts.md`. Find **"Phase 3: Sonnet Comparison Prompt (OPTIONAL PHASE)"**. Copy verbatim. Fill in:
- `[REPO NAME]`
- `[PROJECT NAME]`
- `[CHUNK DESCRIPTION]`
- `[PASTE PHASE 2 OUTPUT FOR THIS CHUNK]` — read from `.claude/scratch/deep-research/{run-id}/{chunk-letter}-phase2-sonnet.md`
- `[LIST OF SPECIFIC PROJECT FILES WITH FULL PATHS]` — from Phase 0 comparison targets
- `[SCRATCH_PATH]` — `.claude/scratch/deep-research/{run-id}/{chunk-letter}-phase3-sonnet.md`

Include `Write` in each agent's tool list. Dispatch with `run_in_background: true`. Do NOT write custom prompts — the template's "Look specifically for" checklist encodes the One-Line Bug Principle (code that exists but is disconnected, data fed to wrong consumers, mechanisms present in isolation).

**Critical:** Agents read project files, NOT the reference repo — Phase 2 already analyzed the reference. Use Phase 2 analysis as the reference input.

**Scratch verification:** Verify all expected Phase 3 files exist before proceeding to Phase 4. Re-dispatch once on failure; skip chunk on second failure.

---

### Phase 4: Synthesis (Opus, single agent)

**Model:** Opus. **Input:** ALL Phase 2 reports + Phase 3 reports if they exist.

**DISPATCH:** Open `agent-prompts.md`. Choose the appropriate template:
- Assessment only (no Phase 3): **"Phase 4: Opus Synthesis Prompt — Assessment Only"**
- With comparison: **"Phase 4: Opus Synthesis Prompt — With Comparison"**

Copy verbatim. Fill in:
- `[N]` — number of domain research agents
- `[REPO NAME]`
- `[PROJECT NAME]` (comparison template only)
- `[PASTE ALL PHASE 2 REPORTS]` — read all `.../run-id/*-phase2-sonnet.md` files
- `[PASTE ALL PHASE 3 REPORTS]` (comparison template only) — read all `.../run-id/*-phase3-sonnet.md` files

Do NOT write custom synthesis prompts — the template's tier definitions and "do NOT classify as could defer" rule prevent Opus over-softening.

**Output:**
- Always: `<REPO>-ASSESSMENT.md` — evergreen document, version-pinned, describes the repo on its own terms
- If comparison ran: also `<REPO>-GAP-ANALYSIS.md` — point-in-time findings, tiered and effort-estimated

**Tiers (if comparison ran):**
- **Tier 0 (hours):** Actively wrong. Trivial fixes.
- **Tier 1 (days):** High-impact architecture additions.
- **Tier 2 (weeks):** Fidelity gaps for production quality.
- **Tier 3 (sprint):** Foundational infrastructure.

Every real finding gets a tier and effort estimate. Nothing goes into "future work" without a tier.

---

### Phase 5: Coordinator Discussion (EM + PM)

Present findings to the PM:
- **Assessment summary** — what did we learn about this repo?
- **Key architectural insights** — patterns worth adopting, approaches worth studying
- **If comparison ran:** prioritized gap findings with tiers and effort estimates
- **Recommended next steps** — what to implement, what to investigate further, what to defer

This is a conversation, not an automated step. The PM makes scope and prioritization decisions.

---

### Phase 5.5: Scratch Triage (Coordinator)

After synthesis and PM discussion:

1. **Default: DELETE all scratch files.** Phase 1 output was consumed by Phase 2. Phase 2 was consumed by Phase 4. Phase 3 was consumed by Phase 4. Durable artifacts are the assessment and gap analysis documents.

2. **Exception — keep Phase 2 if assessment-only and comparison deferred:** If Phase 3 was skipped and comparison will happen in a future session, move Phase 2 files to `.claude/scratch/deep-research/kept/` with a header noting a 30-day expiry. The next deep-research run for the same repo should check `kept/` and clean up expired files.

3. **Clean up:** `rm -rf .claude/scratch/deep-research/{run-id}/` (move kept files first if applicable).

---

## Pipeline B: Internet Research

### Phase sequence (STRICT)

```
Phase 0 → [wait] → Phase 1 → [wait for ALL] → Phase 2 → [wait for ALL] → Phase 3 → Phase 3.5
```

**Phases MUST run sequentially.** Each phase's output shapes the next phase's prompts.

---

### Phase 0: Research Framing (Coordinator, ~5 min)

1. **Define the research question** — what specifically do we need to know? what will we do with the answer?
2. **Identify search domains** — 3-6 topic areas (these become the chunks dispatched to Phase 1 agents)
3. **List known sources** — documentation, libraries, prior art already known
4. **Write focus questions** — what trade-offs matter? what constraints does our project have? what claims need verification?
5. **Generate run ID** — format: `YYYY-MM-DD-HHhMM`

**Output:** Research brief using the **Research Brief Template** from `agent-prompts.md`:

| Topic Area | Search Domains | Known Sources | Focus Question |
|------------|----------------|---------------|----------------|
| A | [what to search for] | [docs/repos known] | [what do we need to know?] |

---

### Phase 1: Broad Discovery (Haiku agents, parallel)

**Model:** Haiku. **Tools:** WebSearch, WebFetch, Context7. **Dispatch:** One agent per topic area, all simultaneously.

**DISPATCH:** Open `agent-prompts.md`. Find **"Phase 1: Haiku Broad Discovery Prompt"**. Copy verbatim. Fill in:
- `[TOPIC AREA LETTER]` — A, B, C, etc.
- `[TOPIC DESCRIPTION]` — from Phase 0 research brief
- `[ANY KNOWN URLS/DOCS]` — from Phase 0 known sources
- `[WHAT SPECIFICALLY DO WE NEED TO KNOW]` — the focus question for this topic
- `[SCRATCH_PATH]` — `.claude/scratch/deep-research/{run-id}/{topic-letter}-phase1-haiku.md`

Include `Write`, `WebSearch`, `WebFetch` in each agent's tool list. Dispatch with `run_in_background: true`. Do NOT write custom prompts — the template's "You are FILTERING, not analyzing" instruction prevents Haiku from producing unverified analysis.

**Haiku filters; Sonnet verifies.** Haiku agents catalog what's available, flag contradictions, and recommend sources for deeper reading. They do NOT verify or analyze claims.

**Scratch verification:** Before proceeding to Phase 2, verify all expected Phase 1 files exist. Re-dispatch once on failure; skip that topic on second failure.

---

### Phase 2: Analytical Deep-Read (Sonnet agents, parallel)

**Model:** Sonnet. **Tools:** WebFetch, Context7, Read. **Input:** Phase 1 discovery report per topic.

**DISPATCH:** Open `agent-prompts.md`. Find **"Phase 2: Sonnet Analytical Deep-Read Prompt"**. Copy verbatim. Fill in:
- `[TOPIC DESCRIPTION]`
- `[PASTE PHASE 1 OUTPUT HERE]` — read from `.claude/scratch/deep-research/{run-id}/{topic-letter}-phase1-haiku.md`
- `[BRIEF DESCRIPTION OF THE PROJECT AND ITS CONSTRAINTS]` — project context
- `[SCRATCH_PATH]` — `.claude/scratch/deep-research/{run-id}/{topic-letter}-phase2-sonnet.md`

Include `Write`, `WebFetch`, `Read` in each agent's tool list. Dispatch with `run_in_background: true`. Do NOT write custom prompts — the template's verification structure (verified/refuted/contradictions resolved) is the core value of Phase 2.

**Critical:** "Verify, don't trust." If Phase 1 flagged a claim, find the primary source. If sources disagree, present both sides with evidence — do not average contradictions into a vague "it depends."

**Scratch verification:** Before proceeding to Phase 3, verify all expected Phase 2 files exist. Re-dispatch once on failure; skip topic on second failure.

---

### Phase 3: Research Synthesis (Opus, single agent)

**Model:** Opus. **Input:** ALL Phase 2 reports.

**DISPATCH:** Open `agent-prompts.md`. Find **"Phase 3: Opus Research Synthesis Prompt"**. Copy verbatim. Fill in:
- `[N]` — number of topic research agents
- `[RESEARCH QUESTION]` — from Phase 0
- `[PASTE ALL PHASE 2 REPORTS]` — read all `.../run-id/*-phase2-sonnet.md` files
- `[BRIEF DESCRIPTION OF PROJECT, CONSTRAINTS, AND WHAT WE'LL DO WITH FINDINGS]`

Do NOT write custom synthesis prompts.

**Output:** `<TOPIC>-RESEARCH-SYNTHESIS.md` with:
- Executive summary (3-5 sentences)
- Findings by topic area with consensus, key finding, and recommendation per topic
- Prioritized recommendations (immediate / near-term / investigate further)
- Open questions
- Full source bibliography

---

### Phase 3.5: Scratch Triage (Coordinator)

After synthesis and PM discussion:

1. **Default: DELETE all scratch files.** Phase 1 output was consumed by Phase 2. Phase 2 was consumed by Phase 3. The durable artifact is the research synthesis document.

2. **Clean up:** `rm -rf .claude/scratch/deep-research/{run-id}/`

---

## Failure Modes

| Failure | Pipeline | Prevention |
|---------|----------|------------|
| Running phases in parallel | Both | Each phase shapes the next. Sequential = cheaper AND better. |
| Writing custom dispatch prompts | Both | Templates in `agent-prompts.md` are tested infrastructure. Copy verbatim, fill blanks. Custom prompts lose guardrails silently — Haiku confabulates, Sonnet scope-bleeds, Opus over-softens. |
| Agreeing to use templates then not using them | Both | The EM has been observed agreeing 5 times then writing custom prompts anyway. The DISPATCH blocks are not suggestions. |
| Scope too narrow | Both | Best findings are often in unexpected domains. Survey broadly. |
| Mixing assessment and comparison in Phase 2 | Repo | Phase 2 is standalone analysis. No references to your project. Comparison is Phase 3. |
| Skipping Phase 2 and going straight to comparison | Repo | Assessment is always the foundation. You cannot compare well without understanding first. |
| Not reading project files in Phase 3 | Repo | "Read project files. Find actual constants. State explicitly when absent." |
| Re-reading reference repo in Phase 3 | Repo | Use the Phase 2 analysis as input. Don't re-read reference source files. |
| Over-softening findings | Repo | Every real finding gets a tier + effort. Nothing deferred without a tier. Tier 2 (weeks) is NOT deferral. |
| Opus says "could defer" | Repo | Tier 2 (weeks) ≠ defer. Tiers are sequencing, not filtering. |
| Trusting Haiku's claims | Internet | Haiku filters — it does NOT verify. Sonnet verifies. |
| Averaging contradictions | Internet | "Sources A and B disagree" is better than a false synthesis. |
| Agent returns empty output | Both | Verify file exists AND has >0 bytes before proceeding. Re-dispatch once. |

---

## Cost Profile

| Run type | Phases | Agents | Wall-clock |
|----------|--------|--------|------------|
| Repo — assessment only (Phases 0-2-4-5) | 4 | ~4-8 Haiku + 4-6 Sonnet + 1 Opus | ~20 min |
| Repo — with comparison (Phases 0-3-4-5) | 5 | ~4-8 Haiku + 8-12 Sonnet + 1 Opus | ~30 min |
| Repo — re-run comparison only (Phases 3-4-5) | 3 | ~4-6 Sonnet + 1 Opus | ~15 min |
| Internet Research (Phases 0-3) | 4 | ~4-8 Haiku + 4-6 Sonnet + 1 Opus | ~20 min |

Phase 3 (comparison) is cheaper in practice: Sonnet agents have the Phase 2 analysis pre-digested and don't need to re-understand the reference repo from scratch.

---

## Relationship to Other Commands

| Command | When to use |
|---------|-------------|
| `/deep-research repo` | Study a codebase — understand its architecture, patterns, and design decisions |
| `/deep-research web` | Investigate a technical topic with multi-source verification |
| `/structured-research` | Batch research across N entities with a repeating schema — teams, companies, tools, etc. |

**Pipeline C (Structured Research) is not implemented here.** For research with batch subjects, acceptance criteria, quality gates, and schema-conforming output, use `/structured-research` instead.
