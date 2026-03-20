---
description: "Research topics using Google NotebookLM — for YouTube videos, podcasts, audio, and other media Claude cannot access directly. Three-phase relay: (1) Opus orchestrator designs research plan, (2) command dispatches Sonnet worker for MCP execution, (3) Opus orchestrator synthesizes findings into polished research doc. Supports targeted mode (specific URLs) and exploratory mode (let NotebookLM find content)."
allowed-tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent", "ToolSearch", "AskUserQuestion"]
argument-hint: "<topic> [--sources url1 url2 ...] [--questions q1 q2 ...]"
---

# NotebookLM Research — Pipeline D

Research via Google NotebookLM for media-rich sources Claude cannot access directly: YouTube videos, podcasts, audio content, web pages with heavy JavaScript rendering, and Google Drive documents.

**Two modes:**
- **Targeted:** PM provides specific URLs (YouTube links, podcast URLs, articles) → orchestrator crafts questions tailored to those sources
- **Exploratory:** PM provides a topic (and optionally example videos for "more like this") → orchestrator leverages NotebookLM's research feature to discover the best content, powered by Google's search

**When to use this:**
- PM provides YouTube links, podcast URLs, or audio content to research
- PM wants to find the best talks/videos/podcasts on a topic (Google is better at this than our WebSearch)
- The source material requires transcription or media processing Claude can't do
- NotebookLM's AI analysis adds value (cross-source synthesis, citation tracking)

**When NOT to use this:**
- Codebase research → `/deep-research repo`
- Web topic research (text articles, docs) → `/deep-research web`
- Structured batch research → `/structured-research`
- Quick API docs → Context7

**Announce at start:** "I'm running `/notebooklm-research` to research {topic} using NotebookLM."

---

## Arguments

`$ARGUMENTS` provides the topic and optional sources/questions.

**Targeted:** `/notebooklm-research <topic> --sources <url1> <url2> ...`

**Exploratory:** `/notebooklm-research <topic>` (no sources — let NotebookLM find content)

**With questions:** `/notebooklm-research <topic> --sources <url1> ... --questions <q1> <q2> ...`

**Interactive:** `/notebooklm-research` (asks for everything)

---

## Execution Flow

### Step 1 — Verify MCP Tools Available

The notebooklm plugin must be enabled for the MCP server to be running.

```
ToolSearch("mcp__plugin_notebooklm_notebooklm__notebook_create")
```

If no results: the plugin is disabled. Alert the PM:

> The notebooklm plugin is not enabled. Enable it in `settings.json` (`"notebooklm@coordinator-claude": true`) and run `/reload-plugins`.

**Do not proceed** until MCP tools are confirmed available.

### Step 2 — Gather Inputs

Parse `$ARGUMENTS` for topic, sources, and questions.

- **Topic** is required. If not provided, ask the PM via AskUserQuestion.
- **Sources** (`--sources`): Optional. If provided, this is targeted mode. If absent, this is exploratory mode — tell the PM: "No specific sources provided — I'll have NotebookLM find the best content for this topic. Want to provide example URLs for 'more like this', or should I go fully exploratory?"
- **Questions** (`--questions`): Optional. If absent, the orchestrator will design them (that's its strength).

### Step 3 — Create Scratch Directory

```bash
mkdir -p ~/.claude/scratch/notebooklm-research/{run-id}/
```

Use a short run ID: `{topic-slug}-{YYYYMMDD}` (e.g., `transformer-arch-20260320`).

### Step 4 — Dispatch Orchestrator (Phase A — Plan)

Dispatch the `notebooklm-research-orchestrator` agent (Opus) to design the research plan:

```
Phase: A

Topic: {topic}

Mode: {targeted / exploratory / hybrid}

{If targeted:}
Source URLs:
1. {url1}
2. {url2}
...

{If exploratory:}
No specific sources — use NotebookLM's research feature to find the best content.
{Optional: "Example sources for 'more like this': {urls}"}

{If questions provided:}
PM-specified questions:
1. {q1}
2. {q2}
...
{Otherwise:}
Design 5-8 research questions using your Opus judgment.

Scratch directory: {scratch-dir}
Output path: ~/.claude/docs/research/YYYY-MM-DD-{topic-slug}.md

{If artifacts requested:}
Artifact requests: {reports / mind maps / slides / audio summary}
```

The orchestrator writes a research plan to `{scratch-dir}/research-plan.md` and returns.

### Step 5 — Read Plan and Dispatch Worker

Read `{scratch-dir}/research-plan.md`. Verify it contains questions and source/research instructions.

Dispatch the `notebooklm-research-worker` agent (Sonnet) with the plan contents:

```
Research topic: {topic from plan}

Notebook name: {notebook name from plan}

{Copy source URLs, research query, custom instructions, and questions from the plan verbatim}

Output path: {scratch-dir}/findings.md

{If artifact requests in plan:}
Artifact requests: {from plan}
```

The worker writes raw findings to `{scratch-dir}/findings.md` and returns.

### Step 6 — Dispatch Orchestrator (Phase B — Synthesize)

Read `{scratch-dir}/findings.md`. Verify it has substantive content (not empty or error-only).

Dispatch the `notebooklm-research-orchestrator` agent (Opus) for synthesis:

```
Phase: B

Topic: {topic}
Findings path: {scratch-dir}/findings.md
Output path: ~/.claude/docs/research/YYYY-MM-DD-{topic-slug}.md
Notebook ID: {from findings metadata}
```

The orchestrator reads the raw findings, synthesizes them, and writes the final research document.

### Step 7 — Evaluate and Cleanup

Read the final research document. Verify:
- Is it substantive? (Not just reformatted NotebookLM responses)
- Does it include source assessment and gap analysis?
- Are citations preserved?

Ask the PM: "Want me to keep the NotebookLM notebook for follow-up queries, or delete it?"

- If keep: note the notebook ID in the research doc metadata
- If delete: dispatch the worker to call `notebook_delete` with the notebook ID from the research doc metadata

Clean up scratch directory.

### Step 8 — Report

Summarize to the PM:
- What was researched (topic + mode)
- How many sources were processed
- Key findings (2-3 bullet executive summary)
- Where the full research doc was saved
- Any gaps the orchestrator flagged for follow-up
