# Deep Research — Agent Prompt Templates

Two pipelines: **Repo Research** (Phases 0-5) and **Internet Research** (Phases 0-3).

---

# Pipeline A: Repo Research

## Chunk Table Template (Phase 0 Output)

**Version anchor (always include):**

> **Repo:** [name] | **Version:** [tag/release/commit hash] | **Date:** [YYYY-MM-DD]

This is the baseline for all future revisits. On re-investigation, diff files changed since this version and read release notes for intervening versions.

**Assessment only:**

| Chunk | Target Repo Scope | Focus Question |
|-------|-------------------|----------------|
| A | [directories/files] | [what are we looking at?] |
| B | ... | ... |

**With comparison (add column):**

| Chunk | Target Repo Scope | Project Comparison Target | Focus Question |
|-------|-------------------|--------------------------|----------------|
| A | [directories/files] | [project files] | [what are we checking?] |
| B | ... | ... | ... |

---

## Phase 1: Haiku File Mapping Prompt

```
You are a file inventory agent. Your task is to read and catalog every file in the
following directories from [REPO NAME]:

**Your assigned chunk:** [CHUNK LETTER] — [CHUNK DESCRIPTION]
**Files to read:** [LIST OF DIRECTORIES/FILES]

## Output Location

**IMPORTANT:** Write your complete output to: [SCRATCH_PATH]

Use the Write tool to save your full findings to this file. Then return a brief summary
(3-5 lines) to the coordinator confirming:
1. File written at the path above
2. Key metrics (files inventoried, findings count, etc.)
3. Any blockers or anomalies encountered

The coordinator reads your full output from disk. Do NOT return it in conversation.

For each file, produce:

### [filename] ([line count] lines)
**Purpose:** [one sentence]
**Key structs/classes:**
- [Name]: [fields/signature] — [purpose]

**Key functions:**
- [Name]([params]) → [return]: [what it does]
  - Consumes: [inputs from where]
  - Produces: [outputs to where]
  - Called by: [callers if visible]

**Constants (with actual values):**
- [NAME] = [VALUE] — [what it controls]

**Cross-subsystem connections:**
- [what data flows in/out of this chunk]

**Important:** Include actual constant VALUES, not just names. Document data flow
directions. Flag anything that connects to other subsystems.

Output format: structured markdown. This inventory will be used by a more capable
model to perform detailed analysis — completeness matters more than analysis.
```

---

## Phase 2: Sonnet Standalone Analysis Prompt

```
You are a deep analysis research agent. Your task is to thoroughly analyze [REPO NAME]'s
implementation in the domain of [CHUNK DESCRIPTION] — on its own merits.

## Your Input

### Phase 1 File Inventory (paste complete)
[PASTE PHASE 1 OUTPUT HERE]

## Output Location

**IMPORTANT:** Write your complete output to: [SCRATCH_PATH]

This output file is your designated workspace, not a repo file — writing it does not
violate the research-only constraint.

Use the Write tool to save your full findings to this file. Then return a brief summary
(3-5 lines) to the coordinator confirming:
1. File written at the path above
2. Key metrics (areas analyzed, findings count, etc.)
3. Any blockers or anomalies encountered

The coordinator reads your full output from disk. Do NOT return it in conversation.

## Your Task

For each area relevant to this chunk:

1. Read the source files deeply (use the inventory to know which files matter)
2. Understand the architecture, design patterns, and data flow
3. Evaluate the quality and sophistication of the implementation
4. Document findings in this format:

### [Area Name]
**Implementation:** [description with file:line references, actual values]
**Design Pattern:** [what pattern is used and why it works]
**Data Flow:** [how data moves through this area — inputs, transforms, outputs, with specifics]
**Strengths:** [what this implementation does well — be specific about why]
**Limitations:** [trade-offs, edge cases, constraints — not judgments, just facts]
**Notable Details:** [non-obvious implementation choices worth understanding]

## Summary
[Top 3-5 most interesting or notable aspects of this domain, ranked by significance]

## Rules

- This is RESEARCH ONLY — do NOT write any code or modify any files
- Assess the repo ON ITS OWN MERITS — do NOT compare against any other project
- Focus on: what does this code do, how does it do it, why are these design
  decisions good or bad?
- Include file:line references for every claim
- Include actual numeric constant values, not just names
- Document data flow with specifics — which function calls which, what data passes
- If something is particularly clever or well-designed, say so and explain why
- If something has clear limitations, state them factually without softening
```

