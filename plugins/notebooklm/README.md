# notebooklm

Google NotebookLM integration plugin (Pipeline D). Enables research on YouTube videos, podcasts, audio content, and other media Claude cannot access directly via a two-phase Agent Teams architecture.

## Components

**Agents:**
- `notebooklm-research-strategist` (Opus) — Pre-team planning agent. Reads EM context, designs the optimal research strategy including notebook topology, worker count (1-3), question design using anti-hallucination techniques, and source strategy. Quota-aware — factors NLM tier limits (50/500/5000 queries/day) into sizing decisions. Writes `strategy.md` to disk.
- `notebooklm-research-scout` (Haiku) — Source discovery. Reads the strategist's plan, finds the best YouTube videos, podcasts, and articles for each notebook's topic area via web search. Writes `sources.md`.
- `notebooklm-research-worker` (Sonnet) — Mechanical MCP execution. Each worker owns one notebook — creates it, ingests assigned sources, runs queries, writes findings. Sends DONE to synthesizer when complete.
- `notebooklm-research-synthesizer` (Opus) — Cross-notebook synthesis. Reads all worker findings, cross-references across notebooks, writes the final polished research document. Optionally writes a **Synthesizer Advisory** with staff-engineer observations beyond scope. Cleans up all notebooks after synthesis.

**Commands:**
- `/notebooklm-research` — Research a topic using NotebookLM. Supports targeted mode (PM provides specific URLs) and exploratory mode (let NotebookLM discover the best content via Google's search).

**MCP Server:** `notebooklm-mcp` via [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) (MIT license). Exposes ~35 tools for notebook management, source ingestion, querying, and artifact generation.

## Prerequisites

1. Install the MCP CLI: `pip install notebooklm-mcp-cli`
2. Authenticate: `nlm login` (opens browser for Google account auth)
3. Agent Teams enabled: `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` in `settings.json` env

## How It Works

The plugin uses a **two-phase Agent Teams architecture** — the EM re-engages briefly between phases (~30 seconds), then is freed:

**Phase 1 — Strategist (regular Agent dispatch):**
1. EM writes context (topic, mode, tier, any PM-provided sources)
2. Opus strategist designs the research strategy: notebook topology, worker count, questions, source strategy
3. Strategist writes `strategy.md` to disk and returns
4. EM reads `worker_count` from strategy.md (mechanical — just extract the number)

**Phase 2 — Right-sized Agent Team:**
5. EM creates team: 1 Haiku scout + N Sonnet workers (1-3) + 1 Opus synthesizer
6. Scout finds sources via web search, writes `sources.md` → task completion unblocks workers
7. Workers create separate notebooks, ingest sources, run queries, write findings → send DONE to synthesizer
8. Synthesizer reads all findings, cross-references, writes final document; optionally writes a **Synthesizer Advisory** (`{output-path}-advisory.md`) with observations beyond scope; deletes all notebooks
9. EM receives notification → cleanup (archive, commit, present results)

**Why two phases:** The strategist decides worker count based on NLM domain knowledge (topic breadth, query budget, source availability). A focused question on free tier gets 1 worker with 5 queries; a broad investigation on Plus gets 3 workers with 8 queries each. The EM doesn't need NLM expertise — the strategist encodes it all.

## Research Modes

**Targeted:** PM provides specific YouTube links, podcast URLs, or web articles. The strategist crafts questions tailored to the known sources.

```
/notebooklm-research transformer architectures --sources https://youtube.com/... https://youtube.com/...
```

**Exploratory:** PM provides a topic (no specific sources). The strategist may direct workers to use NotebookLM's `research_start` feature for discovery via Google's search.

```
/notebooklm-research "AI agent architectures — what are experts saying"
```

**Hybrid:** PM provides some seed URLs plus a topic — strategist starts with known sources, identifies gaps, then expands via discovery.

## Platform Notes

- **macOS/Linux:** The `.mcp.json` command (`notebooklm-mcp`) works directly.
- **Windows:** Change the command to `cmd` with args `["/c", "notebooklm-mcp"]` in `.mcp.json`.

See `CLAUDE.md` for detailed operating notes, rate limits, and caveats.
