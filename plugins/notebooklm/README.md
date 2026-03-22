# notebooklm

Google NotebookLM integration plugin. Enables research on YouTube videos, podcasts, audio content, and other media Claude cannot access directly. **Disabled by default** — managed automatically by the `/notebooklm-research` command.

## Components

**Agents:**
- `notebooklm-research-orchestrator` (Opus) — Research strategist. Designs the research plan, crafts targeted questions using baked-in anti-hallucination techniques, and dispatches the Sonnet worker for MCP execution. Synthesizes raw findings into a polished research document.
- `notebooklm-research-worker` (Sonnet) — Mechanical execution via MCP. Creates notebooks, ingests sources, runs queries, generates artifacts, and writes structured findings to disk. Dispatched by the orchestrator — not invoked directly.

**Commands:**
- `/notebooklm-research` — Research a topic using NotebookLM. Supports targeted mode (PM provides specific URLs) and exploratory mode (let NotebookLM discover the best content via Google's search).

**MCP Server:** `notebooklm-mcp` via [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) (MIT license). Exposes ~35 tools for notebook management, source ingestion, querying, and artifact generation.

## Prerequisites

1. Install the MCP CLI: `pip install notebooklm-mcp-cli`
2. Authenticate: `nlm login` (opens browser for Google account auth)

## How It Works

The plugin lifecycle is managed by the `/notebooklm-research` command:

1. Command verifies the notebooklm plugin is enabled (MCP tools available)
2. Dispatches the Opus orchestrator with topic, sources (if any), and mode
3. Orchestrator designs research questions using query engineering best practices
4. Orchestrator dispatches the Sonnet worker to handle MCP choreography
5. Worker creates notebook, ingests sources or runs exploratory research, queries with each question
6. Orchestrator reads raw findings and synthesizes a polished research document with citations, gaps, and source assessment; optionally writes a **Synthesizer Advisory** (`{output-path}-advisory.md`) with staff-engineer observations beyond the research scope — skipped if there's nothing beyond scope
7. Command asks whether to retain or delete the NotebookLM notebook

This two-tier design (Opus orchestrator + Sonnet worker) keeps expensive judgment work separate from mechanical MCP operations. The orchestrator's baked-in query engineering — citation requirements, specificity rules, structured synthesis templates — addresses NotebookLM's documented hallucination rate on broad queries.

## Research Modes

**Targeted:** PM provides specific YouTube links, podcast URLs, or web articles. The orchestrator crafts questions tailored to the known sources.

```
/notebooklm-research transformer architectures --sources https://youtube.com/... https://youtube.com/...
```

**Exploratory:** PM provides a topic (no specific sources). The orchestrator uses NotebookLM's research feature to discover the best content via Google's search, then queries it.

```
/notebooklm-research "AI agent architectures — what are experts saying"
```

**Hybrid:** PM provides some seed URLs plus a topic — orchestrator starts with known sources, identifies gaps, then expands via discovery.

## Platform Notes

- **macOS/Linux:** The `.mcp.json` command (`notebooklm-mcp`) works directly.
- **Windows:** Change the command to `cmd` with args `["/c", "notebooklm-mcp"]` in `.mcp.json`.

See `CLAUDE.md` for detailed operating notes, rate limits, and caveats.
