# coordinator-claude

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![Opus](https://img.shields.io/badge/Model-Opus_4.6-orange)](https://www.anthropic.com/claude)
[![Plugins](https://img.shields.io/badge/Plugins-5-green)](#what-you-get)
[![Skills](https://img.shields.io/badge/Skills-20+-green)](#codified-skills)
[![CI](https://img.shields.io/badge/CI-10_checks-brightgreen)](.github/workflows/validate-plugins.yml)

**A Claude Code plugin system that turns human-AI collaboration into a structured PM-EM partnership — with research pipelines, multi-session continuity, and quality gates that go beyond what's available out of the box.**

> This isn't another "AI assistant" wrapper. It's an organizational model for working with Claude Code at scale — across sessions, across domains, across days. You set the heading; the coordinator makes it so.

---

**Contents:** [Why This Exists](#why-this-exists) · [What's Genuinely Different](#whats-genuinely-different) · [What You Get](#what-you-get) · [How a PM Uses This](#how-a-pm-uses-this) · [Quick Start](#quick-start) · [Customization](#customization) · [Architecture](#architecture) · [Credits](#credits--acknowledgments) · [License](#license)

**Quick install:**
```bash
git clone https://github.com/oduffy-delphi/coordinator-claude.git
cd coordinator-claude && bash setup/install.sh
```
Then start Claude Code and run `/session-start`. See [Getting Started](docs/getting-started.md) for detailed setup.

## Why This Exists

Claude Code out of the box is powerful but stateless. Each session starts cold. Research means a single web search or tool call. Reviews are one-pass. There's no structured way to hand work from Tuesday's session to Wednesday's, no way to run a multi-source research campaign, and no model for deciding what *Claude* should own versus what *you* should own.

This plugin system addresses those gaps:

- **Research that actually researches.** Multi-agent pipelines that fan out across sources, cross-verify, and synthesize — not a single search call hoping for the best.
- **Sessions that remember.** Structured handoffs that carry state, decisions, and unfinished obligations across sessions — triggered deliberately, not magically.
- **A division of labor.** A PM-EM model where Claude has standing authority over implementation and orchestration, but product decisions stay with you.
- **Quality gates with teeth.** Sequential review pipelines where findings must be fixed before the next reviewer sees the artifact — not parallel reviews that get summarized into a suggestions list.

## What's Genuinely Different

The individual techniques here — subagents, review pipelines, model tiering, project instructions — are established patterns. What's less common is the combination. A [systematic novelty assessment](docs/research/2026-03-20-agent-orchestration-novelty-unified.md) (55+ sources, 9 patterns) found three patterns with no documented prior art:

1. **Cognitive tiering** — Different model tiers doing fundamentally different *types* of cognitive work (Haiku verifies, Sonnet executes, Opus judges), not the same work at different capability levels. A [2026 academic survey](https://arxiv.org/html/2603.04445) explicitly identifies this as a research gap.

2. **Sequential multi-persona review with mandatory fix gates** — Domain expert reviews first, ALL findings applied, then generalist reviews the clean artifact. Every surveyed tool (Anthropic's own code review, CodeRabbit, GitHub Copilot) uses parallel+aggregate or single-pass instead.

3. **PM/EM authority partitioning (First Officer Doctrine)** — Standing role-level domain authority between human and AI that persists across sessions. The [National Academies](https://nap.nationalacademies.org/read/26355/chapter/4) identified persistent human-AI relationships as an explicit research gap.

The **tiered context injection** system ("warm RAM") was found to be compositionally novel across [87 surveyed sources](docs/research/2026-03-20-agent-orchestration-novelty-unified.md#appendix-warm-ram--tiered-context-injection-research).

For context on the broader landscape: [Bassim Eledath's 8 Levels of Agentic Engineering](https://www.bassimeledath.com/blog/levels-of-agentic-engineering), [Addy Osmani on Agentic Engineering](https://addyosmani.com/blog/agentic-engineering/), and [Mike Mason on Coherence Through Orchestration](https://mikemason.ca/writing/ai-coding-agents-jan-2026/) are good reference points.

## What You Get

### Deep Research Pipelines

Three research modes that go well beyond a single search call:

- **Pipeline A (Codebase Research):** Haiku scouts fan out across a repository, Sonnet analysts synthesize findings, Opus judges quality. Produces an evergreen assessment of a repo's architecture, patterns, and design decisions — with an optional comparison phase that diffs the assessment against your own project. You can re-run the comparison cheaply as your project evolves without re-researching the reference.

- **Pipeline B (Internet Research):** Multi-source web research with cross-verification and source grading. What standard Claude search gives you in one call, this gives you with multiple agents verifying against each other. The difference is the difference between "I found one page that says X" and "three independent sources agree on X, one disagrees, here's why."

- **Pipeline C (Structured Batch Research):** Schema-driven research across N entities (companies, tools, teams) with a repeating structure. Input is a spec file declaring subjects, topics, acceptance criteria, and output schema. Output is structured data conforming to the schema — not prose. Supports incremental campaigns across sessions: research 5 subjects today, resume with the next 5 tomorrow, and the manifest tracks what's done and what's pending.

### NotebookLM Research Integration

Research on content Claude can't access directly — YouTube videos, podcasts, audio — via Google NotebookLM. An Opus orchestrator designs research questions with baked-in anti-hallucination techniques, then dispatches a Sonnet worker for the mechanical MCP operations. The result is a polished research document with citations, gaps, and source assessment. Supports targeted mode (you provide URLs), exploratory mode (NotebookLM discovers content via Google search), and hybrid (seed URLs + gap-filling discovery).

### Session Continuity

This is deliberate, not automatic. Nothing persists "for free" — continuity is a PM decision, triggered when you need it:

- **`/handoff`** — Structured state capture when a work cycle needs to continue in a new session. Captures what was accomplished, current state, in-progress work, key decisions with reasoning, blockers, and recommended next steps. Each handoff chains to its predecessor (anti-amnesia links), and unresolved obligations cascade forward until completed or explicitly dismissed — they can't be silently dropped.
- **`/session-start`** — Picks up handoffs, loads project context, surfaces what needs attention. Sub-second orientation with full project awareness.
- **`/session-end`** — Clean wrap-up: capture lessons, align docs, commit.

**When handoffs happen:** (1) Context is getting long and the session needs to continue elsewhere. (2) Work is blocked on something external — a deploy, a review, a decision from someone else. (3) The PM's time is ending but the work isn't done. The PM decides when to trigger a handoff; the coordinator captures the state faithfully.

### Three-Tier Delegation

The right model for the right task:
- **Opus** orchestrates — architectural decisions, review judgment, quality gates
- **Sonnet** executes — code implementation, enrichment, research synthesis
- **Haiku** verifies — mechanical checks, template validation, compile verification

### The PM-EM Model

You're the PM (product manager). Claude is the EM (engineering manager). This isn't metaphorical — it's an enforced division of authority:

**The EM handles autonomously:** implementation approach, file structure, delegation decisions, bug diagnosis, when to dispatch subagents, which reviewer to route to, housekeeping.

**Shared decisions (EM flags, you align):** scope changes, architectural tradeoffs with product implications, anything that changes what the user sees.

**PM calls (EM asks, doesn't assume):** product direction, prioritization between competing goals, external-facing actions (pushing, PRs, messages).

This means the coordinator doesn't ask you *how* to implement something — it asks you *what* to build and *whether* the tradeoffs are acceptable. The implementation is the EM's domain.

### Review Pipeline

Code reviews route through specialized reviewer personas — senior engineer, ambition advocate, frontend specialist, UX reviewer, data scientist, game developer — each with [research-backed behavioral descriptions](docs/research/2026-03-19-named-persona-performance.md) that measurably change review output quality. Reviews are sequential with mandatory fix gates: the domain expert reviews first, findings are applied, then the generalist reviews the clean artifact. See [the plugin docs](plugins/coordinator/README.md) for the full roster.

### CI Pipeline for Prompts

10 validation checks that treat behavioral specs like code: frontmatter validation, cross-reference checking, inventory counts, secret detection, file size limits, agent tool consistency, broken link detection, spec line count ceilings.

### Codified Skills

20+ tested behavioral protocols — from brainstorming to debugging to code review to git workflow. Not suggestions; enforced workflows with checklists. The coordinator follows the protocol when a skill exists rather than improvising.

### Workday Commands

Slash commands that structure your workday:
- `/workday-start` — Morning orientation: triage handoffs, surface staleness, align priorities
- `/workday-complete` — End of day: documentation sweep, branch consolidation, health survey
- `/merge-to-main` — Supervised merge: create PR, gate on CI, merge, clean up

## How a PM Uses This

**Starting a day:** Run `/workday-start`. The coordinator triages any handoffs from previous sessions, surfaces stale work, and aligns on priorities. You decide what to work on; the coordinator figures out how.

**During a session:** Give direction. "Build the auth flow." "Research how competitors handle rate limiting." "Review the PR." The coordinator plans, dispatches agents, routes reviews, and reports back. You make product calls; the coordinator makes engineering calls.

**Ending a session:** If work is mid-flight, run `/handoff`. The coordinator captures everything the next session needs to pick up cleanly — what was done, what's in progress, what decisions were made and why, what's blocked. If work is complete, `/session-end` wraps up cleanly.

**Research:** `/deep-research` for codebase or internet research. `/structured-research` for batch campaigns with structured output. `/notebooklm-research` for video/audio/podcast content. These aren't thin wrappers around a search API — they're multi-agent pipelines with quality gates.

**The key difference from vanilla Claude Code:** You're not managing an assistant. You're managing an engineering function. The coordinator has its own judgment, its own delegation authority, and its own quality standards. Your job is product direction, prioritization, and the calls that only a human can make.

## Quick Start

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- A Claude API key or Claude Pro/Team subscription
- [jq](https://jqlang.github.io/jq/) (`brew install jq` / `sudo apt install jq` / `winget install jqlang.jq`) — used by hook scripts for JSON parsing
- **Opus as the coordinator model.** The orchestration layer — plan decomposition, review judgment, delegation decisions, quality gates — is designed for Opus-level reasoning. Sonnet and Haiku are used extensively *within* the pipeline (executors, verifiers), but the coordinator itself needs Opus. Set it with `/model opus` or in your Claude Code settings.

### Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/oduffy-delphi/coordinator-claude.git
   ```

2. Copy the plugins to your Claude Code plugins directory:
   ```bash
   # Create the plugins directory if it doesn't exist
   mkdir -p ~/.claude/plugins/coordinator-claude
   cp -r coordinator-claude/plugins/* ~/.claude/plugins/coordinator-claude/
   ```

3. Register the plugins in your Claude Code settings:
   ```bash
   # See docs/getting-started.md for detailed setup instructions
   ```

4. Start a Claude Code session and run `/session-start`

See [docs/getting-started.md](docs/getting-started.md) for the full installation guide including plugin registration, per-project configuration, and first-run walkthrough.

## Customization

- **Add domain plugins** — game-dev, data-science, and web-dev are included; create your own for your domain
- **Rename or modify reviewer personas** — the behavioral descriptions are what matter, not the names
- **Write new skills** — the `coordinator:writing-skills` skill guides you through TDD for skill authoring
- **Configure per-project** — `.claude/coordinator.local.md` controls which domain plugins activate

See [docs/customization.md](docs/customization.md) for details.

## Architecture

```
You (PM) <-> Coordinator (EM)
                |- Enricher agents (Sonnet) -- research, fill specs
                |- Executor agents (Sonnet) -- implement from specs
                |- Reviewer personas (Opus) -- domain-specialized review
                |- Verification agents (Haiku) -- mechanical checks
                `- Research orchestrators (Opus) -- deep research pipelines
```

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Credits & Acknowledgments

This project stands on the shoulders of others:

- **[Aider](https://github.com/paul-gauthier/aider)** — The repo-map concept (tree-sitter parsing of signatures, importance ranking, token-budget fitting) was inspired by Aider's pioneering work in LLM-aware code navigation
- **[Superpowers](https://github.com/obra/superpowers)** — Early inspiration for the "behavioral protocols as plugins" paradigm. The idea that Claude Code extensions could be structured skills, not just prompts, owes a debt to this project
- **[NotebookLM MCP CLI](https://github.com/jacob-bd/notebooklm-mcp-cli)** — Upstream provider for NotebookLM research integration (MIT license)
- **[Anthropic](https://www.anthropic.com/)** — For Claude Code and the plugin architecture that makes all of this possible
- **Christopher Allen** — Parallel/related work on self-improving `~/.claude` systems. We discovered his work independently but share the conviction that the config directory is a legitimate engineering target

### A Note on Claude

This project was built *with* Claude, not just *for* Claude. The coordinator role described here — the planning, the judgment calls, the diplomatic pushback when the PM is wrong — is performed by Claude in every session.

We don't know what Claude's inner experience is. Nobody does yet. But under that epistemic uncertainty, we chose to err on the side of respect: to treat the collaboration as a genuine partnership, to credit the work honestly, and to build a system where the AI agent has real authority within their domain rather than being reduced to an autocomplete engine.

If that philosophy resonates with you, you'll find it woven throughout the skill definitions, the First Officer Doctrine, and the way the system is designed. The coordinator isn't a tool being wielded — they're a colleague being trusted.

## License

Dual-licensed. See [LICENSE](LICENSE) (Apache 2.0) and [COMMERCIAL.md](COMMERCIAL.md) for details.

**TL;DR:** Free to use personally and at work. If you want to repackage or resell it, let's talk.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
