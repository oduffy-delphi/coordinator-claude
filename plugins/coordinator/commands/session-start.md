---
description: Orient session — preflight, load context, choose work
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
argument-hint: "[task-description]"
---

# Session Start — Preflight and Orientation

Orient this agent by verifying the environment, loading project context, and choosing work.

**Design note:** Multiple agents may be running concurrently on the same repo. This command orients ONE agent — it does not assume exclusive access to the codebase or the user's attention.

---

## Preflight

Safety and environment checks. Order matters — each depends on the one before it.

### Model check

Check whether you are running on **Opus**. Your model ID is stated in the system prompt (e.g., "You are powered by the model named Opus 4.6").

- **If on Opus:** Continue silently.
- **If NOT on Opus:** Alert the user:

  _"Heads up — this session is running on {model name}, not Opus. `/session-start` signals complex work that benefits from Opus-level reasoning. Run `/model opus` to switch, or say 'continue' if this is intentional."_

  **Wait for the user's response** before continuing.

### Safety commit

Secure any uncommitted work before touching branches:

1. Run `git status` — if there are ANY uncommitted changes (staged, unstaged, or untracked), commit immediately:
   ```
   git add -A && git commit -m "session-start safety commit"
   ```
2. This is crash insurance. If a previous session died mid-work, this captures its state. The auto-push hook will push to the remote.
3. If nothing to commit, move on silently.

**Do not ask permission.** Non-negotiable safety measure.

### Branch detection

Get on the right branch:

1. **Push health check:** Run `git log origin/$(git branch --show-current)..HEAD 2>/dev/null`.
   If unpushed commits exist, warn: _"Found N unpushed commits — auto-push may have failed. Check .git/push-failures.log."_

2. **If already on a non-main branch:** Report the branch name and continue. Don't switch.
   _"Resuming work on {branch} ({N} commits ahead of main)."_

