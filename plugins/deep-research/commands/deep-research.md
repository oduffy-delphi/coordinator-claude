---
description: "Run a deep research pipeline on a repository (Pipeline A) or a topic across internet sources (Pipeline B). Use for studying codebases, building knowledge bases, evaluating libraries, or investigating multi-source technical topics with verified findings. For structured research with batch subjects and output schemas, use /structured-research instead."
allowed-tools: ["Read", "Bash"]
argument-hint: "'repo' <repo-path> [--compare <project-path>] | 'web' <topic>"
---

# Deep Research — Router

This command routes to the appropriate pipeline-specific driver.

## Step 1: Parse Arguments

`$ARGUMENTS` determines the pipeline:

- **`repo <path> [--compare <path>]`** — Pipeline A (repo research)
- **`web <topic>`** — Pipeline B (internet research, Agent Teams)
- **Auto-detect:** if the first argument is a path that exists on disk → repo; otherwise → web

## Step 2: Route

Use the Skill tool to invoke the appropriate sub-command, passing through all arguments:

- **Pipeline A:** `skill: "deep-research:deep-research-repo", args: "<remaining arguments>"`
- **Pipeline B:** `skill: "deep-research:deep-research-web", args: "<remaining arguments>"`

That's it. The driver handles everything from here.
