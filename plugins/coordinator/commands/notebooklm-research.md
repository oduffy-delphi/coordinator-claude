---
description: "Research topics using Google NotebookLM — for YouTube videos, podcasts, audio, and other media Claude cannot access directly. Creates a NotebookLM notebook, ingests source URLs, queries with structured questions, and synthesizes findings. Requires the notebooklm plugin to be enabled."
allowed-tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent", "ToolSearch", "AskUserQuestion"]
argument-hint: "<topic> [--sources url1 url2 ...] [--questions q1 q2 ...]"
---

# NotebookLM Research — Pipeline D

Research via Google NotebookLM for media-rich sources Claude cannot access directly: YouTube videos, podcasts, audio content, web pages with heavy JavaScript rendering, and Google Drive documents.

**When to use this:**
- PM provides YouTube links, podcast URLs, or audio content to research
- The source material requires transcription or media processing Claude can't do
- NotebookLM's AI analysis adds value (cross-source synthesis, citation tracking)

**When NOT to use this:**
- Codebase research → `/deep-research repo`
- Web topic research → `/deep-research web`
- Structured batch research → `/structured-research`
- Quick API docs → Context7

**Announce at start:** "I'm running `/notebooklm-research` to research {topic} using NotebookLM for media sources Claude can't access directly."

---

## Arguments

`$ARGUMENTS` provides the topic and optional sources/questions.

**Full form:** `/notebooklm-research <topic> --sources <url1> <url2> ... --questions <q1> <q2> ...`

**Topic only:** `/notebooklm-research <topic>` — will ask PM for sources, generate questions from topic.

**Interactive:** `/notebooklm-research` — will ask for topic, sources, and questions interactively.

---

## Execution Flow

### Step 1 — Enable Plugin

The notebooklm plugin is kept **disabled by default** to avoid cluttering the coordinator's context with 35 MCP tools. Enable it for this command's duration:

```bash
# Enable the plugin — adjust path if your Claude config directory differs
cd ~/.claude && python -c "
import json
with open('settings.json', 'r') as f: s = json.load(f)
# Find the notebooklm plugin key (may vary by marketplace name)
for key in s.get('enabledPlugins', {}):
    if 'notebooklm' in key:
        s['enabledPlugins'][key] = True
        break
with open('settings.json', 'w') as f: json.dump(s, f, indent=2)
print('notebooklm plugin enabled')
"
```

Then run `/reload-plugins` to load the MCP server.

Verify MCP tools are available:
```
ToolSearch("mcp__plugin_notebooklm_notebooklm__notebook_create")
```

If ToolSearch returns no results after reload, check that `notebooklm-mcp` is installed (`pip install notebooklm-mcp-cli`) and authenticated (`nlm login`).

**Do not proceed** until MCP tools are confirmed available.

### Step 2 — Gather Inputs

Parse `$ARGUMENTS` for topic, sources, and questions.

- **Topic** is required. If not provided, ask the PM via AskUserQuestion.
- **Sources** (`--sources`): If not provided, ask the PM: "What URLs should I feed to NotebookLM? (YouTube links, web pages, podcast URLs, etc.)"
- **Questions** (`--questions`): If not provided, generate 5-8 research questions from the topic using your Opus judgment. Present them to the PM for approval/modification before proceeding.

### Step 3 — Create Scratch Directory

```bash
mkdir -p ~/.claude/scratch/notebooklm-research/{run-id}/
```

Use a short run ID: `{topic-slug}-{YYYYMMDD}` (e.g., `transformer-arch-20260320`).

### Step 4 — Dispatch Worker

Dispatch the `notebooklm-research-worker` agent (Sonnet) with:

- **Notebook name:** `{topic} — {YYYY-MM-DD}`
- **Source URLs:** the collected URLs
- **Research questions:** the approved questions
- **Output path:** `~/.claude/scratch/notebooklm-research/{run-id}/findings.md`
- **Artifact requests:** if the PM requested reports, mind maps, slides, or podcasts

### Step 5 — Read and Evaluate Worker Output

Read `{scratch-dir}/findings.md`. Evaluate:

- Did all sources process successfully?
- Were all questions answered?
- Are the responses substantive or shallow?
- Any failures that need PM attention?

### Step 6 — Synthesize

Using your Opus judgment, synthesize the worker's raw findings into a polished research document:

- Cross-reference findings across sources
- Assess source quality and reliability
- Identify gaps or contradictions
- Structure takeaways for the PM
- Preserve important citations

### Step 7 — Write Final Artifact

Write the synthesized research document to:

```
~/.claude/docs/research/YYYY-MM-DD-{topic-slug}.md
```

Format: Standard research artifact with metadata header, executive summary, detailed findings, and source list.

### Step 8 — Cleanup Decision

Ask the PM: "Want me to keep the NotebookLM notebook for follow-up queries, or delete it?"

- If keep: note the notebook ID in the research doc metadata
- If delete: dispatch the worker to call `notebook_delete`

Clean up scratch files regardless.

### Step 9 — Disable Plugin

Restore the plugin to disabled state to remove MCP tools from future sessions:

```bash
cd ~/.claude && python -c "
import json
with open('settings.json', 'r') as f: s = json.load(f)
for key in s.get('enabledPlugins', {}):
    if 'notebooklm' in key:
        s['enabledPlugins'][key] = False
        break
with open('settings.json', 'w') as f: json.dump(s, f, indent=2)
print('notebooklm plugin disabled')
"
```

No need to `/reload-plugins` — the tools will simply not load in the next session.

### Step 10 — Report

Summarize to the PM:
- What was researched
- How many sources were processed
- Key findings (2-3 bullet executive summary)
- Where the full research doc was saved
- Any limitations or gaps worth noting
