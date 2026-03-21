# Deep Research Plugin

Multi-agent deep research pipelines for Claude Code. Two pipelines:

- **Pipeline A (Repo Research)** — study a repository's architecture via Haiku file mapping → Sonnet analysis → Opus synthesis
- **Pipeline B (Internet Research)** — investigate a topic across web sources via Agent Teams (Haiku scout + Sonnet specialists + Opus synthesizer)

## Prerequisites

### Agent Teams (required for Pipeline B)
Set in your `settings.json` under `env`:
```json
"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
```
Without this, `/deep-research web` will fail.

### Peer dependency: coordinator plugin (Pipeline A only)
Pipeline A references `coordinator:stuck-detection` for self-monitoring. If using Pipeline A without the coordinator plugin, remove the stuck-detection reference from `deep-research-orchestrator.md`. Pipeline B (Agent Teams) has no coordinator dependency.

## Commands

- `/deep-research repo <path>` — Pipeline A: repo assessment (relay pattern)
- `/deep-research web <topic>` — Pipeline B: internet research (Agent Teams, fire-and-forget)

## How It Works (Agent Teams)

1. EM scopes research, crafts search queries, asks PM for timing preferences (~2 min)
2. EM creates team, spawns 1 Haiku scout + 3-5 Sonnet specialists + 1 Opus synthesizer (~1 min)
3. EM is **free** — team works autonomously
4. **Scout** reads EM's search queries from scope.md, executes web searches, mechanically vets accessibility, writes shared source corpus (~2-3 min)
5. **Specialists** unblock when scout completes, read shared corpus, deep-read sources, cross-pollinate via messaging
6. Specialists self-govern convergence (floor + diminishing returns + ceiling)
7. Each specialist sends `DONE` message to synthesizer (wake-up signal — `blockedBy` is a status gate, not an event trigger)
8. **Synthesizer** verifies all tasks complete, reads specialist outputs, writes final document
9. EM receives notification → quick cleanup (archive, commit, present results)

## Maintenance Notes

- `pipelines/relay-protocol.md` is a snapshot from the coordinator plugin. If the coordinator's relay protocol evolves, review this copy for necessary changes.
