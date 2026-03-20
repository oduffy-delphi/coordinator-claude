# coordinator-claude

**A structured agent orchestration plugin for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — multi-agent workflows, named reviewer personas, and session continuity.**

A Claude Code plugin that mirrors a PM-EM dynamic: you're the PM (product manager), Claude is the EM (engineering manager). The coordinator dispatches work to specialized agents across Opus/Sonnet/Haiku tiers, routes code reviews to named personas, manages session continuity, and runs deep research pipelines — without being hamstrung by excessive guardrails or losing context across sessions.

> This isn't another "AI assistant" wrapper. It's an organizational model for human-AI collaboration — a bridge crew, not a chatbot. You set the heading; the coordinator makes it so.

**Quick install:**
```bash
git clone https://github.com/oduffy-delphi/coordinator-claude.git
cd coordinator-claude && bash setup/install.sh
```
Then start Claude Code and run `/session-start`. See [Getting Started](docs/getting-started.md) for detailed setup.

## Where This Sits in the Landscape

As of mid-2026, the individual techniques here — CLAUDE.md project instructions, specialized subagents, review pipelines, model tiering, persistent memory, plan-before-execute workflows — are all established patterns in the Claude Code ecosystem and the broader agentic engineering community.

What's less common is the specific combination. A [systematic novelty assessment](docs/research/2026-03-20-agent-orchestration-novelty-unified.md) (55+ sources, 9 patterns) found three patterns with no documented prior art:

