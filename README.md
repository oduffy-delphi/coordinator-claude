# coordinator-claude

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![Opus](https://img.shields.io/badge/Model-Opus_4.6-orange)](https://www.anthropic.com/claude)
[![Plugins](https://img.shields.io/badge/Plugins-6-green)](#what-you-get)
[![Skills](https://img.shields.io/badge/Skills-22-green)](#codified-skills)
[![Agent Teams](https://img.shields.io/badge/Agent_Teams-3_pipelines-blueviolet)](#deep-research-pipelines)
[![CI](https://img.shields.io/badge/CI-10_checks-brightgreen)](.github/workflows/validate-plugins.yml)

**A Claude Code plugin system that turns human-AI collaboration into a structured PM-EM partnership — with research pipelines, multi-session continuity, and quality gates that go beyond what's available out of the box.**

> This isn't another "AI assistant" wrapper. It's an organizational model for working with Claude Code at scale — across sessions, across domains, across days. You set the heading; the coordinator makes it so.

---

**Contents:** [Why This Exists](#why-this-exists) · [What's Distinctive Here](#whats-distinctive-here) · [What You Get](#what-you-get) · [How a PM Uses This](#how-a-pm-uses-this) · [Quick Start](#quick-start) · [Customization](#customization) · [Architecture](#architecture) · [Credits](#credits--acknowledgments) · [License](#license)

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

## What's Distinctive Here

The building blocks in this repo are not inventions. Claude Code already supports plugins, hooks, subagents, and agent teams, and other agent frameworks already use role-specialized multi-agent workflows. What this repo adds is a more opinionated operating model on top of those primitives: structured delegation, explicit review stages, session continuity conventions, and a PM/EM collaboration frame for human-AI work.

The main differentiator is not a new category of agent architecture. It is the combination of existing patterns into a practical workflow for Claude Code: specialized workers, staged review, startup context injection, and research-oriented team coordination. Claude Code's own docs now describe agent teams as appropriate for parallel research, review, debugging, and cross-layer coordination, with teammates communicating directly through a shared task list.

### Patterns We Emphasize

1. **Role-specialized model use.** We assign different Claude models to different workflow roles, such as orchestration, execution, and verification. This follows established multi-agent specialization patterns rather than claiming a new architectural category. Claude Code supports subagents with separate context windows, tool access, and permissions, which makes this style practical.

2. **Staged review rather than one-pass review.** We prefer a workflow where specialist review happens before a generalist pass, instead of aggregating everything into a single review step. That is a process choice, not a claim of invention. GitHub's own Copilot code review now describes an agentic review architecture, which shows the broader direction of travel across coding tools.

3. **A PM/EM collaboration frame.** We use a simple rule of thumb: the human owns product direction and external decisions, while the agent owns implementation orchestration and technical delegation. The [human-AI teaming literature](https://nap.nationalacademies.org/read/26355/chapter/4) already treats role allocation, dynamic function allocation, and differentiated authority as core issues, so this should be read as an operational framing rather than a novel research concept.

4. **Research-oriented team workflows.** Our research pipelines lean on Claude Code agent teams for parallel exploration, shared task coordination, and teammate-to-teammate communication. That capability is now documented by Anthropic, so the claim here is about our pipeline design, not about inventing autonomous research swarms.

5. **Session-orientation conventions.** We use startup hooks, handoffs, and cached context artifacts to reduce cold starts and make long-running work easier to resume. Claude Code's hooks system supports SessionStart, UserPromptSubmit, SubagentStop, PreCompact, PostCompact, and SessionEnd, which makes this kind of workflow feasible.

We do not claim that the core concepts here are unprecedented. The contribution is in the integration: packaging current Claude Code capabilities and established multi-agent patterns into a disciplined workflow system that is easier to run repeatedly across sessions and projects.

For context on the broader landscape: [Bassim Eledath's 8 Levels of Agentic Engineering](https://www.bassimeledath.com/blog/levels-of-agentic-engineering), [Addy Osmani on Agentic Engineering](https://addyosmani.com/blog/agentic-engineering/), and [Mike Mason on Coherence Through Orchestration](https://mikemason.ca/writing/ai-coding-agents-jan-2026/) are good reference points.

For the full picture — the ecosystem survey, the [novelty assessment](docs/research/2026-03-20-agent-orchestration-novelty-unified.md), and the real constraints — see **[State of the Meta](docs/research/STATE-OF-THE-META.md)**.

## What You Get

### Deep Research Pipelines

Three research modes that go well beyond a single search call — built on Claude Code's **Agent Teams** (experimental), where teammates collaborate autonomously via messaging and shared tasks:

- **Pipeline A (Internet Research):** 1 Haiku scout builds a shared source corpus from EM-crafted search queries → 3-5 Sonnet specialists deep-read, verify claims, and cross-pollinate findings via peer messaging → 1 Opus synthesizer resolves contradictions, writes the final document, and optionally writes a **Synthesizer Advisory** with staff-engineer observations beyond the research scope. Specialists self-govern their timing (floor/ceiling/diminishing-returns) with no EM monitoring.

- **Pipeline B (Repo Research):** 2 Haiku scouts build structured file inventories (function signatures, constant values, cross-subsystem data flow) → 4 Sonnet specialists deep-read source files, analyze architecture and patterns, and cross-pollinate findings in real time via peer messaging → 1 Opus synthesizer cross-references all specialist assessments into a final document with file:line references and confidence levels. Optional `--compare` mode adds a gap analysis against your own project. The entire team runs as an Agent Teams swarm — the EM scopes the repo into 4 domain-aligned chunks, spawns 7 teammates, and is freed; the team handles everything autonomously including convergence timing and cross-chunk discovery.

- **Pipeline C (Structured Research):** Schema-driven research across N entities with repeating structure, now powered by Agent Teams. A Haiku scout maps web findings to schema fields from an EM-processed brief → 1-5 Sonnet verifiers compare against existing data and produce schema field tables with change types (CONFIRMED/UPDATED/NEW/REFUTED) → an Opus synthesizer reconciles cross-topic conflicts and writes YAML/JSON conforming to the spec's output schema. Quality gates from the spec are embedded in verifier prompts for self-validation. Supports incremental campaigns across sessions via manifest tracking.

<details>
<summary><strong>Agent Teams architecture details</strong></summary>

All three research pipelines use Claude Code's experimental [Agent Teams](https://docs.anthropic.com/en/docs/claude-code) feature — a fire-and-forget pattern where the EM creates a team, spawns all teammates in parallel, and is immediately freed. The team self-coordinates:

- **Three-tier team composition:** Haiku scouts (fast mechanical work — file inventories, web searches, accessibility vetting), Sonnet specialists (analytical work — deep reading, verification, cross-pollination), Opus synthesizer (judgment — contradiction resolution, prioritized recommendations, optional advisory). Each model does what it's best at.
- **Shared artifacts over broadcast:** Scouts write to disk (file inventories, source corpora); specialists read from disk. This avoids the message explosion of N×N communication and lets specialists start from curated input rather than raw search results.
- **Task-gated blocking:** Specialists are `blockedBy` the scout task — they auto-start when the scout completes. The synthesizer is `blockedBy` all specialist tasks, but since it's already running and idle, specialists send explicit `DONE` messages as wake-up signals (`blockedBy` is a [status gate, not an event trigger](plugins/deep-research/pipelines/team-protocol.md#how-agent-teams-blocking-actually-works-empirical--sourced)).
- **Self-governing timing:** Specialists manage their own convergence using a floor (minimum research time + source count), ceiling (maximum time), and diminishing-returns detector (last 3 sources added nothing new). No EM monitoring or WRAP_UP broadcast needed.
- **7-teammate ceiling:** Agent Teams supports up to 7 parallel teammates. Team compositions are designed around this constraint (e.g., Pipeline B: 2 scouts + 4 specialists + 1 synthesizer = 7 exactly).

</details>

### NotebookLM Research Integration

Research on content Claude can't access directly — YouTube videos, podcasts, audio — via Google NotebookLM. An Opus orchestrator designs research questions with baked-in anti-hallucination techniques, then dispatches a Sonnet worker for the mechanical MCP operations. The result is a polished research document with citations, gaps, and source assessment. Supports targeted mode (you provide URLs), exploratory mode (NotebookLM discovers content via Google search), and hybrid (seed URLs + gap-filling discovery).

### Session Continuity

This is deliberate, not automatic. Nothing persists "for free" — continuity is a PM decision, triggered when you need it:

- **`/handoff`** — Structured state capture when a work cycle needs to continue in a new session. Captures what was accomplished, current state, in-progress work, key decisions with reasoning, blockers, and recommended next steps. Each handoff chains to its predecessor (anti-amnesia links), and unresolved obligations cascade forward until completed or explicitly dismissed — they can't be silently dropped.
- **`/session-start`** — Picks up handoffs, loads project context, surfaces what needs attention. Sub-second orientation with full project awareness.
- **`/session-end`** — Clean wrap-up: capture lessons, align docs, commit.
- **Context pressure advisory** — A `UserPromptSubmit` hook that reads the session transcript file on every prompt, estimates context usage as a percentage of the model's window, and emits warnings at two thresholds: advisory (~60% — "start thinking about handoff") and critical (~78% — "compaction is imminent, handoff now"). A companion `PreCompact` hook writes a sentinel file that the advisory hook detects on the next prompt, triggering post-compaction orientation guidance. Both hooks are model-aware (Opus 1M, Sonnet/Haiku 200K), bark-once per threshold (no repeated nagging), and fail-open if the transcript is missing. The result: the coordinator proactively manages its own continuity rather than waiting for the PM to notice context degradation.

**When handoffs happen:** (1) The context pressure hook recommends it — the system is tracking its own cognitive runway. (2) Work is blocked on something external — a deploy, a review, a decision from someone else. (3) The PM's time is ending but the work isn't done. The PM decides when to trigger a handoff; the coordinator captures the state faithfully.

**Evidence-based prompt engineering.** The pipeline templates were refined by [studying leading open-source deep research implementations](docs/research/2026-03-21-deep-research-prompt-improvements.md) — including [dzhng/deep-research](https://github.com/dzhng/deep-research) and LangChain's [open_deep_research](https://github.com/langchain-ai/open_deep_research) — and implementing five improvements that neither repo has:

1. **Adversarial search** — Every research run must include at least one search targeting criticism, limitations, and opposing views. Prevents echo chambers and premature convergence.
2. **Cross-pollination** — Findings from one topic area inform other topics' deep-read phases. Multi-hop reasoning without additional agent dispatches.
3. **Citation-first synthesis** — "According to [Source], [claim]" rather than "[Claim] ([Source])." Every assertion is visibly traceable; unsourced claims are immediately obvious.
4. **Source recency enforcement** — Sources older than 12 months are flagged; fast-moving topics use a 6-month threshold. Stale-only findings are explicitly marked.
5. **Structured claim tables** — Complex topics produce intermediate claims tables (claim, source, date, confidence, corroboration) for more rigorous synthesis.

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

22 tested behavioral protocols — from brainstorming to debugging to code review to git workflow. Not suggestions; enforced workflows with checklists. The coordinator follows the protocol when a skill exists rather than improvising.

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
- **Agent Teams (experimental)** — Required for the deep research pipelines. Enable by adding `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` to your `env` in Claude Code's `settings.json`. Without this, `/deep-research` commands will fail.
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

- **Add domain plugins** — game-dev, data-science, web-dev, and deep-research are included; create your own for your domain
- **Rename or modify reviewer personas** — the behavioral descriptions are what matter, not the names
- **Write new skills** — the `coordinator:writing-skills` skill guides you through TDD for skill authoring
- **Configure per-project** — `.claude/coordinator.local.md` controls which domain plugins activate

See [docs/customization.md](docs/customization.md) for details.

## Architecture

```
You (PM) <-> Coordinator (EM)
                |- Enricher agents (Sonnet) ── research, fill specs
                |- Executor agents (Sonnet) ── implement from specs
                |- Reviewer personas (Opus) ── domain-specialized review
                |- Verification agents (Haiku) ── mechanical checks
                `- Deep Research (Agent Teams) ── fire-and-forget autonomous swarms
                     |- Pipeline A: 1 Haiku scout → 3-5 Sonnet specialists → 1 Opus synthesizer
                     |- Pipeline B: 2 Haiku scouts → 4 Sonnet specialists → 1 Opus synthesizer
                     `- Pipeline C: 1 Haiku scout → 1-5 Sonnet verifiers → 1 Opus synthesizer
```

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Credits & Acknowledgments

This project stands on the shoulders of others:

- **[Aider](https://github.com/paul-gauthier/aider)** — The repo-map concept (tree-sitter parsing of signatures, importance ranking, token-budget fitting) was inspired by Aider's pioneering work in LLM-aware code navigation
- **[Superpowers](https://github.com/obra/superpowers)** — Early inspiration for the "behavioral protocols as plugins" paradigm. The idea that Claude Code extensions could be structured skills, not just prompts, owes a debt to this project
- **[NotebookLM MCP CLI](https://github.com/jacob-bd/notebooklm-mcp-cli)** — Upstream provider for NotebookLM research integration (MIT license)
- **[Anthropic](https://www.anthropic.com/)** — For Claude Code and the plugin architecture that makes all of this possible
- **[dzhng/deep-research](https://github.com/dzhng/deep-research)** — Minimal recursive deep research implementation. Its `researchGoal` intent carrier pattern (each search query carries forward-looking reasoning about what to do with results) inspired our research intent tracking in Pipeline B. Zod-schema-at-every-step approach validated our commitment to structured output throughout
- **[open_deep_research](https://github.com/langchain-ai/open_deep_research)** — LangChain's production deep research system. Its two-stage compression pipeline (raw notes → lossless citation-preserving compression → final synthesis) informed our citation preservation approach. The `think_tool` forced-reflection pattern inspired our Phase 2 reflection instructions
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
