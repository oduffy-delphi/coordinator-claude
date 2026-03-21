# Deep Research Plugin

Multi-agent deep research pipelines for Claude Code. Both pipelines use Agent Teams (fire-and-forget):

- **Pipeline A (Internet Research)** — investigate a topic across web sources via 1 Haiku scout (source corpus) + 3-5 Sonnet specialists (deep-read + verify) + 1 Opus synthesizer
- **Pipeline B (Repo Research)** — study a repository's architecture via 2 Haiku scouts (file inventory) → 4 Sonnet specialists (analysis + optional comparison) → 1 Opus synthesizer

## Prerequisites

### Agent Teams (required for both pipelines)
Set in your `settings.json` under `env`:
```json
"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
```
Without this, `/deep-research` will fail.

## Commands

- `/deep-research web <topic>` — Pipeline A: internet research
- `/deep-research repo <path> [--compare <project-path>]` — Pipeline B: repo assessment (+ optional comparison)

## How It Works

Both pipelines follow the same Agent Teams pattern:

1. **EM scopes** — defines chunks/topics, estimates sizes, asks PM for timing (~2 min)
2. **EM creates team** and spawns all teammates in parallel (~1 min)
3. **EM is freed** — team works autonomously
4. **Haiku scouts** build shared artifacts (file inventories for repo, source corpus for web)
5. **Sonnet specialists** unblock, deep-read, cross-pollinate via messaging, self-govern timing
6. Each specialist sends `DONE` message to synthesizer (`blockedBy` is a status gate, not an event trigger)
7. **Opus synthesizer** reads specialist outputs, cross-references, writes final document(s)
8. EM receives notification → cleanup (archive, commit, present results)

### Pipeline A specifics
- 1 Haiku scout — builds shared source corpus from web searches
- Specialists verify claims, resolve contradictions, enforce source recency
- Team protocol: `pipelines/team-protocol.md`

### Pipeline B specifics
- 2 Haiku scouts (2 chunks each) — produces structured file inventories with function signatures, constants, data flow
- In `--compare` mode: scouts also identify equivalent project files; specialists produce both assessment and comparison artifacts; synthesizer produces ASSESSMENT.md + GAP-ANALYSIS.md
- Team protocol: `pipelines/repo-team-protocol.md`
