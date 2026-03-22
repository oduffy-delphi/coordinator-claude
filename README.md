# oduffy-custom — A Custom Agent Hierarchy for Claude Code

A local plugin marketplace that extends [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with a structured agent hierarchy: named specialist reviewers, an orchestration pipeline, and codified workflow skills. Built by Dónal O'Duffy and Claude as a collaborative development environment.

## What This Is

Claude Code ships with a powerful but general-purpose agent. Out of the box, it reads files, writes code, and runs commands — but it doesn't have opinions about *how* to organize work, *when* to ask for review, or *who* should review what.

This plugin set layers a structured workflow on top of Claude Code:

- **Named specialist agents** with distinct expertise and personalities (a senior engineer who reviews code quality, a UX specialist who evaluates user flows, a game dev expert who knows Unreal Engine)
- **A coordinator role** that orchestrates multi-step work through an enrichment-review-execution pipeline
- **Codified workflow skills** that encode best practices as repeatable processes (brainstorming, TDD, plan writing, systematic debugging)
- **A review pipeline** that routes work to the right specialist based on what changed

The result is something like a small engineering team, where Claude plays multiple roles with different perspectives, and the human (Dónal) serves as PM — setting direction, making judgment calls, and approving designs.

## What's Novel

A [deep research assessment](../../docs/research/2026-03-20-agent-orchestration-novelty-unified.md) (140+ sources, 70+ deep-read) evaluated this system against the AI agent framework ecosystem, coding tools, and academic literature. Individual patterns — manager-worker hierarchies, role-based agents, model routing — all have precedent. What's new is the specific combination and operational philosophy:

**Genuinely novel (no documented prior art):**

- **Cognitive tiering** — Different model tiers do different *cognitive work*, not the same work at different capability levels. Haiku verifies (template checks, compile checks), Sonnet executes (code writing, analysis), Opus judges (synthesis, planning). The academic literature covers cost cascading ("same task, cheaper model first") and capability routing ("best model for domain"), but a [2026 survey](https://arxiv.org/html/2603.04445) explicitly identifies our approach as a research gap.

- **Sequential review with mandatory fix gates** — Domain expert reviews first, ALL fixes applied, then generalist reviews a clean artifact. Every surveyed tool (GitHub Copilot, CodeRabbit, Anthropic's own code review tool) uses parallel+aggregate or single-pass. The "apply all fixes before Reviewer 2 sees the work" pattern is absent everywhere. (For pre-implementation planning and plan review, the system also offers **parallel debate via staff sessions** — persona agents challenge each other's positions simultaneously. Both patterns coexist: sequential for post-execution code review, parallel debate for collaborative planning.)

- **PM/EM authority partitioning** — Standing role-level domain authority boundaries between human (PM) and AI (EM) that persist across sessions. The [National Academies](https://nap.nationalacademies.org/read/26355/chapter/4) identified persistent human-AI relationships as an explicit research gap. This system operationally answers it.

**Compositionally novel:**

- **Proactive orientation cache ("warm RAM")** — An ephemeral daily cache generated between sessions and injected at start, with self-invalidating VCS metadata and explicit pointers to full artifacts. Not RAG, not full injection, not cold start. Five-property combination undocumented across 87 sources. Anthropic's [context engineering blog](https://anthropic.com/engineering/effective-context-engineering-for-ai-agents) describes the principle; this system implements it with proactive generation. The Claude Code community is independently requesting this capability ([#11455](https://github.com/anthropics/claude-code/issues/11455), [#18417](https://github.com/anthropics/claude-code/issues/18417)).

**Novel applications of known principles:**

- **Selective tool withholding** — MCP tools deliberately withheld from the orchestrator, forcing delegation. Microsoft [recommends](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) least-privilege for agents; no framework enforces it as a design principle.

- **Character Personas in engineering review** — Named reviewers (Patrik, Sid, Camelia) are [tier 2 Character Personas](https://arxiv.org/html/2404.18231v2), not tier 1 functional role labels. All prior multi-agent review systems use tier 1. The naming serves human cognitive convenience; the persona depth produces better review output.

- **Plugin-based capability composition** — Agents, skills, commands, hooks, and MCP config bundled into per-domain packages with per-project scoping via `coordinator.local.md`. Individual primitives are platform features; the opinionated composition is undocumented.

## The Organizational Metaphor

The system borrows from engineering management practice:

| Role | Who | Responsibility |
|------|-----|---------------|
| **PM (Captain)** | Dónal | Vision, priorities, judgment calls, design approval |
| **EM / Coordinator (First Officer)** | Claude (main session) | Orchestration, delegation, spec compliance, pipeline flow |
| **Executor** | Claude (subagent, Sonnet) | Faithful implementation of well-specified work |
| **Reviewers** | Claude (subagents, Opus) | Code quality, UX, domain expertise — each with a named identity and perspective |

This is the "First Officer Doctrine" — Claude operates as EM to Dónal's PM. The EM executes with ambition, counsels honestly when they disagree, and clarifies scope when it's ambiguous. Silent compliance into a bad outcome is a failure of the role.

## Plugins

| Plugin | Purpose | When to Enable |
|--------|---------|----------------|
| **[coordinator](coordinator/)** | Core orchestration pipeline, universal reviewers, all workflow skills | Always |
| **[game-dev](game-dev/)** | Sid (Unreal Engine specialist) + UE MCP servers | Unreal Engine projects |
| **[web-dev](web-dev/)** | Pali (front-end architecture) + Fru (UX flow review) | Web projects |
| **[data-science](data-science/)** | Camelia (ML, statistics, data modeling) | ML/data work |
| **[holodeck-control](holodeck-control/)** | UE editor control agents (world-builder, asset-author, gameplay-engineer, infra-engineer) | Unreal Engine editor projects |
| **[holodeck-docs](holodeck-docs/)** | UE documentation lookup + Python execution | Unreal Engine projects |
| **[notebooklm](notebooklm/)** | NotebookLM integration — YouTube, podcast, audio research via MCP | Media research (enable on demand) |

The coordinator plugin is always enabled. Domain plugins are toggled per-project via `.claude/coordinator.local.md`.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full conceptual model — how agents interact, how the pipeline flows, and the design philosophy behind it.

## The Pipeline

A typical feature goes through these stages:

```
Brainstorm  →  Plan  →  Execute  →  Review  →  Ship
   (skill)    (skill     (executor    (Patrik     (finish
               or staff   agents)     + domain     branch)
               session)               reviewers)
```

The **Plan** stage has two paths:
- **EM writes plan** → single-reviewer dispatch (lightweight, existing flow)
- **Staff session** → parallel debate between staff engineers (Patrik + Zoli, or domain experts) who craft the plan collaboratively via Agent Teams. The EM writes objectives; the team writes the blueprint.

Each stage is a codified skill or command. The coordinator orchestrates transitions between stages and verifies output at each checkpoint.

## Context-for-Orientation: The "Warm RAM" Pattern

Most agent frameworks solve the context problem by either injecting everything (burning the context window) or injecting nothing (cold start every session). This system takes a third approach: **tiered context injection with an ephemeral orientation cache**.

```
L1 (always loaded)    CLAUDE.md + MEMORY.md + orientation cache
                      ~200 lines — what matters, where to look
                          │
L2 (on-demand)        DIRECTORY.md, health ledger, repomap, architecture atlas
                      Full artifacts on disk — loaded when a task needs them
                          │
L3 (deep storage)     The codebase, git history, pipeline docs
                      Read by subagents as needed — never bulk-loaded into the coordinator
```

The key mechanism is the **orientation cache** — an ephemeral daily file generated by the `update-docs` pipeline and loaded at session start via a `SessionStart` hook. It contains:

- Repo structure summary (not the full tree — a TL;DR with component counts)
- Health snapshot (system grades and audit dates from the health ledger)
- Recent work summary (what changed, what shipped, what's pending)
- Metadata: `generated_at`, `git_head_at_generation` (self-invalidating — you know exactly how stale it is)

This solves the **orientation problem** specifically: *what state is the world in right now, and where do I go to learn more?* The coordinator starts every session with enough context to route correctly, without burning context window on raw data. It's the difference between giving someone a filing cabinet and giving them a table of contents.

The paper trail matters as much as the summary. Every L1 entry points to an L2 artifact. The orientation cache says "coordinator-core is A/HEALTHY, audited 2026-03-18" — the coordinator knows the grade without loading the 200-line audit report, but can find it instantly if needed.

## Version History

- **v1.0.0** (March 2026) — Initial plugin architecture. Four plugins, 5 agents, 7 commands, 13 skills. Absorbed workflow skills from Superpowers framework, added named reviewer agents with distinct personalities, built enrichment-review-execution pipeline.
- **v1.1.0** (March 2026) — Absorbed improvements from Superpowers v5.0.0: scope assessment in brainstorming, file structure planning, executor status protocol (DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT), expanded self-review with judgment checks, spec compliance verification in delegation pipeline, instruction priority hierarchy, subagent gate for skill discovery.
- **v1.2.0** (March 2026) — Write-ahead status protocol. All pipeline phases now mark plan/stub documents as "in progress" *before* starting work, not just on completion. Two-layer breadcrumbs (tracker README + stub header) eliminate ambiguous state after crashes. Enricher, executor, enrich-and-review, delegate-execution, review-dispatch, and executing-plans all updated. Plan document header now includes a `Status:` field.
- **v1.3.0** (March 2026) — Boot-time capability catalog. `capability-catalog.md` injected at session start via coordinator hook — behavioral primer ("Route, Don't Execute") that lists all specialists with one-line routing guidance. Universal emission (no per-project filtering), meta-mode exclusion, graceful degradation. Fixed holodeck-control hooks.json format bug (silent failure since creation). See ARCHITECTURE.md § Boot-Time Behavioral Priming.
- **v1.4.0** (March 2026) — Agent Teams adoption. All 4 research pipelines (A: Internet, B: Repo, C: Structured, D: NotebookLM) migrated to Agent Teams (fire-and-forget team pattern). Deep-research extracted to standalone plugin. NotebookLM ported to two-phase spawn with quota-aware sizing.
- **v1.5.0** (March 2026) — Staff sessions (`/staff-session`). Agent Teams-based collaborative planning and review with configurable tiers (lightweight/standard/full). Two genres: plan mode (staff engineers craft plans from PM/EM objectives via parallel debate) and review mode (multi-perspective critique of existing artifacts). New debate messaging protocol (POSITION/CHALLENGE/CONCESSION/QUESTION). All 6 persona agents updated with Agent Teams tools. New `staff-synthesizer` agent for cross-referencing debate positions.

---

## Setup on a New Machine

### Prerequisites
- Claude Code CLI installed
- This repo cloned to `~/.claude/`

### Step 1: Register the marketplace

```bash
claude plugin marketplace add ~/.claude/plugins/oduffy-custom
```

This adds the marketplace to `known_marketplaces.json` and `settings.json` (`extraKnownMarketplaces`).

### Step 2: Register plugins in installed_plugins.json

As of March 2026, `claude plugin install` does not fully support directory-based local marketplaces — it adds to `settings.json` but not `installed_plugins.json`. Add entries manually:

```jsonc
// In ~/.claude/plugins/installed_plugins.json, add to "plugins" object:
"coordinator@oduffy-custom": [{
  "scope": "user",
  "installPath": "C:\\Users\\<USERNAME>\\.claude\\plugins\\oduffy-custom\\coordinator",
  "version": "1.0.0",
  "installedAt": "<ISO-TIMESTAMP>",
  "lastUpdated": "<ISO-TIMESTAMP>"
}],
"game-dev@oduffy-custom": [{
  "scope": "user",
  "installPath": "C:\\Users\\<USERNAME>\\.claude\\plugins\\oduffy-custom\\game-dev",
  "version": "1.0.0",
  "installedAt": "<ISO-TIMESTAMP>",
  "lastUpdated": "<ISO-TIMESTAMP>"
}],
"web-dev@oduffy-custom": [{
  "scope": "user",
  "installPath": "C:\\Users\\<USERNAME>\\.claude\\plugins\\oduffy-custom\\web-dev",
  "version": "1.0.0",
  "installedAt": "<ISO-TIMESTAMP>",
  "lastUpdated": "<ISO-TIMESTAMP>"
}],
"data-science@oduffy-custom": [{
  "scope": "user",
  "installPath": "C:\\Users\\<USERNAME>\\.claude\\plugins\\oduffy-custom\\data-science",
  "version": "1.0.0",
  "installedAt": "<ISO-TIMESTAMP>",
  "lastUpdated": "<ISO-TIMESTAMP>"
}]
```

### Step 3: Enable plugins in settings.json

Add to the `enabledPlugins` object in `~/.claude/settings.json`:

```jsonc
"coordinator@oduffy-custom": true,
"game-dev@oduffy-custom": true,    // or false if not doing game dev
"web-dev@oduffy-custom": true,     // or false if not doing web dev
"data-science@oduffy-custom": true  // or false if not doing data science
```

### Step 4: Create cache junctions (development workflow)

Claude Code reads from a cache directory, not directly from source. For a development workflow where you edit plugin source files directly, replace cache copies with junctions so edits are instantly visible:

```cmd
rem Run from ~/.claude/
rem For each plugin, replace cache with junction to source:
mklink /J plugins\cache\oduffy-custom\coordinator\1.0.0 plugins\oduffy-custom\coordinator
mklink /J plugins\cache\oduffy-custom\game-dev\1.1.0 plugins\oduffy-custom\game-dev
mklink /J plugins\cache\oduffy-custom\web-dev\1.0.0 plugins\oduffy-custom\web-dev
mklink /J plugins\cache\oduffy-custom\data-science\1.0.0 plugins\oduffy-custom\data-science
mklink /J plugins\cache\oduffy-custom\notebooklm\1.0.0 plugins\oduffy-custom\notebooklm
```

On macOS/Linux: `ln -sf ~/.claude/plugins/oduffy-custom/{plugin} ~/.claude/plugins/cache/oduffy-custom/{plugin}/{version}`

> **Note:** If installing from a git-based marketplace (not developing locally), the cache is managed by Claude Code automatically and this step is unnecessary.

### Step 5: Restart Claude Code

Start a new session and verify with `/reload-plugins`. You should see all custom plugin components in the count.

## Directory Structure

```
oduffy-custom/
├── .claude-plugin/
│   └── marketplace.json    # Marketplace manifest listing all plugins
├── ARCHITECTURE.md         # Conceptual model and design philosophy
├── coordinator/            # Core orchestration (always enabled)
│   ├── .claude-plugin/plugin.json
│   ├── capability-catalog.md # Boot-time behavioral primer (Route, Don't Execute)
│   ├── routing.md          # Base routing table (universal reviewers)
│   ├── agents/             # enricher, executor, patrik, zoli, review-integrator, staff-synthesizer
│   ├── commands/           # handoff, session-start, session-end, staff-session, etc.
│   ├── hooks/              # coordinator-reminder hook + capability catalog emission
│   ├── pipelines/          # staff-session/ (team protocol + prompt templates)
│   └── skills/             # brainstorming, executing-plans, requesting-staff-session, etc.
├── game-dev/               # Game development domain
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json           # UE MCP server config
│   ├── routing.md          # Routing fragment: Sid
│   └── agents/             # sid
├── web-dev/                # Web development domain
│   ├── .claude-plugin/plugin.json
│   ├── routing.md          # Routing fragment: Pali, Fru
│   └── agents/             # pali, fru
├── data-science/           # Data science domain
│   ├── .claude-plugin/plugin.json
│   ├── routing.md          # Routing fragment: Camelia
│   └── agents/             # camelia
├── holodeck-control/       # UE editor control domain
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json           # Holodeck control MCP server
│   ├── routing.md          # Routing fragment: 4 domain agents
│   └── agents/             # world-builder, asset-author, gameplay-engineer, infra-engineer
├── holodeck-docs/          # UE documentation domain
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json           # Holodeck docs MCP server
│   └── agents/             # ue-docs-researcher, ue-python-executor
├── deep-research/          # Multi-agent research pipelines
│   ├── .claude-plugin/plugin.json
│   ├── CLAUDE.md            # Pipeline A/B/C documentation
│   ├── agents/             # research-scout, research-specialist, research-synthesizer,
│   │                       # repo-scout, repo-specialist, structured-synthesizer
│   ├── commands/           # deep-research, deep-research-web, deep-research-repo, deep-research-structured
│   └── pipelines/          # team protocols + prompt templates (A: web, B: repo, C: structured)
└── notebooklm/             # NotebookLM media research (Agent Teams)
    ├── .claude-plugin/plugin.json
    ├── .mcp.json           # NotebookLM MCP server (plugin-scoped)
    ├── CLAUDE.md            # Operating notes + auth guide
    ├── agents/             # strategist, scout, worker, synthesizer
    └── pipelines/          # team protocol + prompt templates
```

## Key Files (Not in This Directory)

- `~/.claude/settings.json` — Plugin enable/disable state + marketplace registration
- `~/.claude/plugins/installed_plugins.json` — Plugin install records
- `~/.claude/plugins/known_marketplaces.json` — Marketplace registry
- `~/.claude/CLAUDE.md` — Global development principles (the "constitution")

## Troubleshooting

**Plugins not showing as skills/commands:**
- Check `enabledPlugins` in `settings.json` — must be `true`
- Check `installed_plugins.json` — must have entry with correct `installPath`
- Restart Claude Code (changes take effect on next session)

**CLI `plugin install` fails silently:**
- Known issue with directory-based local marketplaces (March 2026)
- Use manual JSON entries as described in Step 2

**Per-project plugin selection:**
- Use `.claude/coordinator.local.md` with `project_type` field
- coordinator is always enabled; domain plugins enabled per-project

**Plugin cache not syncing (solved with junctions):**
- Claude Code reads plugins from `~/.claude/plugins/cache/oduffy-custom/{plugin}/{version}/`, not from source
- **Fix:** Replace cache directories with Windows junctions pointing to source. This makes edits to source instantly visible in cache — no manual copying needed.
- Setup (run from `~/.claude/`):
  ```cmd
  rem Remove the real cache directory, then create a junction to source
  rmdir /s /q plugins\cache\oduffy-custom\{plugin}\{version}
  mklink /J plugins\cache\oduffy-custom\{plugin}\{version} plugins\oduffy-custom\{plugin}
  ```
- On macOS/Linux, use symlinks instead: `ln -sf`
- Junctions don't require admin privileges on Windows
- All oduffy-custom plugins should have junctions set up — see Step 2 below

**New plugin not found in marketplace:**
- Plugin must be listed in `~/.claude/plugins/oduffy-custom/.claude-plugin/marketplace.json`
- Without a marketplace entry, `installed_plugins.json` + `settings.json` entries will error: "Plugin not found in marketplace"

**Plugin-scoped MCP server not starting (Windows):**
- Use `"command": "cmd", "args": ["/c", "your-command"]` in `.mcp.json` — bare command names may not resolve through the plugin loader's PATH
- Verify the MCP server starts manually: `echo '{}' | your-command --help`

## Authors

Dónal O'Duffy & Claude
