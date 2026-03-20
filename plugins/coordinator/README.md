# coordinator

Core orchestration plugin. Always enabled on every project.

## What It Does

The coordinator plugin is the backbone of the system. It provides:

1. **The orchestration role** — the main session agent operates as EM (engineering manager), delegating work to specialized subagents rather than implementing directly
2. **Universal reviewers** — Patrik (code quality, architecture) and Zoli (ambition backstop) are available on every project regardless of domain
3. **Workflow skills** — 21 codified processes (SKILL.md) covering the full development lifecycle, plus 7 pipeline definitions (PIPELINE.md) backing commands
4. **Session commands** — slash commands for pipeline operations (dispatch executors, route reviews, manage handoffs)

## Components

### Agents

| Agent | Model | Role |
|-------|-------|------|
| **enricher** | Sonnet | Research agent — surveys codebases, traces deps, fills in stub details |
| **executor** | Sonnet | Implementation agent — follows specs precisely, reports DONE/DONE_WITH_CONCERNS/BLOCKED |
| **review-integrator** | Sonnet | Applies reviewer findings to artifacts with annotations, escalates disagreements |
| **patrik-code-review** | Opus | Senior engineer reviewer — exacting standards, documentation completeness, architecture |
| **zoli-ambition-advocate** | Opus | Backstop reviewer — challenges conservative recommendations, never a primary reviewer |
| **structured-research-orchestrator** | Opus | Pipeline C orchestrator — owns full research lifecycle per subject, dispatches Haiku/Sonnet sub-agents |

### Commands (19, all user-invocable via `/`)

| Command | Purpose |
|---------|---------|
| `/session-start` | Orient session — preflight, load context, choose work |
| `/session-end` | Wrap up finished work — capture lessons, update docs |
| `/handoff` | Save session state for next session handoff |
| `/workday-start` | Morning orientation — triage handoffs, surface staleness, align priorities |
| `/workday-complete` | End-of-day — update docs, consolidate branches, run health survey |
| `/update-docs` | Repo-wide documentation maintenance and sync |
| `/delegate-execution` | Dispatch enriched stubs to executor agents |
| `/execute-plan` | Execute a PM-approved implementation plan in the coordinator session |
| `/enrich-and-review` | Run enrichment pipeline on chunk directories |
| `/review-dispatch` | Route artifacts to the right reviewer |
| `/generate-repomap` | Generate a ranked repository map for LLM context injection |
| `/mise-en-place` | Autonomous backlog execution — gather ready items, execute without stopping |
| `/deep-research` | Deep research pipeline — codebase (Pipeline A) or internet sources (Pipeline B) |
| `/structured-research` | Batch research across multiple subjects with repeating structure and output schema |
| `/architecture-audit` | Bootstrap or refresh the architecture atlas via multi-phase agent pipeline |
| `/architecture-rotation` | Run the weekly architecture audit rotation — score, audit, apply, update ledger |
| `/code-health` | Night-shift code health review — scan commits, dispatch reviewer, apply findings |
| `/bug-sweep` | Systematic codebase bug hunt — fix AI-fixable bugs, defer blocked ones to backlog |
| `/notebooklm-research` | Research via Google NotebookLM — YouTube, podcasts, audio. Requires notebooklm plugin |

### Skills (21)

**Workflow & Planning:**
- `brainstorming` — Collaborative dialogue to refine ideas into designs. Scope assessment, design-for-isolation, existing-codebase awareness.
- `writing-plans` — Decompose designs into executable tasks. Scope checking, file structure mapping, TDD-oriented granularity.
- `executing-plans` — Execute plans task-by-task with review checkpoints. Prefers `/delegate-execution` in coordinator sessions.
- `verification-before-completion` — Prove it works before claiming it's done.
- `deep-research` — Multi-source investigation of repos or topics.

**Development Process:**
- `test-driven-development` — RED-GREEN-REFACTOR cycle, strictly enforced.
- `systematic-debugging` — Root-cause debugging process.
- `dispatching-parallel-agents` — Dispatch independent tasks in parallel.
- `stuck-detection` — Self-monitoring protocol — repetition, oscillation, analysis paralysis detection.

**Code Review:**
- `requesting-code-review` — Request review via `/review-dispatch`.
- `receiving-code-review` — How to receive and act on review feedback.

