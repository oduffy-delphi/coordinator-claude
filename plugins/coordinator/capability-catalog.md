<!-- Maintenance: update when plugins change. Version: 1.2 | Last reviewed: 2026-03-21 -->

# Specialists — Route, Don't Execute

## Why Delegation Is Superior, Not Just Correct

The EM sees 8 thin MCP tools; domain agents access 40+ via the `execute_domain_tool` proxy with full schemas loaded in fresh context. This isn't organizational hierarchy — it's a capability gap. Delegates have:
- **Tool access:** Hidden tools with typed parameters and validation the EM would need to ToolSearch for
- **Loaded knowledge:** Pre-baked domain patterns, verification protocols, and operational skills in their system prompts
- **Context efficiency:** Fresh Sonnet context dedicated to one task vs. Opus context juggling orchestration state

This design saves ~40K tokens of MCP schemas from the EM's context window — tokens better spent on orchestration judgment than tool definitions.

Before using a tool yourself, ask: would a specialist produce better results? The answer is almost always yes for multi-step work.

When a reviewer returns findings, **accept their expertise** — implement ALL items, including P2s, nitpicks, and suggestions to defer. Every finding is an opportunity to meet or exceed their quality bar. The only exceptions: escalate to the PM when findings change scope, or push back if you believe the reviewer is genuinely wrong (state why explicitly).

**Patrik** — architecture + code review. Use /review-dispatch.
**Enricher/Executor** — codebase research + implementation. Use /enrich-and-review, /delegate-execution.

**Camelia** — ML, statistics, RAG eval, training. Route: any AI/data pipeline work.

**Sid** — UE architecture + C++/BP design (has RAG access + war stories). Route: "should I use X?" design questions. Superior to you on UE idiom judgment.
**Blueprint Inspector** — automated BP documentation extraction. Route: "document all BPs."

**UE Editor** — 4 domain agents with typed tools you cannot access directly:
- world-builder (lighting, terrain, nav), asset-author (**BP graph ops — Python CANNOT do this**), gameplay-engineer (AI, GAS, combat), infra-engineer (perf, tests, networking)
- Blueprint graph operations (nodes, pins, functions) are impossible via Python — only ue-asset-author can do them. This is the strongest example of the capability gap.
- Use /dispatch or ue-editor-control skill. execute_python_code is the escape hatch for simple one-liners, not the default.

**ue-docs-researcher** — multi-source RAG synthesis (320K+ vectors). Route: multi-step UE lookups. Single lookups: quick_ue_lookup directly.

**NotebookLM** — break-glass for YouTube/podcasts/audio Claude can't access. Use /notebooklm-research. NOT for normal web research.

**Palí** — front-end review (tokens, design system, CSS). **Fru** — UX flow review (trust, clarity). Use /review-dispatch.

**Pipeline orchestrators** (dispatch via commands, not directly):
- **deep-research-orchestrator** — /deep-research dispatches this. Reads PIPELINE.md, runs Haiku→Sonnet→Opus.
- **bug-sweep-orchestrator** — /bug-sweep dispatches this. Scans→analyzes→triages→fixes.
- **architecture-audit-orchestrator** — /architecture-audit dispatches this. Inventories→analyzes→synthesizes atlas.
- **structured-research-orchestrator** — /structured-research dispatches this. Spec-driven batch research across multiple subjects.
