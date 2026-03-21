---
description: "Run a deep research pipeline on a topic across internet sources (Pipeline A) or a repository (Pipeline B). Use for studying codebases, building knowledge bases, evaluating libraries, or investigating multi-source technical topics with verified findings. For structured research with batch subjects and output schemas, use /structured-research instead."
allowed-tools: ["Read", "Bash"]
argument-hint: "'repo' <repo-path> [--compare <project-path>] | 'web' <topic>"
---

# Deep Research — Router

This command routes to the appropriate pipeline-specific driver.

## Step 1: Parse Arguments

`$ARGUMENTS` determines the pipeline:

- **`web <topic>`** — Pipeline A (internet research, Agent Teams)
- **`repo <path> [--compare <path>]`** — Pipeline B (repo research, Agent Teams)
- **Auto-detect:** if the first argument is a path that exists on disk → repo; otherwise → web

## Step 2: Route

Use the Skill tool to invoke the appropriate sub-command, passing through all arguments:

- **Pipeline A:** `skill: "deep-research:deep-research-web", args: "<remaining arguments>"`
- **Pipeline B:** `skill: "deep-research:deep-research-repo", args: "<remaining arguments>"`

That's it. The driver handles everything from here.
