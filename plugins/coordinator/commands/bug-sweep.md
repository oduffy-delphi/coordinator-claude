---
description: Systematic codebase bug hunt — find and fix all AI-fixable bugs in-session, defer blocked ones to backlog
allowed-tools: ["Read", "Edit", "Write", "Bash", "Grep", "Glob", "Agent"]
argument-hint: "[path]"
---

# Bug Sweep — Systematic Codebase Bug Hunt

Detect stack, grep for mechanical patterns, dispatch parallel Sonnet agents for semantic analysis and test suite execution, triage findings, fix all AI-fixable bugs via executor agents, and defer genuinely blocked items to `tasks/bug-backlog.md`. Uses `pipelines/bug-sweep/PIPELINE.md` as the pipeline definition.

**Announce at start:** "I'm running `/bug-sweep` — systematic bug hunt across the codebase."

**Reference:** Full pipeline design and pattern library in `plugins/coordinator/pipelines/bug-sweep/PIPELINE.md`.

## Arguments

`$ARGUMENTS` is an optional path to scope the sweep. If provided, all chunk definitions and grep searches are constrained to that path. If omitted, the full codebase is scanned.

Examples:
- `/bug-sweep` — full codebase sweep
- `/bug-sweep src/` — scope to the `src/` directory
- `/bug-sweep src/pipeline/` — scope to a specific subsystem

---

## Phase 0: Scope and Pattern Selection (Coordinator, ~5 min)

1. **Detect project stack** — run bash to scan for language files, test frameworks, and build configs:
   ```bash
   find ${SCOPE:-.} -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.cpp" -o -name "*.h" | head -20
   ls -d tests/ __tests__/ spec/ test/ 2>/dev/null
   ls pytest.ini pyproject.toml jest.config.* tsconfig.json CMakeLists.txt 2>/dev/null
   ```
   If `$ARGUMENTS` is provided, set `SCOPE=$ARGUMENTS` in the scan. Otherwise `SCOPE=.`.

2. **Select patterns** from the Pattern Library (in the skill) based on detected stack. Universal patterns always apply; language-specific patterns apply per detected language. Structural patterns are OFF unless the PM explicitly requested a broader sweep.

3. **Define search chunks** — split the scoped path into 3-6 logical chunks by directory or system:
   - If architecture atlas exists at `tasks/architecture-atlas/systems-index.md`, use its system boundaries
   - Otherwise derive from `DIRECTORY.md` or top-level directory structure
   - If `$ARGUMENTS` scopes to a subtree, define chunks within that subtree only

4. **Check test suite** — identify the test runner command (`pytest`, `jest`, `npm test`, `cargo test`, etc.) and prepare to run it in Phase 1.

5. **Read `tasks/lessons.md`** (if exists) — add any project-specific bug patterns discovered there to the pattern set for this sweep.

6. **Generate run ID** — format `YYYY-MM-DD-HHhMM` (e.g., `2026-03-18-14h30`). All scratch output goes to `.claude/scratch/bug-sweep/{run-id}/`.

7. **Report:** Emit a chunk table showing each chunk's directory scope and assigned patterns, plus the test runner command.

---

## Phase 1: Search + Test (parallel)

Run Track A1 first (fast, in-coordinator). Then dispatch Track A2 agents and Track B in parallel.

### Track A1 — Mechanical Pattern Grep (Coordinator, fast)

Before dispatching any agents, run deterministic grep searches across all chunks via Bash. These are pattern-library entries resolvable by regex — no LLM needed:

```bash
# Universal
grep -rn "TODO\|FIXME\|HACK\|XXX\|BUG" ${SCOPE:-.} --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.cpp" --include="*.h"

# Empty catch/except (Python)
grep -Pn "except.*:\s*$" ${SCOPE:-.} -r --include="*.py" -A1 | grep -B1 "^\s*pass\s*$"

# Bare except (Python)
grep -rn "^\s*except:\s*$" ${SCOPE:-.} --include="*.py"

# Unhandled promise (JS/TS)
grep -rn "\.then(" ${SCOPE:-.} --include="*.ts" --include="*.tsx" --include="*.js" | grep -v "\.catch("
```

Capture results as a grep findings list, grouped by chunk. This feeds into Track A2 agents as context (< 30 seconds).

### Track A2 — Semantic Analysis (one Sonnet per chunk, parallel)

