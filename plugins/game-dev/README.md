# game-dev

Game development domain plugin for the Donal + Claude agent hierarchy. Enable for Unreal Engine and game development projects.

## Components

**Agents:**
- sid-game-dev (Opus) — UE5 specialist, game systems architect, code reviewer
- ue-blueprint-inspector (Opus) — Blueprint documentation coordinator, dispatches Sonnet workers for large projects
- ue-blueprint-worker (Sonnet) — mechanical per-BP inspection via MCP, dispatched by the inspector coordinator

**Dependencies:** holodeck-docs plugin (UE documentation lookup — agent, skill, command)

**MCP Servers:** holodeck-docs (UE documentation RAG), holodeck-control (UE Editor integration) — configured globally in `~/.claude.json`

**Routing:** Registers Sid for game dev signals with Patrik (coordinator) as backstop. Simple doc lookups route to holodeck-docs plugin's ue-docs-researcher (Sonnet); architecture and review route to Sid (Opus).

## Standalone Plugin

The game-dev plugin is self-contained within this repository. MCP servers (`holodeck-control` for UE Editor integration, `holodeck-docs` for documentation RAG) are configured separately in your `~/.claude.json` per the Unreal Engine tooling docs. The plugin works without them — Sid's review and architecture capabilities don't require MCP — but Blueprint inspection and live editor authoring do.

## Authors

Donal O'Duffy & Claude