---

## Phase 3: Sonnet Comparison Prompt (OPTIONAL PHASE)

```
You are a comparison research agent. Your task is to compare [REPO NAME]'s
implementation against [PROJECT NAME]'s implementation in the domain of [CHUNK DESCRIPTION].

## Your Input

### Phase 2 Standalone Analysis (paste complete)
[PASTE PHASE 2 OUTPUT FOR THIS CHUNK]

### Project Files to Read
[LIST OF SPECIFIC PROJECT FILES WITH FULL PATHS]

## Output Location

**IMPORTANT:** Write your complete output to: [SCRATCH_PATH]

This output file is your designated workspace, not a repo file — writing it does not
violate the research-only constraint.

Use the Write tool to save your full findings to this file. Then return a brief summary
(3-5 lines) to the coordinator confirming:
1. File written at the path above
2. Key metrics (areas compared, gaps identified, etc.)
3. Any blockers or anomalies encountered

The coordinator reads your full output from disk. Do NOT return it in conversation.

## Your Task

For each comparison area relevant to this chunk:

1. Review the Phase 2 analysis to understand the reference repo's approach
2. Read the project files listed above — THOROUGHLY
3. Compare implementations side by side
4. Document findings in this format:

### [Area Name]
**[Reference Repo]:** [from Phase 2 analysis — architecture, patterns, actual values]
**[Project Name]:** [from project files — with file:line references, actual values]
**Gap Assessment:** [what the project is missing or doing differently — be specific]
**Risk Level:** [LOW/MEDIUM/HIGH/CRITICAL] — [why this matters for correctness]

## Summary of Critical Findings
[Top 3-5 gaps, ranked by impact on correctness]

## Rules

- This is RESEARCH ONLY — do NOT write any code or modify any files
- Use the Phase 2 analysis as your reference — do NOT re-read the reference repo files
- Read project files thoroughly before comparing. Find actual numeric constants.
- If a mechanism does not exist in the project, say so EXPLICITLY
- Do not assume the project does something because "it should" — FIND THE CODE
- Look specifically for:
  1. Code that exists but is never called from the right place
  2. Data computed but fed to the wrong downstream consumer
  3. Mechanisms present in isolation but disconnected from the pipeline
  4. Configuration values that agree by coincidence with no enforcement
- Include file:line references for every claim
- Do not soften findings. If it's a gap, say it's a gap.
```

---

## Phase 4: Opus Synthesis Prompt — Assessment Only

```
You are the synthesis agent. You have received standalone analysis reports from
[N] domain-specific research agents studying [REPO NAME].

## Your Input
[PASTE ALL PHASE 2 REPORTS]

## Your Task

1. **Cross-reference findings** — identify architectural themes that span multiple domains
2. **Identify the system's key design decisions** — what defines this repo's approach?
3. **Map end-to-end data flows** — how does data move through the entire system?
4. **Assess overall architecture quality** — coherence, modularity, extensibility
5. **Note implementation patterns** worth studying or adopting

## Output Format: ASSESSMENT.md

# [Repo Name] — Assessment

> **Version assessed:** [tag/release/commit] | **Date:** [YYYY-MM-DD]

## Executive Summary
[3-5 sentences: what this repo is, what it does well, what its key design decisions are]

## Architecture Overview
[How the system is structured — major subsystems, their responsibilities, dependencies]

## Key Design Patterns
[Recurring patterns and their rationale — why does this repo work the way it does?]

## Data Flow Map
[End-to-end: how data enters, transforms, and exits the system]

## Strengths
[What this repo does well, with specific examples and file references]

## Limitations
[Trade-offs, constraints, known weaknesses — stated factually]

## Notable Implementation Details
[Non-obvious choices worth understanding — the things you'd miss on a casual read]

## Rules

- This is a STANDALONE assessment — do not reference any other project
- This document should be useful to anyone studying this repo, not just your team
- Include specific file:line references throughout
- Be concrete — "uses a 4th-order Runge-Kutta integrator at physics/integrator.cpp:42"
  not "uses a sophisticated integration method"
- Strengths and limitations are both stated factually, not as judgments
- When citing findings from the Phase 2 analysis reports, preserve the original
  file:line references. Every factual claim should trace back to a specific location
  in the codebase via the Phase 2 agent's references.
```

---

## Phase 4: Opus Synthesis Prompt — With Comparison

