# NotebookLM Plugin — Operating Notes

This plugin provides access to Google NotebookLM via the [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) MCP server. It enables research on YouTube videos, podcasts, audio content, and other media that Claude cannot access directly.

## Plugin Lifecycle — Disabled by Default

This plugin is kept **disabled** in `settings.json` to avoid loading 35 MCP tools into the EM's context on every session. The `/notebooklm-research` command handles enabling the plugin at the start of a research run and disabling it when done. **The EM/coordinator should never call NotebookLM MCP tools directly** — all research flows through the `notebooklm-research-worker` agent dispatched by the command.

## Authentication

- **Initial login:** Run `nlm login` in a terminal. This opens a browser for Google account authentication and extracts session cookies automatically.
- **Credentials stored at:** `~/.notebooklm-mcp-cli/`
- **If auth fails mid-session:** Call the `refresh_auth` MCP tool first. If that fails, re-run `nlm login` in a separate terminal.

## Rate Limits

- Free tier: ~50 queries/day
- Source processing is async — use `source_add` with `wait: true` for synchronous behavior, or poll readiness via `notebook_get`

## Important Caveats

- Uses undocumented Google APIs — may break without notice
- NotebookLM is a Google product with its own terms of service
- AI-generated transcriptions and analysis may contain errors — cross-reference critical findings

## Notebook Housekeeping

Old research notebooks accumulate in the Google account. Periodically:
1. List notebooks via `notebook_list`
2. Delete stale research notebooks that are no longer needed
3. Watch for orphan notebooks from crashed or rate-limited sessions

## MCP Tools

The MCP server exposes ~35 tools. The research worker uses a subset (~13) for the research pipeline. The full tool list is available via `ToolSearch("notebooklm")`. Key tools for research:

- `notebook_create` / `notebook_delete` — lifecycle management
- `notebook_get` / `notebook_list` — status and inventory
- `source_add` — ingest URLs, YouTube links, Drive files, text, PDFs
- `source_describe` / `source_get_content` — inspect processed sources
- `notebook_query` — ask questions with AI, get cited responses
- `studio_create` / `studio_status` / `download_artifact` — generate reports, mind maps, slides
- `research_start` / `research_status` / `research_import` — cross-notebook research
- `refresh_auth` — refresh authentication tokens