Dispatch one Agent per chunk using `model: sonnet`. Include tools: `["Read", "Write", "Grep", "Glob"]`.

Each agent prompt:
```
You are a bug-finding agent. Your chunk: [{chunk-name}] covering [{directories}].

Track A1 grep findings for your chunk (review for false positives):
{grep-findings-for-this-chunk}

For each file in your chunk:
1. Review the grep findings — flag any that are intentional patterns (catch-and-ignore, etc.) as false positives
2. Run deeper semantic analysis — read the code and identify:
   - Error handling gaps (unchecked return values, missing error propagation)
   - Potential null/undefined access
   - Resource leaks (file handles, connections not closed)
   - Logic errors (off-by-one, incorrect conditions, wrong operator)
   - Dead code paths
   - Race conditions or shared-state bugs
   - Language-specific patterns: {assigned-patterns-for-chunk}

For each finding:
- Severity: P0 (crash/data loss), P1 (incorrect behavior), P2 (edge case/minor)
- Confidence: HIGH / MEDIUM / LOW
- Location: file:line
- Description: what's wrong and why
- AI-fixable: yes / needs human verification / needs plan session

Cast a wide net. Report everything that looks like a bug, even if only moderately confident. The coordinator will triage. False positives are cheap; missed bugs are expensive.

Write your complete findings to: .claude/scratch/bug-sweep/{run-id}/{chunk-name}-phase1-sonnet.md

Return a brief summary (3-5 lines): file written, total finding count, any blockers encountered.
```

### Track B — Test Suite (one Haiku agent, parallel with Track A2)

Dispatch one Agent with `model: haiku`. Include tools: `["Bash", "Write", "Read"]`.

**Why Haiku:** Running a test command and capturing stdout is mechanical work — no semantic judgment needed. The coordinator triages the results.

Agent prompt:
```
Run the project test suite and capture results.

Test command: {test-runner-command}

For each test failure or error:
- Test name and file:line
- Error message (full, not truncated)
- Likely source of the bug (if determinable from the error)

If no test suite exists, report that fact clearly and stop.

Write complete results to: .claude/scratch/bug-sweep/{run-id}/tests-phase1-haiku.md

Return a brief summary: pass count, fail count, error count, any notable failures.
```

### Scratch Verification

After all Phase 1 agents complete, verify all expected scratch files exist:
```bash
ls .claude/scratch/bug-sweep/{run-id}/
```
If any chunk agent failed to write its file, re-dispatch that agent once. If it fails again, proceed with available findings — do not stall the sweep.

---

## Phase 2: Triage (Coordinator, ~5 min)

Read all Phase 1 scratch files from `.claude/scratch/bug-sweep/{run-id}/`.

### Step 2.0: Verify Findings Against Current Code

Before categorizing, verify each P1/HIGH-confidence finding actually exists. Phase 1 agents can hallucinate bugs already fixed by prior sweeps. Dispatch a **Haiku agent** per chunk (`model: haiku`) — this is mechanical read-and-confirm work:
1. **Read the cited file:line** — does the described code actually exist there?
2. **Check recent history** — `git log --oneline -5 {file}` for recent fixes
3. **Return verified/stale verdict per finding** — drop stale findings before categorization

### Step 2.1: Categorize

**1. Fix now (default)**
If the bug is clear and the fix is clear, it goes here. This includes:
- Missing error handling → add it
- Dead code → remove it
- Swallowed exceptions → add logging or re-raise
- Failed tests with obvious cause
- TODO/FIXME items that are straightforward
- Small scoping decisions the EM can make

**2. Backlog** — only for bugs that genuinely cannot be fixed in-session:
- Needs human verification (manual testing, visual check, play-testing)
- Needs a plan session (fix is large enough that getting it wrong would be expensive to undo)
- Logic that might be intentional and requires PM judgment

**3. False positive** — pattern matched but not actually a bug (intentional patterns, docs mentioning bug terminology, etc.)

**Bias toward fixing.** It's roughly the same effort to fix a small bug as to document it. If you can fix it safely, fix it — the backlog is for genuinely blocked items, not a parking lot.

**Deduplication:** Multiple agents may surface the same cross-system issue. Merge duplicates, keep the most detailed description.

**Output:** Two lists — "Fix now" grouped by file/system, and "Backlog" with "why blocked" for each item.

---

## Phase 3: Fix (Sonnet executors, parallel)

