---
description: Bootstrap or refresh the architecture atlas via a multi-phase agent pipeline (Haiku scouts → Sonnet analysts → Opus synthesizer)
allowed-tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent"]
argument-hint: [--refresh]
---

# Architecture Audit — Architecture Atlas Bootstrap and Refresh

Runs the `deep-architecture-audit` skill to produce or update the persistent architecture atlas at `tasks/architecture-atlas/`. The atlas captures function-level connectivity, ASCII flow diagrams, cross-system dependency matrices, and per-system observations for the full codebase.

Each model tier does what it's best at: Haiku inventories mechanically (cheap, parallel), Sonnet analyzes and diagrams (analytical depth), Opus synthesizes cross-system (highest judgment for connectivity mapping). Phases run in strict sequence — each phase's output shapes the next.

**Announce at start:** "I'm running `/architecture-audit` to [bootstrap the architecture atlas / refresh the architecture atlas for churned systems]."

---

## Arguments

`$ARGUMENTS` may contain `--refresh` to force refresh mode. Otherwise, mode is auto-detected.

- **No `--refresh`, no atlas:** First run. Full discovery of all systems.
- **No `--refresh`, atlas exists:** Same as first run — full discovery unless `--refresh` is passed.
- **`--refresh`:** Refresh mode. Identifies churned systems via git activity, remaps only those, carries stable systems forward. Substantially cheaper.

Auto-detection rule: check for `tasks/architecture-atlas/systems-index.md`. If not found, first run. If found and `--refresh` is not passed, prompt the PM: "Atlas already exists. Did you mean to pass `--refresh`?" and stop.

---

## Phase 0: Scope and Chunking (Coordinator)

**Model:** Coordinator (Opus). **Time:** ~5 min.

1. Read orientation artifacts:
   - `.claude/repomap.md` — function-level map with cross-file references
   - `DIRECTORY.md` — directory structure documentation

2. **First run — define system boundaries and sub-chunks:**
   - Derive 4-8 system boundaries from repo map + directory structure
   - Each file is assigned to exactly ONE system. No overlapping assignments.
   - Shared utilities go to a dedicated "shared/core" system or to the most dependent system.
   - **Sub-chunk large systems:** Any system with >12 files splits into sub-chunks of 8-12 files grouped by concern. Sub-chunks share the same Sonnet analyst in Phase 2; each gets its own Haiku scout in Phase 1. Label sub-chunks with the system's chunk letter + number suffix (e.g., `B1`, `B2`).
   - Write focus questions for each chunk.
   - **Generate run ID** — format: `YYYY-MM-DD-HHhMM`. Scratch directory: `.claude/scratch/deep-architecture-audit/{run-id}/`
   - **Output:** First Run Chunk Table from `deep-architecture-audit/agent-prompts.md`. All chunks `mode: full`.

3. **Refresh run — identify churned systems:**
   - Read `systems-index.md` for existing system list and `Last mapped` dates.
   - Diff git activity since each system's last mapped date:
     ```bash
     git log --since="<last-mapped-date>" --name-only --pretty=format: -- <system-dirs> | sort -u
     ```
   - Systems with changed files → `mode: refresh`. Systems with no changes → `mode: stable`.
   - Apply same sub-chunking rule to churned systems.
   - **Generate run ID** — same format. Scratch directory: `.claude/scratch/deep-architecture-audit/{run-id}/`
   - **Output:** Refresh Chunk Table from `deep-architecture-audit/agent-prompts.md`.

**Chunk table templates are in `deep-architecture-audit/agent-prompts.md`.** Use them verbatim.

---

## Phase 1: Function-Level Inventory (Haiku agents, parallel)

**Model:** Haiku. **Dispatch:** One agent per sub-chunk with `mode: full` or `mode: refresh`.

**First run (mode: full):** Each agent reads every file in its sub-chunk and produces:
- File path, line count, key structs/functions with signatures
- Caller/callee relationships with `[ENTRY]`, `[BOUNDARY -> system-name]`, `[INTERNAL -> sub-chunk-name]`, and `[UNKNOWN]` markers
- Constants with actual values
- Cross-subsystem data flow

**Refresh (mode: refresh — Phase 1R):** Each agent receives the existing atlas entry and focuses only on changed files. Produces a delta inventory: new functions, removed functions, changed signatures, new/removed cross-system boundaries.

