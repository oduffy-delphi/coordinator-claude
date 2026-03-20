# Game Dev Plugin

## UE Documentation

Sid uses Context7 for UE documentation research. Bootstrap before first use:

```
ToolSearch("select:mcp__plugin_context7_context7__resolve-library-id,mcp__plugin_context7_context7__query-docs")
```

**Key documentation sources:**

| Tool | Context7 ID | Purpose |
|------|-------------|---------|
| UE5 official docs | `/websites/dev_epicgames_en-us_unreal-engine` | High-level guidance, Blueprint, UMG, Animation |
| Vanilla C++ | `/websites/en_cppreference_w` | STL, algorithms, language features |
| GAS deep-dive | `/tranek/gasdocumentation` | Gameplay Ability System architecture |
| UE C++ patterns | `/mrrobinofficial/guide-unrealengine` | UE-specific C++ idioms |

## Sid's Role

Sid is the **architect and reviewer** for game development work. He uses Context7 documentation as part of deeper analysis — design decisions, code review, anti-pattern recognition, architecture recommendations.

**Routing rule:** Architecture and design → Sid. Patrik backstops on architectural soundness at High effort.

## Blueprint Inspection (Optional)

The `ue-blueprint-inspector` and `ue-blueprint-worker` agents require an MCP server connected to a running Unreal Editor. Without MCP, these agents cannot function.

If you configure a compatible MCP server:
- Connect it to a running UE Editor instance
- Ensure it exposes `manage_asset`, `inspect`, and `manage_blueprint` tools
- The inspector can then discover and document all Blueprints in your project