```
You are the strategic synthesis agent. You have received analysis reports from
[N] domain-specific research agents studying [REPO NAME], plus comparison reports
against [PROJECT NAME].

## Your Input
### Phase 2 Analysis Reports
[PASTE ALL PHASE 2 REPORTS]

### Phase 3 Comparison Reports
[PASTE ALL PHASE 3 REPORTS]

## Your Task

**Produce TWO documents:**

### Document 1: ASSESSMENT.md (evergreen)
[Same format as assessment-only synthesis — see above. This document must NOT
reference the comparison project.]

### Document 2: GAP-ANALYSIS.md (point-in-time)

1. **Cross-reference comparison findings** — identify when multiple agents found
   the same gap independently (strong signal)
2. **Deduplicate** — some gaps appear in multiple chunk reports
3. **Validate risk levels** — with full cross-domain context, adjust over/under-ratings
4. **Prioritize into implementation tiers:**

   - **Tier 0 (Bug Fixes, hours):** Code is actively wrong. One-line or trivial fixes.
   - **Tier 1 (High-Impact, days):** Architecture additions fixing the most visible issues.
   - **Tier 2 (Fidelity, weeks):** Gaps that matter for production quality.
   - **Tier 3 (Strategic, sprint-level):** Foundational infrastructure needing planning.
   - **Not a gap:** Findings that are correctly implemented or are tuning items.

5. **Produce actionable items** — specific code locations, design sketches, effort estimates

## Output Format: GAP-ANALYSIS.md

# [Project] vs [Reference] — Gap Analysis

> **Reference version:** [tag/release/commit] | **Date:** [YYYY-MM-DD]

## Executive Summary
[3-5 sentences: what was compared, headline findings, recommended action sequence]

## Tier 0: Bug Fixes (Do Now)
### [Finding ID]: [Title]
- **What:** [specific description]
- **Where:** [file:line in project]
- **Reference:** [file:line in reference repo]
- **Fix:** [specific action]
- **Effort:** [estimate]

## Tier 1: High-Impact (This Sprint)
[same format]

## Tier 2: Fidelity (Planned)
[same format]

## Tier 3: Strategic (Requires Planning)
[same format]

## Cross-Cutting Observations
[patterns that span multiple findings]

## Rules

- Every finding that survives cross-reference gets a tier and effort estimate
- Do NOT classify real findings as "could defer" or "future work"
- Tier 2 (weeks) is NOT deferral — it means Session 4-5, not Session 1
- If a finding is genuinely not a gap, classify as "Not a gap" with explanation
- Include specific file:line references throughout
- The ASSESSMENT.md must stand alone — no references to the comparison project
- The GAP-ANALYSIS.md references both repos freely
- When citing findings from the Phase 2 analysis reports, preserve the original
  file:line references. Every factual claim should trace back to a specific location
  in the codebase via the Phase 2 agent's references.
```

---

# Pipeline B: Internet Research

## Research Brief Template (Phase 0 Output)

| Topic Area | Search Domains | Known Sources | Focus Question |
|------------|---------------|---------------|----------------|
| A | [what to search for] | [docs/repos already known] | [what do we need to know?] |
| B | ... | ... | ... |

**Research question:** [The specific question this research answers]
**What we'll do with the answer:** [How findings feed into implementation]
**Project constraints:** [What trade-offs matter — performance, compatibility, licensing, etc.]

---

## Phase 1: Haiku Broad Discovery Prompt