**DISPATCH:** Open `deep-architecture-audit/agent-prompts.md`. Copy the **Phase 1: Haiku Function-Level Inventory Prompt** (first run) or **Phase 1R: Haiku Delta Inventory Prompt (Refresh)** template verbatim. Fill in the bracketed fields. Do NOT write a custom prompt — the template's guardrails prevent Haiku from confabulating relationships.

**Scratch path (first run):** `.claude/scratch/deep-architecture-audit/{run-id}/{chunk-letter}{sub-chunk}-phase1-haiku.md`
**Scratch path (refresh):** `.claude/scratch/deep-architecture-audit/{run-id}/{chunk-letter}{sub-chunk}-phase1R-haiku.md`

Include `Write` in the agent's tool list. Dispatch with `run_in_background: true`. Pass the scratch path as `[SCRATCH_PATH]` in the template.

**Scratch verification:** Before proceeding to Phase 2, verify all expected Phase 1 scratch files exist. If any are missing, re-dispatch the failed agent once. If it fails again, skip that sub-chunk and note the gap — the Sonnet analyst will work with incomplete inventory for that system.

---

## Phase 2: System Analysis and Diagrams (Sonnet agents, parallel)

**Model:** Sonnet. **Dispatch:** One agent per system (reads ALL sub-chunk inventories for that system from the scratch directory).

**First run (Phase 2):** Each agent reads all sub-chunk Phase 1 reports for its system and produces:
1. System narrative — purpose, responsibilities, design philosophy
2. ASCII information flow diagram (max 100 chars wide; split complex flows into labeled sub-diagrams)
3. Boundary catalog — every cross-system connection in `{function} -> {target_system}:{target_function} | {data_type}` format
4. Key architectural observations — Strengths, Concerns, Notable Patterns. **No grade.**
5. Summary — top 3-5 aspects ranked by architectural significance

**Refresh (Phase 2R):** Each agent receives the existing atlas page + all Phase 1R delta reports for its system. Produces an updated atlas page: preserves unchanged sections verbatim, updates affected sections, regenerates ASCII diagram if flow changed materially, updates YAML frontmatter (`last_mapped`, `entry_points`, `cross_system_connections`, `dependencies`). No grade.

**DISPATCH:** Open `deep-architecture-audit/agent-prompts.md`. Copy the **Phase 2: Sonnet System Analysis Prompt (Discovery)** (first run) or **Phase 2R: Sonnet System Analysis Update Prompt (Refresh)** template verbatim. Do NOT write a custom prompt — the observation-only structure prevents grade confabulation on first pass.

**Scratch path (first run):** `.claude/scratch/deep-architecture-audit/{run-id}/{chunk-letter}-phase2-sonnet.md`
**Scratch path (refresh):** `.claude/scratch/deep-architecture-audit/{run-id}/{chunk-letter}-phase2R-sonnet.md`

Include `Write` in the agent's tool list. Dispatch with `run_in_background: true`. Pass the scratch path as `[SCRATCH_PATH]` in the template.

**Scratch verification:** Before proceeding to Phase 3, verify all expected Phase 2/2R scratch files exist. Re-dispatch once on failure; skip that system on second failure and note the gap for Opus.

**Context overflow check:** Measure total Phase 2 output before dispatching Phase 3. If combined output exceeds ~80K tokens (~300KB markdown, ~4000 lines), summarize each system to its boundary catalog + top 5 observations before passing to Opus. Do not pass raw reports that would overflow context.

---

## Phase 3: Cross-System Synthesis (Opus, single agent)

**Model:** Opus. **Input:** ALL Phase 2 reports (first run) or stable atlas pages + Phase 2R reports (refresh).

**First run (Phase 3):** Opus cross-references all boundary catalogs and produces five atlas artifacts:
1. `systems-index.md` — master index table: System, File Count, Entry Points, Cross-System Connections, Dependencies, Last Mapped. **No Grade or Status columns.**
2. `cross-system-map.md` — unified ASCII diagram with box-drawing characters, max 120 chars wide
3. `connectivity-matrix.md` — system-to-system dependency counts table
4. `file-index.md` — one line per tracked file mapping it to its system
5. `systems/{name}.md` — per-system detail pages with YAML frontmatter:
   ```yaml
   ---
   system: [system-name-kebab-case]
   last_mapped: YYYY-MM-DD
   entry_points: N
   cross_system_connections: N
   dependencies: [list]
   ---
   ```
   No grade or status fields in YAML frontmatter.