1. **Cognitive tiering** — Different model tiers doing fundamentally different *types* of cognitive work (Haiku verifies, Sonnet executes, Opus judges), not the same work at different capability levels. A [2026 academic survey](https://arxiv.org/html/2603.04445) explicitly identifies this as a research gap.

2. **Sequential multi-persona review with mandatory fix gates** — Domain expert reviews first, ALL findings applied, then generalist reviews the clean artifact. Every surveyed tool (Anthropic's own code review, CodeRabbit, GitHub Copilot) uses parallel+aggregate or single-pass instead.

3. **PM/EM authority partitioning (First Officer Doctrine)** — Standing role-level domain authority between human and AI that persists across sessions. The [National Academies](https://nap.nationalacademies.org/read/26355/chapter/4) identified persistent human-AI relationships as an explicit research gap.

Three more patterns represent novel applications of known principles (character personas in engineering review, selective tool withholding, plugin-based capability composition), and the **tiered context injection** system ("warm RAM") was found to be compositionally novel across [87 surveyed sources](docs/research/2026-03-20-agent-orchestration-novelty-unified.md#appendix-warm-ram--tiered-context-injection-research).

Named reviewer personas work not because of the names, but because [rich behavioral descriptions genuinely steer model behavior](docs/research/2026-03-19-named-persona-performance.md) through training data cluster activation — confirmed causally by Anthropic's persona vectors research. The names are convenience handles for humans; the descriptions are the active ingredient.

For context on the broader landscape: [Bassim Eledath's 8 Levels of Agentic Engineering](https://www.bassimeledath.com/blog/levels-of-agentic-engineering), [Addy Osmani on Agentic Engineering](https://addyosmani.com/blog/agentic-engineering/), and [Mike Mason on Coherence Through Orchestration](https://mikemason.ca/writing/ai-coding-agents-jan-2026/) are good reference points.

## What You Get

### Named Reviewer Personas

Six specialized reviewers with distinct expertise and standards:
- **Patrik** — Senior engineer. Rigorous code review, architecture, documentation completeness
- **Zolí** — Ambition advocate. Challenges conservative recommendations ("should we be more ambitious?")
- **Sid** — Game developer. Unreal Engine systems, gameplay mechanics, Blueprint/C++
- **Palí** — Frontend specialist. Design tokens, component patterns, CSS architecture
- **Fru** — UX reviewer. Trust signals, user flow clarity, interface intuition
- **Camelia** — Data scientist. ML, statistics, data modeling, LLM workflows

These aren't just labels — each persona has [research-backed behavioral descriptions](docs/research/2026-03-19-named-persona-performance.md) that measurably change review output quality. The names are stable pointers for human calibration; the descriptions are the active ingredient.

### Deep Research Pipeline

Three research modes, all multi-agent with quality gates:
- **Pipeline A (Codebase):** Haiku scouts fan out across a repository, Sonnet analysts synthesize findings, Opus judges quality
- **Pipeline B (Internet):** Multi-source web research with cross-verification and source grading
- **Pipeline C (Structured Batch):** Schema-driven research across N entities (companies, tools, teams) with repeating structure

Fast, cheap, and high-quality. What would take a human researcher hours runs in minutes.

### Three-Tier Delegation

The right model for the right task:
- **Opus** orchestrates — architectural decisions, review judgment, quality gates
- **Sonnet** executes — code implementation, enrichment, research synthesis
- **Haiku** verifies — mechanical checks, template validation, compile verification

### Session Continuity

Never lose context:
- **Handoffs** — structured state capture between sessions
- **Orientation cache** — sub-second session start with full project awareness
- **Memory system** — persistent knowledge across conversations
- **Project trackers** — workstream-level progress tracking with archive conventions

### CI Pipeline for Prompts

10 validation checks that treat behavioral specs like code:
- Frontmatter validation, cross-reference checking, inventory counts
- Secret detection, file size limits, agent tool consistency
- Broken link detection, spec line count ceilings

### Session Lifecycle Commands

Slash commands that structure your workday:
- `/session-start` — Orient a new session: load context, check handoffs, surface what needs attention
- `/session-end` — Wrap up cleanly: capture lessons, align docs, commit
- `/handoff` — Save session state so the next session picks up where you left off
- `/workday-start` — Morning orientation: triage handoffs, surface staleness, align priorities
- `/workday-complete` — End of day: documentation sweep, branch consolidation, health survey
- `/merge-to-main` — Supervised merge: create PR, gate on CI, merge, clean up

These aren't ceremonial — they're the connective tissue that makes multi-session work feel continuous rather than amnesiac.

### 20+ Codified Skills

From brainstorming to debugging to code review to git workflow — tested behavioral protocols that shape how the coordinator approaches work. Not suggestions; enforced workflows. The coordinator doesn't improvise when a skill exists — they follow the checklist, like any good officer would.

## The EM Model (and Its Honest Limits)

The coordinator's primary mode is **engineering manager**: they plan work, dispatch agents, route reviews, verify output, and manage state. The PM sets the course; the coordinator runs the ship.

In practice, the coordinator *can* and sometimes *does* write code directly — particularly when dispatching an executor would spend more tokens and time than just handling it in context. This is a pragmatic tradeoff, not a hard architectural boundary. The system is designed to *encourage* delegation (and the coordinator will dispatch mechanical tasks to executors more often than not), but it isn't *enforced* — because the only way to make delegation deterministic would be to hamstring the coordinator, and we'd rather have a capable agent who occasionally does too much themselves than a restricted one who can't act when action is the right call.

If you want stricter separation, you can tighten the instructions in your CLAUDE.md. We chose the flexible version.

## Quick Start

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- A Claude API key or Claude Pro/Team subscription
- **Opus as the coordinator model.** The orchestration layer — plan decomposition, review judgment, delegation decisions, quality gates — is designed for Opus-level reasoning. Substituting Sonnet or below for the coordinator is a [tribble problem](https://en.wikipedia.org/wiki/The_Trouble_with_Tribbles): it'll look like it's working until the tribbles are everywhere. Each individual judgment call degrades subtly — wrong delegation, shallow review, missed quality gates — and they compound. Sonnet and Haiku are used extensively *within* the pipeline (executors, verifiers), but the coordinator itself needs Opus. Set it with `/model opus` or in your Claude Code settings.

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

- **Rename personas** — or keep them. The behavioral descriptions are what matter, not the names
- **Add domain plugins** — game-dev is included as an example; create your own for your domain
- **Write new skills** — the `coordinator:writing-skills` skill guides you through TDD for skill authoring
- **Configure per-project** — `.claude/coordinator.local.md` controls which domain plugins activate

See [docs/customization.md](docs/customization.md) for details.

## Architecture

```
You (PM) <-> Coordinator (EM)
                |- Enricher agents (Sonnet) -- research, fill specs
                |- Executor agents (Sonnet) -- implement from specs
                |- Reviewer personas (Opus) -- Patrik, Camelia, Sid, Palí, Fru
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
