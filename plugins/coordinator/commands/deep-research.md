---
description: "Run a deep research pipeline on a repository (Pipeline A) or a topic across internet sources (Pipeline B). Use for studying codebases, building knowledge bases, evaluating libraries, or investigating multi-source technical topics with verified findings. For structured research with batch subjects and output schemas, use /structured-research instead."
allowed-tools: ["Agent", "Read", "Bash"]
argument-hint: "'repo' <repo-path> [--compare <project-path>] | 'web' <topic>"
---

# Deep Research — Dispatch

**Do NOT read the pipeline doc yourself. Dispatch the `deep-research-orchestrator` agent.**

## Step 1: Parse Arguments

`$ARGUMENTS` determines the pipeline:

- **`repo <path> [--compare <path>]`** → Pipeline A (repo research)
- **`web <topic>`** → Pipeline B (internet research)
- **Auto-detect:** if argument is a path that exists on disk → repo; otherwise → web

## Step 2: Announce

"I'm running `/deep-research` to [assess repo X / compare X against Y / research Z on the web]."

## Step 3: Dispatch Orchestrator

Dispatch a **`deep-research-orchestrator`** agent (`subagent_type: "coordinator:deep-research-orchestrator"`, `run_in_background: true`).

The dispatch prompt needs only:
- **Pipeline type:** A or B
- **Target:** repo path or research topic
- **Comparison path** (if Pipeline A with `--compare`)
- **Project context** (if Pipeline B): 2-3 sentences on what the project is, what we'll do with findings, what constraints matter
- **Output path** (optional): override the default `~/.claude/docs/research/` location
- **Research framing** (optional): if you've already discussed scope with the PM, include the research brief

The agent reads the pipeline doc and templates from disk. Do NOT paste them into the dispatch prompt.

## Step 4: Return Control

After dispatching, tell the PM:
"Deep research orchestrator dispatched. It will run [Haiku discovery → Sonnet verification → Opus synthesis / Haiku inventory → Sonnet analysis → Opus synthesis] autonomously. I'll present findings when it completes."

**Do NOT wait, poll, or drive phases from this context.** The orchestrator owns the pipeline end-to-end.