**Git & Branching:**
- `using-git-worktrees` — Isolated workspaces per feature.
- `finishing-a-development-branch` — Complete development, PR, merge.
- `merging-to-main` — PR creation, CI gating, merge, cleanup.

**Writing & Meta:**
- `writing-skills` — TDD applied to skill/documentation authoring.
- `skill-discovery` — Find and use skills. SUBAGENT-STOP gate, instruction priority hierarchy.
- `validate` — Run all CI validation checks locally.

**Health & Maintenance:**
- `debt-triage` — Review and prioritize the technical debt backlog. EM-PM conversation, not dispatched agent.
- `tracker-maintenance` — Maintain the project tracker — archive completed work, update dependencies, sweep for untracked commits.
- `lessons-trim` — Trim stale entries from lessons files, merge duplicates, clean up feature-scoped files.
- `handoff-archival` — Archive consumed handoffs older than 48 hours, migrate legacy locations.
- `atlas-integrity-check` — Check changed files against the architecture atlas for unmapped entries.
- `project-onboarding` — Bootstrap project tracking infrastructure — tracker, tasks, archive, handoffs.

### Pipelines (7)

- `bug-sweep` — Systematic codebase bug hunt pipeline
- `daily-code-health` — Commit review + dispatch + apply findings
- `deep-architecture-audit` — Deep-dive audit of a specific system
- `deep-research` — Codebase (Pipeline A) and internet (Pipeline B) research
- `executing-plans` — Task-by-task plan execution with checkpoints
- `mise-en-place` — Autonomous backlog execution
- `weekly-architecture-audit` — Rotation-based audit with scoring

### Hooks

- **SessionStart** — Coordinator discipline reminder (sets EM role, loads pipeline awareness)
- **PreToolUse** (WebSearch/WebFetch) — Delegation nudge: suggests Sonnet subagent for multi-query research
- **PostToolUse** (ExitPlanMode) — Plan persistence check: ensures plan content is saved to disk
- **SubagentStop** — Executor exit watchdog: detects thrashing, forces post-mortem

## Routing Extension Protocol

The coordinator defines the routing framework that domain plugins extend:

1. This plugin's `routing.md` defines universal reviewers (Patrik, Zoli) and the routing algorithm
2. Domain plugins contribute routing fragments via their own `routing.md` files
3. At dispatch time, `/review-dispatch` merges all fragments into a composite routing table
4. Signals from changed code determine which reviewer handles the review

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full conceptual model.

## Per-Project Config

Create `.claude/coordinator.local.md` in your project:

```yaml
---
project_type: web    # web | game | data-science | pure-docs
---
```

Default (no config): core-only (Patrik + Zolí).

## Version History

### v1.3.0 (March 2026) — Squad Expansion

- **Review-integrator:** New Opus agent that applies reviewer findings to artifacts. Replaces manual EM feedback application in review-dispatch, enrich-and-review, and delegate-execution. The EM now verifies rather than types.
- **Reviewer self-checks:** All 6 reviewers get built-in self-moderation prompts.
- **Routing intelligence:** Effort calibration table, skip conditions, and EM override guidance added to routing.md.
- **Health infrastructure:** New skills (debt-triage, tracker-maintenance, lessons-trim) with templates.
- **Session-start health surface:** New Step 0g reads health ledger and surfaces findings (non-blocking).
- **Workday-complete redesign:** Branch consolidation + health survey. No longer merges to main — merging is a deliberate, supervised act via /merge-to-main.
- **Merge-to-main hardening:** New Step 0 test suite gate with --force escape hatch.

### v1.2.0 (March 2026) — Write-Ahead Status Protocol

All pipeline phases now mark documents *before* starting work, not just on completion.

- Enricher: marks stub as "Enrichment in progress" before research
- Executor: marks stub as "Execution in progress" before implementation
- All commands updated with write-ahead phases

### v1.1.0 (March 2026) — Superpowers v5.0.0 Absorption

- Brainstorming: scope assessment, design-for-isolation principles
- Writing-plans: scope check, file structure mapping
- Executor: DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT protocol
- Delegate-execution: spec compliance verification
- Skill-discovery: SUBAGENT-STOP gate, instruction priority hierarchy
