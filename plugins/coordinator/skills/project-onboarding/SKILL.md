---
name: project-onboarding
description: "Bootstrap a new project's tracking and coordination infrastructure — tracker, tasks directory, archive structure, handoff directory. Walks the EM through scaffolding with PM input for workstream definition. Use when starting a new project or when /update-docs reports missing tracker infrastructure."
---

# Project Onboarding

## When to Use

- Starting work in a new project repository for the first time
- `/update-docs` reports `tracker_missing` — the project lacks coordination infrastructure
- PM asks to set up project tracking in an existing repo

## Prerequisites

- You are in the project's working directory (not `~/.claude`)
- PM is available for workstream definition (Step 3 requires PM input)

## Steps

### Step 1: Survey Existing State

Before scaffolding, check what already exists. Do NOT overwrite existing files.

```
Check for:
├── docs/project-tracker.md          — if exists, skip to Step 5 (maintenance mode)
├── tasks/                           — may exist from prior sessions
│   └── lessons.md                   — may exist
├── archive/completed/               — may exist
├── .claude/                         — may exist (settings, handoffs)
│   └── handoffs/                    — may exist
└── CLAUDE.md                        — should exist (not created by this skill)
```

Report what exists and what needs to be created. If `docs/project-tracker.md` already exists, this skill becomes a health check — verify the format matches the standard template and flag deviations.

### Step 2: Scaffold Directory Structure

Create only what's missing. Use `mkdir -p` for directories, create files only if absent.

**Directories:**
- `docs/` — if missing
- `tasks/` — if missing
- `archive/completed/` — if missing
- `.claude/handoffs/` — if missing

**Files:**
- `tasks/lessons.md` — if missing, create with:
```markdown
# Lessons — [Project Name]

Engineering patterns worth internalizing. Bold title + 1-2 sentence rule. Max 3 lines per entry.

<!-- This file is maintained by the EM. See CLAUDE.md § Self-Improvement Loop for conventions. -->
```

**Do NOT create:**
- `CLAUDE.md` — project-specific, requires dedicated PM conversation
- `tasks/health-ledger.md` — created by `/architecture-audit`
- `.claude/orientation_cache.md` — created by `/workday-start` or `/update-docs`
- `.claude/settings.local.json` — machine-specific, gitignored

### Step 3: Define Workstreams (PM Conversation)

**This step requires PM input.** Present a prompt to the PM:

> I need to set up the project tracker. Workstream grouping is a PM call.
>
> **What are the 3-5 major workstreams for this project?** For each, I need:
> - A name (short, noun-phrase)
> - Current status: `Ready` | `Enrichment` | `Review` | `Executing` | `Blocked`
> - 2-5 immediate deliverables (checkbox items)
> - Any known dependencies or blockers
>
> I'll also add a Backlog section for items that are real but not imminent.

Wait for PM response before proceeding. Do not auto-generate workstreams — the PM defines what matters.

### Step 4: Create Project Tracker

Write `docs/project-tracker.md` using the standard format:

```markdown
# Project Tracker — [Project Name]
**Last updated:** YYYY-MM-DD
**Overall status:** [one-line summary]

## Active Workstreams

### 1. [Workstream Name]
**Status:** [status]
**Specs:** [path/to/spec.md] (if applicable)

- [ ] Deliverable description
- [ ] Another deliverable — **depends on:** [blocker]
- [ ] _PM: Non-engineering action item_

### 2. [Workstream Name]
...

## Backlog
- Future item — brief context

## Archive Pointer
→ Completed work: archive/completed/
→ Latest: archive/completed/YYYY-MM.md
```

**Conventions (from tracker-maintenance skill):**
- Max ~5 active workstreams
- Engineering items are detailed enough to orient an agent
- PM items are italic with `_PM:_` prefix — lightweight stubs
- Dependencies use `**depends on:**` or `**blocked by:**` inline
- Spec links use `**spec:**` inline
- Status values: `Ready` → `Enrichment` → `Review` → `Executing` → `Complete`

### Step 5: Verify and Report

Run a quick health check on what was created:

1. Confirm `docs/project-tracker.md` exists and parses correctly (has `## Active Workstreams` heading)
2. Confirm `tasks/lessons.md` exists
3. Confirm `archive/completed/` directory exists
4. Confirm `.claude/handoffs/` directory exists
5. If CLAUDE.md is missing, flag it: "NOTE: No CLAUDE.md found. Create one with project-specific principles before starting work."

Report: "Project onboarding complete. Created: [list]. Skipped (already existed): [list]. Next: run `/update-docs` to generate orientation cache."

## Notes

- This skill creates the **skeleton**. The tracker-maintenance skill (invoked by `/update-docs`) handles ongoing maintenance.
- The project tracker format is defined in the tracker-maintenance skill — this skill uses the same format for consistency.
- `.claude/` directory contents: `handoffs/` is tracked in git; `settings.local.json` should be in `.gitignore`.
