# coordinator-claude — A Structured Workflow System for Claude Code

A plugin set that turns Claude Code into a small engineering team: a coordinator that delegates, named specialists that review, and codified skills that encode best practices. You play PM; Claude plays EM.

## What This Does

Every pattern here — multi-agent orchestration, quality gates, model tiering, hooks-based context injection — exists elsewhere in the Claude Code ecosystem. The individual pieces aren't new. What's unusual is combining all of Claude Code's extension primitives (hooks, subagents, skills, commands, Agent Teams, MCP servers) into one coherent workflow stack, including early adoption of [Agent Teams](https://code.claude.com/docs/en/agent-teams) (still experimental and gated) as a first-class primitive for collaborative planning and research.

Three things are particularly distinctive within the Claude Code plugin ecosystem:

- **PM/EM authority partitioning.** Not "planner/coder/reviewer" — a persistent product-management authority split where the human owns product direction and the AI owns engineering execution, with explicit boundaries that carry across sessions.

- **Sequential review with mandatory fix gates.** Domain expert reviews first, all fixes applied, *then* the generalist reviews a clean artifact. Most tools use parallel-aggregate or single-pass review. This enforced sequencing is uncommon.

- **Agent Teams for collaborative planning.** Staff sessions where persona agents debate plans in parallel via Agent Teams messaging, then a synthesizer cross-references positions. Distinct from using Agent Teams for simple task fan-out.

For a deeper assessment, see the [novelty research doc](docs/research/2026-03-20-agent-orchestration-novelty-unified.md).

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
| **[coordinator](plugins/coordinator/)** | Core orchestration pipeline, universal reviewers, all workflow skills | Always |
| **[game-dev](plugins/game-dev/)** | Sid (Unreal Engine specialist) | Unreal Engine projects |
| **[web-dev](plugins/web-dev/)** | Pali (front-end architecture) + Fru (UX flow review) | Web projects |
| **[data-science](plugins/data-science/)** | Camelia (ML, statistics, data modeling) | ML/data work |
| **[deep-research](plugins/deep-research/)** | Multi-agent research pipelines (internet, repo, structured) | Research tasks |
| **[notebooklm](plugins/notebooklm/)** | NotebookLM integration — YouTube, podcast, audio research via MCP | Media research (enable on demand) |

The coordinator plugin is always enabled. Domain plugins are toggled per-project via `.claude/coordinator.local.md`.

See [architecture.md](docs/architecture.md) for the full conceptual model — how agents interact, how the pipeline flows, and the design philosophy behind it.

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

## Context Injection: Tiered "Warm RAM"

The coordinator uses three tiers of context, not bulk injection:

```
L1 (always loaded)    CLAUDE.md + MEMORY.md + orientation cache (~200 lines)
L2 (on-demand)        DIRECTORY.md, health ledger, repomap, architecture atlas
L3 (deep storage)     Codebase, git history — read by subagents, never bulk-loaded
```

The **orientation cache** is an ephemeral daily file generated between sessions and injected at start via a `SessionStart` hook. It contains repo structure, health snapshot, recent work summary, and self-invalidating VCS metadata (`git_head_at_generation`). Every L1 entry points to an L2 artifact for drill-down.

## Version History

- **v1.1.1** — Staff sessions (Agent Teams for collaborative planning/review), README positioning rewrite
- **v1.1.0** — Agent Teams adoption for all research pipelines; deep-research extracted to standalone plugin; context pressure advisory hooks
- **v1.0.0** — Initial public release: 6 plugins, 24 agents, 38 skills, enrichment-review-execution pipeline

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
coordinator-claude/
├── plugins/
│   ├── coordinator/            # Core orchestration (always enabled)
│   │   ├── .claude-plugin/plugin.json
│   │   ├── agents/             # enricher, executor, patrik, zoli, review-integrator, staff-synthesizer
│   │   ├── commands/           # handoff, session-start, session-end, staff-session, etc.
│   │   ├── hooks/              # coordinator-reminder hook + capability catalog emission
│   │   ├── pipelines/          # staff-session/ (team protocol + prompt templates)
│   │   └── skills/             # 38 workflow skills (brainstorming, TDD, debugging, etc.)
│   ├── game-dev/               # Sid (Unreal Engine specialist)
│   ├── web-dev/                # Pali (front-end) + Fru (UX flow)
│   ├── data-science/           # Camelia (ML, statistics)
│   ├── deep-research/          # Agent Teams research pipelines (A: web, B: repo, C: structured)
│   └── notebooklm/             # NotebookLM media research via Agent Teams
├── docs/                       # Architecture, customization, CI pipeline
├── setup/                      # Installer
└── assets/                     # Social preview card + generation template
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
