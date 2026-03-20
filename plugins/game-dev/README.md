# game-dev

Game development domain plugin. Enable for Unreal Engine and game development projects. **Disabled by default** — enable explicitly via per-project config.

## Components

**Agents:**
- `sid-game-dev` (Opus) — UE5 specialist, game systems architect, code reviewer
- `ue-blueprint-inspector` (Opus) — Blueprint documentation coordinator, dispatches Sonnet workers for large projects (requires UE Editor MCP)
- `ue-blueprint-worker` (Sonnet) — Mechanical per-BP inspection, dispatched by the inspector coordinator (requires UE Editor MCP)

**Routing:** Registers Sid for game dev signals with Patrik (coordinator) as backstop.

## Enabling

Add to your project's `.claude/coordinator.local.md`:

```yaml
---
project_type: game
---
```

Or explicitly list reviewers:

```yaml
---
active_reviewers:
  - patrik
  - sid
---
```

## Sid's Research Approach

Sid uses Context7 for UE documentation research rather than guessing. Key sources:
- `mcp__plugin_context7_context7__resolve-library-id` + `query-docs` for API lookups
- Epic's official UE5 documentation via Context7
- Community GAS documentation via Context7

## Blueprint Inspection (Optional MCP Feature)

The Blueprint inspector and worker agents require a UE Editor MCP server connected to a running Unreal Editor instance. This is not included in coordinator-em by default.

If you have a compatible MCP server, the inspector can:
- Discover all Blueprints in a project
- Dispatch parallel Sonnet workers for mechanical inspection
- Produce structured documentation with incremental update support

## Example Domain Plugin

This plugin also serves as a reference implementation for adding domain plugins. The structure (agents/, routing.md, README.md, optional CLAUDE.md) is the minimal required shape for any domain plugin.