Dispatch Sonnet executor agents to fix all "Fix now" items. Group by file/system to minimize merge conflicts. Aim for 2-4 executors depending on how many systems are affected.

Each executor receives:
- The finding list for its file group (file:line, description, severity, confidence)
- Read access to the source files to understand context
- Clear acceptance criteria: fix the bug, don't refactor surrounding code, don't expand scope

**Post-fix test run:** After all executors complete, re-run the test suite:
```bash
{test-runner-command}
```
If any test fails that was passing before:
1. Identify which fix caused the regression
2. Revert that specific fix (`git diff` to identify the change, `git checkout -- {file}` to revert)
3. Move the finding to "Backlog — caused regression, needs human verification"

---

## Phase 4: Report and Commit (Coordinator)

**1. Commit fixes:**
```bash
git add -A
git commit -m "bug-sweep: fixed N bugs across M files"
```

**2. Update bug backlog** (only if there are genuinely blocked items):

Append to `tasks/bug-backlog.md`. If the file doesn't exist and there are blocked items, create it:

```markdown
# Bug Backlog

> Last sweep: YYYY-MM-DD | Commit at sweep: [short hash] | Open: N items
> Next sweep suggested: when code churn warrants it — workday-start tracks this

| ID | System | Severity | Description | Why Blocked | Found |
|----|--------|----------|-------------|-------------|-------|
```

ID format: `BS-{date}-{N}`. Only genuinely blocked bugs go here. Fixed bugs belong in git history, not the backlog. Remove entries when resolved — don't mark them "fixed" and leave them in the table.

**3. Report to PM:**
```markdown
## Bug Sweep Complete

**Scope:** [path scanned] | [N] systems, [M] files
**Patterns applied:** [list]
**Tests:** [pass/fail/error counts — before and after fixes]
**Found:** [total] findings ([X] fixed, [Y] backlogged, [Z] false positives)
**Fixes applied:**
- file:line — description
**Blocked items:** [list with "why blocked", or "none"]
```

**4. Delete scratch files:**
```bash
rm -rf .claude/scratch/bug-sweep/{run-id}/
```
Scratch files are fully consumed by the triage and fix phases. No persistent value.

---

## Failure Modes

| Failure | Prevention |
|---------|------------|
| False positive flood | Phase 2 triage with explicit "false positive" category — filter aggressively |
| Fix introduces regression | Post-fix test suite run; revert and backlog if new failures appear |
| Sonnet over-reports low-confidence findings | Coordinator filters by confidence; LOW-confidence + needs-human-verification → backlog |
| Pattern library misses project-specific bugs | Phase 0 reads `tasks/lessons.md` for known gotchas before dispatching |
| Test suite doesn't exist | Report the gap, suggest adding tests, proceed with code-only sweep |
| Executor fix conflicts across files | Group fixes by file/system to minimize overlap; sequential if one system has many fixes |
| Scratch file missing after agent completes | Verify with `ls`; re-dispatch once; proceed with available findings if it fails again |

---

## Cost Profile

| Scenario | Sonnet Agents | Executors | Wall-Clock |
|----------|---------------|-----------|------------|
| Small repo, 3 systems | 4 (3 search + 1 test) | 2-3 | ~15-25 min |
| Medium repo, 6 systems | 7 (6 search + 1 test) | 3-5 | ~25-40 min |
| Large repo, 8+ systems | 9+ (search + 1 test) | 4-6 | ~35-50 min |

Track A1 grep adds < 1 min to Phase 0 regardless of repo size. It runs in-coordinator with no agent cost.

---

## Relationship to Other Commands

- **`pipelines/bug-sweep/PIPELINE.md`** — the pipeline definition this command executes. Full pattern library, phase definitions, and backlog schema live there.
- **`/workday-start`** — surfaces a staleness nudge when no bug sweep has run in 30+ days. That's the trigger to run this command.
- **`/review-dispatch`** — for reviewing specific files or PRs, not a codebase-wide bug hunt.
- **`/delegate-execution`** — for executing a known list of tasks. Bug-sweep generates its own work list; use delegate-execution only if manually curating fixes from the backlog.
- **`daily-code-health` skill** — for recent-commit review (not a full sweep). Structural patterns excluded from bug-sweep belong there.
- **`weekly-architecture-audit` skill** — for architectural debt. Structural patterns excluded from bug-sweep also belong there.
