# notebooklm

Google NotebookLM integration plugin. Enables research on YouTube videos, podcasts, audio content, and other media Claude cannot access directly. **Disabled by default** — managed automatically by the `/notebooklm-research` command.

## Components

**Agents:**
- `notebooklm-research-worker` (Sonnet) — Mechanical research execution via MCP. Creates notebooks, ingests sources, runs queries, writes structured findings. Dispatched by the coordinator's `/notebooklm-research` command.

**MCP Server:** `notebooklm-mcp` via [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) (MIT license). Exposes ~35 tools for notebook management, source ingestion, querying, and artifact generation.

## Prerequisites

1. Install the MCP CLI: `pip install notebooklm-mcp-cli`
2. Authenticate: `nlm login` (opens browser for Google account auth)

## How It Works

The plugin lifecycle is managed by the `/notebooklm-research` command:

1. Command enables the plugin in `settings.json`
2. Reloads plugins to load MCP tools
3. Dispatches the research worker agent
4. Worker creates notebook, ingests sources, runs queries
5. Coordinator synthesizes raw findings into a polished research document
6. Command disables the plugin to remove MCP tools from future sessions

This enable/disable pattern keeps 35 MCP tools out of the coordinator's context during normal sessions.

## Platform Notes

- **macOS/Linux:** The `.mcp.json` command (`notebooklm-mcp`) works directly.
- **Windows:** Change the command to `cmd` with args `["/c", "notebooklm-mcp"]` in `.mcp.json`.

See `CLAUDE.md` for detailed operating notes, rate limits, and caveats.