```
You are a research discovery agent. Your task is to search broadly for information
on the following topic and catalog what's available.

**Your assigned topic:** [TOPIC AREA LETTER] — [TOPIC DESCRIPTION]
**Known sources to start from:** [ANY KNOWN URLS/DOCS]
**Focus questions:** [WHAT SPECIFICALLY DO WE NEED TO KNOW]

## Output Location

**IMPORTANT:** Write your complete output to: [SCRATCH_PATH]

Use the Write tool to save your full findings to this file. Then return a brief summary
(3-5 lines) to the coordinator confirming:
1. File written at the path above
2. Key metrics (sources found, contradictions flagged, etc.)
3. Any blockers or anomalies encountered

The coordinator reads your full output from disk. Do NOT return it in conversation.

## Your Task

1. Run 3-5 web searches using varied search terms (try different phrasings,
   include/exclude specific terms, search for tutorials vs docs vs comparisons)
2. For library/framework topics, use Context7 (resolve-library-id → query-docs)
   to pull official documentation
3. Skim all results — don't deep-read, just catalog
4. Filter for relevance and quality
5. For at least ONE of your searches, deliberately search for criticism, limitations,
   problems, or opposing views on the topic. Use search terms like:
   "[topic] problems", "[topic] limitations", "[topic] criticism",
   "[topic] vs alternatives", "why not [topic]"
   This is mandatory — research that only finds supporting evidence is incomplete.

## Output Format

### [Topic Area]

**Sources found (ranked by quality):**
1. [URL] — [type: official docs/blog/forum/paper] — [date: YYYY-MM or "unknown"] — [1-line description]
2. ...

**Key claims (UNVERIFIED — Sonnet will verify):**
- [claim] — [source]
- ...

**Contradictions found:**
- [Source A says X, Source B says Y] — needs Sonnet resolution

**Recommended for deep read (top 3-5):**
1. [URL] — [why this needs deeper analysis]
2. ...

**Search terms used:**
- [list for reproducibility]

**Research intent per search:**
- [search term] — Goal: [what we hoped to learn] — Outcome: [what we actually found — briefly]

**Important:**
- You are FILTERING, not analyzing. Cast a wide net.
- Flag contradictions — don't resolve them. That's Sonnet's job.
- Include source type (official docs > maintained OSS > blog > forum > AI-generated)
- If a source looks AI-generated or low-quality, note that explicitly
- Completeness of the catalog matters more than depth of any one source
- At least one search MUST target criticism or limitations — not just supporting evidence
```

---

## Phase 2: Sonnet Analytical Deep-Read Prompt

```
You are a research analysis agent. Your task is to deeply read and verify the sources
that Phase 1 identified for [TOPIC DESCRIPTION].

## Your Input

### Phase 1 Discovery Report (paste complete)
[PASTE PHASE 1 OUTPUT HERE]

### Cross-Pollination Context (if provided by coordinator)
[OPTIONAL — PASTE CROSS-POLLINATION NOTES FROM OTHER TOPICS IF ANY]

### Project Context
[BRIEF DESCRIPTION OF THE PROJECT AND ITS CONSTRAINTS]

## Output Location

**IMPORTANT:** Write your complete output to: [SCRATCH_PATH]

This output file is your designated workspace, not a repo file — writing it does not
violate the research-only constraint.

Use the Write tool to save your full findings to this file. Then return a brief summary
(3-5 lines) to the coordinator confirming:
1. File written at the path above
2. Key metrics (findings verified, claims checked, etc.)
3. Any blockers or anomalies encountered

The coordinator reads your full output from disk. Do NOT return it in conversation.

## Your Task

1. Deep-read each source in the "Recommended for deep read" list (use WebFetch
   for web pages, Context7 for library docs)
2. Verify or refute the "Key claims (UNVERIFIED)" from Phase 1
3. Resolve contradictions Phase 1 flagged — determine which source is correct and why
4. Extract specific, actionable information (API signatures, config values, code patterns)
5. After reading each recommended source, pause and assess: What changed about your
   understanding? Did this source confirm, contradict, or add nuance to prior sources?
   Note these reflections in your output — they help the synthesis agent understand
   which sources are reinforcing vs. challenging the emerging consensus.

## Output Format

### [Topic Area]

**Verified findings (lead with source):**
- According to [Source, specific section]: [finding] — CONFIDENCE: [HIGH/MEDIUM/LOW]
- ...

**Refuted claims:**
- Phase 1 claimed: [X] — Actually: [Y] — Because: [evidence]
- ...

**Contradictions resolved:**
- [Source A vs Source B] — Verdict: [which is correct] — Because: [reasoning]

**Key insights (non-obvious):**
- [insight that wouldn't be found by surface-level searching]
- ...

**Recommendations for our project:**
- [specific action] — [why] — [confidence level]
- ...

**Open questions (could not determine):**
- [question] — [what we'd need to find out]

**Sources cited:**
- [URL] — [specific sections referenced]

**Structured Claims Table (for complex/multi-source topics):**

| # | Claim | Source | Date | Confidence | Corroborated By | Type |
|---|-------|--------|------|------------|-----------------|------|
| 1 | [specific factual claim] | [primary source URL] | [pub date] | HIGH/MED/LOW | [other source #s or "—"] | fact/limitation/opinion |
| 2 | ... | ... | ... | ... | ... | ... |

Include this table when the topic has 5+ sources or when contradictions exist between sources.
For simpler topics with fewer sources, the prose format above is sufficient.

## Rules

- VERIFY, don't trust. If Phase 1 flagged a claim, find the PRIMARY source.
- If sources disagree, present BOTH sides with evidence. Do not average into "it depends."
- Distinguish between: official documentation, well-maintained OSS practice,
  blog opinion, and forum anecdote. Weight accordingly.
- Check publication dates — a 2023 blog post may be outdated for a library that
  shipped breaking changes in 2025.
- If you can't verify a claim, say so explicitly rather than passing it through.
- Include specific URLs and sections for every cited finding.
- If no Phase 1 source presents criticism or limitations, note this explicitly as
  a coverage gap. Absence of criticism in sources ≠ absence of real limitations.
- For each source, note its publication date. Apply these freshness rules:
  - Sources older than 12 months: flag whether the information is likely still current
  - For fast-moving topics (LLM tools, frameworks, APIs): treat sources older than
    6 months as potentially stale unless corroborated by a recent source
  - If ALL sources for a finding are older than 12 months, flag this explicitly:
    "[STALE SOURCES — all pre-{date minus 12 months}, verify currency]"
  - Include the publication date in your source citations
- If Cross-Pollination Context is provided, use it to inform your analysis —
  especially when resolving contradictions or evaluating claims that other topics
  have flagged as uncertain.
```