**Refresh (Phase 3R):** Opus merges stable + churned. Regenerates `cross-system-map.md` and `connectivity-matrix.md` from the union of all systems. Updates `systems-index.md` rows for churned systems only; preserves stable rows. Updates `file-index.md` for file additions, removals, and reassignments. Updates per-system files for churned systems only.

**DISPATCH:** Open `deep-architecture-audit/agent-prompts.md`. Copy the **Phase 3: Opus Cross-System Synthesis Prompt (Full)** (first run) or **Phase 3R: Opus Cross-System Synthesis Prompt (Refresh)** template verbatim. Do NOT write a custom prompt.

Opus writes atlas artifacts directly to `tasks/architecture-atlas/`. If Phase 3 fails, the previous atlas remains intact — no partial writes.

---

## Phase 4: Integration and Report (Coordinator)

**Model:** Coordinator (Opus). **Time:** ~5 min.

1. **Review atlas artifacts for completeness:**
   - Every system has a per-system file in `systems/`
   - `systems-index.md` has a row for every system
   - `cross-system-map.md`, `connectivity-matrix.md`, and `file-index.md` are present
   - All per-system YAML frontmatter has required fields

2. **Present summary to PM:**
   - Systems discovered, file counts, key entry points
   - Key architectural observations — coupling hotspots, boundary patterns, notable design choices
   - Systems that may warrant early audit priority (high cross-system connections, large file counts)
   - Comparison with previous mapping if refresh run

3. **Atomic commit:**
   ```bash
   git add tasks/architecture-atlas/
   git commit -m "deep-architecture-audit: [first run|refresh] — [N] systems mapped"
   ```

4. **Note suggested weekly rotation starting point** — systems with highest cross-system connectivity and oldest `Last mapped` dates get priority for first `weekly-architecture-audit` pass.

5. **Delete scratch files:**
   ```bash
   rm -rf .claude/scratch/deep-architecture-audit/{run-id}/
   ```

---

## Failure Modes

| Failure | Prevention |
|---------|------------|
| Haiku invents call relationships | Template guardrail: "write [UNKNOWN], do NOT guess" |
| Haiku analyzes instead of inventorying | Template guardrail: "completeness > analysis" |
| Dispatching agents with >12 files | Sub-chunk to 8-12 files per agent before dispatch |
| ASCII diagrams too wide | "max 100 chars, split if needed" |
| Grades added during discovery | Phase 2 uses Discovery template (no grade); weekly audit adds grades |
| Custom prompts instead of templates | Read `agent-prompts.md`, copy verbatim, fill blanks |
| Chunk boundary overlap | Phase 0: each file assigned to exactly ONE system |
| Opus context overflow | If Phase 2 output >80K tokens, coordinator summarizes before Opus |
| Partial write on failure | Phase 4 atomic commit; Phase 3 failure leaves previous atlas intact |
| Atlas exists but no `--refresh` passed | Prompt PM; do not proceed without explicit mode confirmation |
| Phase 1/2 scratch file missing | Re-dispatch once; skip and note gap on second failure |

---

## Cost Profile

| Scenario | Haiku | Sonnet | Opus | Wall-Clock |
|----------|-------|--------|------|------------|
| First run, 6 systems (all ≤12 files) | 6 | 6 | 1 | ~25-35 min |
| First run, 8 systems (all ≤12 files) | 8 | 8 | 1 | ~35-45 min |
| First run with large system (e.g., 59-file system → 5-6 sub-chunks) | 10-14 | 6-8 | 1 | ~40-55 min |
| Refresh, 2 churned systems | 2 | 2 | 1 | ~15-20 min |
| Refresh, 5 churned systems | 5 | 5 | 1 | ~25-30 min |

Large systems multiply Haiku agent count but not Sonnet count — one Sonnet analyst receives all sub-chunk reports for a given system.

---

## Relationship to Other Commands

- **`/weekly-architecture-audit`** — maintains the atlas incrementally after this command establishes it. Adds grades to per-system pages. Requires a populated atlas; run this command first.
- **`pipelines/deep-architecture-audit/PIPELINE.md`** — the pipeline definition this command executes. The source of truth for pipeline behavior; this command codifies the orchestration loop.
- **`coordinator:dispatching-parallel-agents`** — required background skill for Phase 1 and Phase 2 dispatch. Read before running this command if parallel agent dispatch is unfamiliar.
- **`update-docs`** — uses `file-index.md` for new-system detection: files not listed in the index flag new systems for PM review.