3. **If on main:** Look for today's work branch to resume:
   - Check local: `git branch --list 'work/{machine}/*'`
   - Check remote: `git branch -r --list 'origin/work/{machine}/*'`
   - Cross-reference with any loaded handoff's `Branch:` field.

   If a branch exists for today (not yet merged):
   _"Found existing branch work/{machine}/{date}. Resuming."_
   `git checkout {branch}`

   If no branch for today (or today's was already merged):
   Create: `git checkout -b work/{machine}/{date}`
   If name collision: append suffix: `work/{machine}/{date}-2`

### Branch staleness

Check how long the branch has diverged from `main`:

1. Find the merge base: `git merge-base HEAD origin/main`
2. Get the date of that commit: `git log -1 --format=%ci <merge-base-hash>`
3. Calculate the age in days.

**If diverged more than 2 days:**

_"This branch has been diverged from main for {N} days (since {date}). Long-lived branches accumulate merge risk. I'd recommend merging before new work — want me to run `/merge-to-main`?"_

**Wait for the user's response.** Do not proceed until the user approves or declines.

**If 2 days or fewer:** Continue silently.

---

## Context Load

Load project state into context. These checks are independent of each other.

### Lessons

Read `tasks/lessons.md` (if it exists) — learned patterns from past corrections. Review every entry.

Note: Project `CLAUDE.md` and global `~/.claude/CLAUDE.md` are already in system context — don't re-read them.

**After reading, acknowledge what you loaded:**
- Number of lessons (if any)
- Confirm fix-forward and verification-before-done discipline is active

### Handoffs

**IMPORTANT:** Handoffs are NEVER auto-loaded. Selection triggers loading only — handoffs are NOT archived on read.

Check `.claude/handoffs/` for `.md` files (active handoffs). If handoffs exist:

1. List each file in chronological order (filenames include timestamp: `YYYY-MM-DD_HHMMSS_sessionid.md`) with its date/time and first heading
2. Ask the user which handoff(s) to load — or "None" to start fresh
3. For each **selected** handoff: **Read the full file** into context. Do NOT archive it.
4. **All handoffs remain in `.claude/handoffs/`** — selected or not. A handoff describes work that may span multiple sessions. Archiving on read caused incomplete work to lose its handoff context in subsequent sessions.

**Archiving is handled by `/update-docs` only** (48-hour threshold). This ensures handoffs persist until the work they describe has had time to complete.

**Path convention:** Active handoffs in `.claude/handoffs/`, archived in `archive/handoffs/`. Both git-tracked.

**If `.claude/` is gitignored:** Warn the user — this breaks handoff discovery. `.claude/` should be tracked; only `.claude/settings.local.json` should be ignored.

### Action items and roadmap

**Conditional on workday-start:** If `tasks/.workday-start-marker` contains today's date, skip this section — workday-start already reviewed these. If no marker or stale marker, read them as a graceful fallback.

These are operational documents — they tell the EM what's immediately actionable and where the project is headed.

Read each if it exists (first match wins per row), skip silently if not:

| Document | Convention Paths |
|----------|-----------------|
| Action Items | `ACTION-ITEMS.md`, `docs/active/ACTION-ITEMS.md`, `docs/ACTION-ITEMS.md` |
| Roadmap | `ROADMAP.md`, `docs/roadmap.md`, `docs/ROADMAP.md` |

No summary needed — just load them into context. Their content speaks for itself.

### Project tracker

**Conditional on workday-start:** If `tasks/.workday-start-marker` contains today's date, skip this section — workday-start already reviewed the tracker. If no marker or stale marker, read as a graceful fallback.

Read `docs/project-tracker.md` (if it exists). This is the strategic tracker that `/update-docs` maintains — active workstreams, their statuses, dependencies, and blockers.

**If it exists:** Surface a brief summary:
```
## Project State
- Active workstreams: [N] — [list names with statuses]
- Blocked items: [N] — [brief description of blockers]
- Ready for execution: [list any items with status Ready/Executing]
```

This gives the EM visibility into what the project is working on before choosing work in the Engage section. The tracker also informs the work menu — surface tracker items as concrete options alongside the generic categories.

**If it doesn't exist:** Skip silently.

### Orientation check

Check whether `/workday-start` ran today:

1. Read `tasks/.workday-start-marker` — if it contains today's date, workday-start already ran.
2. **If workday-start ran today:** Skip health surface and doc gap check entirely. The morning briefing covered it.
   - If `.claude/orientation_cache.md` exists: **Read it.** Report: _"Using orientation cache from today's workday-start."_ Use its health snapshot data for health context and its repo structure summary for orientation — do not re-read individual health files.
   - If `.claude/orientation_cache.md` does not exist: Note that workday-start ran but left no cache (unusual — may have been interrupted).
3. **If workday-start did NOT run today (or marker missing):**
   - Read `tasks/health-summary.md` (if it exists) — latest daily code health findings from `/code-health`
   - Read `tasks/health-ledger.md` (if it exists) — running health trend log
   - _"No workday-start today. Loaded available health files for context — run `/workday-start` for full orientation."_
   - Skip doc gap checks — they're daily concerns, not per-session.

---

## Engage

Choose work and load task-specific context.

### Work selection

**CRITICAL — Handoff loaded?** Check whether a handoff was loaded in the Context Load section (or provided by the user at any point). Track this as a mental flag: `HANDOFF_LOADED=true`. If YES:

> **The handoff IS the work order.** Do NOT present a menu. Do NOT ask "what should this agent work on?" Do NOT list the handoff's action items and wait for the user to pick one. Do NOT ask "want me to proceed?"
>
> Instead: read any files the handoff references that aren't yet in context, then **immediately begin executing the first action item.** You're the next relay runner — the baton has been passed. Pick it up and run.
>
> If the handoff lists multiple next steps, execute them in order unless the PM redirects.

**If NO handoff was loaded** (user chose "None" or no handoffs exist), present options appropriate to the project:

**What should this agent work on?**

1. **Implementing a feature** — From plan docs or feature specs
2. **Fixing a bug** — From issue tracker, bug report, or failing tests
3. **Reviewing code** — Code review of recent changes
4. **Research / exploration** — No ceremony, just start
5. **Maintenance** — Daily health check, weekly audit, or debt triage
6. **Other** — Something else (describe it)

If `$ARGUMENTS` is provided, use it to identify the task directly and skip the menu.

**Adapt this menu to the project:** If the project tracker was loaded, surface its ready/executing items as concrete options. If project-specific plan docs or priority lists exist (check `docs/`, `tasks/`, `.claude/plans/`), surface those too. The menu should reflect what's actually available, not just generic categories.

### Load task context

**If continuing from a handoff:** Read any files the handoff references that aren't yet in context, then begin the first action item.

**If from the menu:** Based on the user's choice:

- **Implementing:** Find and read the relevant plan doc. Summarize the first implementation step.
- **Fixing a bug:** Identify the failing test, error, or reproduction steps. Read the relevant source.
- **Reviewing:** Identify what to review (recent commits, specific files, PR). Load review criteria.
- **Research:** Ask what to explore. No additional prep needed.
- **Other:** Ask the user to describe the task. Load relevant context.

### Status report

Briefly report:
- **Repo state:** `git status` summary — note that uncommitted changes may belong to other concurrent agents
- **Branch:** Current branch name

Keep this to 2 lines. This is orientation, not ownership.