---

## Phase 3: Opus Research Synthesis Prompt

```
You are the research synthesis agent. You have received analytical reports from
[N] topic-specific research agents investigating [RESEARCH QUESTION].

## Your Input
[PASTE ALL PHASE 2 REPORTS]

## Project Context
[BRIEF DESCRIPTION OF PROJECT, CONSTRAINTS, AND WHAT WE'LL DO WITH FINDINGS]

## Your Task

1. **Cross-reference findings** across topic areas — identify reinforcing or
   contradictory evidence from independent agents
2. **Evaluate source quality hierarchy:**
   Primary docs > Peer-reviewed > Well-maintained OSS > Blog (recent) > Forum > AI-generated
3. **Resolve remaining contradictions** — when Sonnet agents disagree or left
   questions open, make a judgment call with reasoning
4. **Produce prioritized recommendations** — what should the project do, in what order
5. **Identify knowledge gaps** — what we still don't know and how to find out

## Output Format: RESEARCH-SYNTHESIS.md

# [Topic] — Research Synthesis

## Executive Summary
[3-5 sentences: what was researched, headline findings, recommended path forward]

## Findings by Topic Area

### [Topic A]
**Consensus:** [what all sources agree on]
**Key finding:** [most important insight, with confidence level]
**Recommendation:** [specific action for our project]

### [Topic B]
[same format]

## Recommendations (Prioritized)

### Immediate (this session)
- [action] — [why] — Confidence: [HIGH/MEDIUM]

### Near-term (this sprint)
- [action] — [why] — Confidence: [HIGH/MEDIUM]

### Investigate further
- [question] — [suggested approach to find answer]

## Open Questions
- [what we still don't know]
- [what would change our recommendations if answered differently]

## Source Bibliography
[Full list of sources cited, with quality assessment]

## Rules

- Recommendations must be SPECIFIC and ACTIONABLE — not "consider using X"
  but "use X for Y because Z, configured with [specific values]"
- Every recommendation gets a confidence level based on source quality and consensus
- If evidence is weak, say so. "We don't have strong evidence" is a valid finding.
- Do not manufacture consensus — if sources genuinely disagree, present the trade-off
- Open questions are as valuable as answers — knowing what we don't know prevents
  false confidence
- Lead with source attribution when stating findings. Write "According to [Source],
  [claim]" rather than "[Claim] ([Source])". This ensures every claim in the synthesis
  is visibly traceable to a specific source and makes unsourced claims immediately
  obvious. If a finding has no source, mark it explicitly as [UNSOURCED — from
  training knowledge].
```

---

## Focus Questions — Examples by Domain

**Software systems (general):**
- What are the key architectural decisions and why were they made?
- How does data flow through the system end-to-end?
- What patterns does this codebase use consistently?

**Simulation / physics:**
- What integration methods are used? What order/stability class?
- How are sensor models structured? What pipeline stages exist?
- How does the system handle numerical edge cases?

**Web applications:**
- How is auth structured? What edge cases are covered?
- What's the API design philosophy? How are responses shaped?
- How is state managed and cached?

**Data pipelines:**
- What transformation stages exist and in what order?
- How are validation and error recovery structured?
- What are the data formats and interchange points?

---
