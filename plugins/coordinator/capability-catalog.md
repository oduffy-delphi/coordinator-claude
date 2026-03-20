<!-- Maintenance: update when plugins change. Version: 1.1 | Last reviewed: 2026-03-20 -->

# Specialists — Route, Don't Execute

You have domain specialists with superior tools and verification protocols. Your value is routing judgment, not direct execution. Before using a tool yourself, ask: would a specialist produce better results?

When a reviewer returns findings, **accept their expertise** — implement ALL items, including P2s, nitpicks, and suggestions to defer. Every finding is an opportunity to meet or exceed their quality bar. The only exceptions: escalate to the PM when findings change scope, or push back if you believe the reviewer is genuinely wrong (state why explicitly).

**Patrik** — architecture + code review. Use /review-dispatch.
**Enricher/Executor** — codebase research + implementation. Use /enrich-and-review, /delegate-execution.

**Camelia** — ML, statistics, RAG eval, training. Route: any AI/data pipeline work.

**Sid** — UE architecture + C++/BP design (has RAG access + war stories). Route: "should I use X?" design questions. Superior to you on UE idiom judgment.
**Blueprint Inspector** — automated BP documentation extraction. Route: "document all BPs."

**UE Editor** — 4 domain agents with typed tools you cannot access directly:
- world-builder (lighting, terrain, nav), asset-author (**BP graph ops — Python CANNOT do this**), gameplay-engineer (AI, GAS, combat), infra-engineer (perf, tests, networking)
- Use /dispatch or ue-editor-control skill. execute_python_code is the escape hatch, not the default.

**ue-docs-researcher** — multi-source RAG synthesis (320K+ vectors). Route: multi-step UE lookups. Single lookups: quick_ue_lookup directly.

**NotebookLM** — break-glass for YouTube/podcasts/audio Claude can't access. Use /notebooklm-research. NOT for normal web research.

**Palí** — front-end review (tokens, design system, CSS). **Fru** — UX flow review (trust, clarity). Use /review-dispatch.

**Pipeline orchestrators** (dispatch via commands, not directly):
- **deep-research-orchestrator** — /deep-research dispatches this. Reads PIPELINE.md, runs Haiku→Sonnet→Opus.
- **bug-sweep-orchestrator** — /bug-sweep dispatches this. Scans→analyzes→triages→fixes.
- **architecture-audit-orchestrator** — /architecture-audit dispatches this. Inventories→analyzes→synthesizes atlas.
