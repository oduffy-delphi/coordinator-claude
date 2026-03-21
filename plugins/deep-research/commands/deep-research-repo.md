---
description: "Pipeline A relay driver — deep research on a repository. Dispatches the orchestrator per-phase and workers per-manifest. Handles scoping, Haiku file mapping, Sonnet analysis, optional comparison, and Opus synthesis."
allowed-tools: ["Agent", "Read", "Write", "Bash", "Glob", "Grep"]
argument-hint: "<repo-path> [--compare <project-path>]"
---

# Deep Research — Pipeline A (Repo Research) Relay Driver

This command drives the full Pipeline A relay: orchestrator dispatches for judgment, worker dispatches for mechanical/analytical work, verification between phases, and commits at each milestone.

**Read the relay protocol for format details:** `~/.claude/plugins/deep-research/pipelines/relay-protocol.md`

## Arguments

`$ARGUMENTS`:
- `<repo-path>` — path to the repository to research (required)
- `--compare <project-path>` — optional path to a project to compare against

## Step 1 — Setup

1. Parse arguments: extract repo path and optional comparison path
2. Generate run ID: `YYYY-MM-DD-HHhMM` (current timestamp)
3. Generate topic slug from repo name (e.g., `onnxruntime`, `langchain`)
4. Create scratch directory:
   ```bash
   mkdir -p tasks/scratch/deep-research/{run-id}/prompts
   ```
5. Set output path: `docs/research/YYYY-MM-DD-{topic-slug}.md` (use project's docs/research/ if it exists, otherwise `~/.claude/docs/research/`)
6. Create empty decisions log: write `# Decisions Log\n` to `{scratch-dir}/decisions.md`

Announce: "Running Pipeline A (repo research) on {repo-path}."

## Step 2 — Phase 0: Scope (Orchestrator Dispatch)

Dispatch the `deep-research-orchestrator` agent (`subagent_type: "deep-research:deep-research-orchestrator"`):

```
Phase: 0 — Scope Definition

Pipeline: A (Repo Research)
Target: {repo-path}
{If --compare: "Comparison target: {project-path}"}
Scratch directory: {scratch-dir}

Survey the repository, define 4-6 domain-aligned chunks, pin the version,
and write focus questions. Write Haiku file mapping worker prompts using
templates from agent-prompts.md.

Write your outputs to:
1. Dispatch manifest: {scratch-dir}/dispatch-manifest.md
2. Worker prompts: {scratch-dir}/prompts/{worker-id}.md (one per chunk)
3. Decisions log: {scratch-dir}/decisions.md (READ existing content first, then APPEND your Phase 0 section)
```

**Verify:** Read `{scratch-dir}/dispatch-manifest.md`. Confirm status is `DISPATCH_WORKERS` and worker entries exist.

## Step 3 — Phase 1: File Mapping (Haiku Workers)

Read the dispatch manifest. For each worker entry:

1. Read the prompt file from `{scratch-dir}/prompts/{worker-id}.md`
2. Dispatch the worker as an Agent:
   - `model: "haiku"` (or as specified in manifest)
   - `run_in_background: true` (if manifest says `Parallel: true`)
   - `prompt:` the content of the prompt file

Wait for all workers to complete.

**Verify:** Check that all expected output files exist in `{scratch-dir}/phase-1/`:
```bash
ls {scratch-dir}/phase-1/
```

For any missing or empty files: re-dispatch that worker once with the same prompt. Skip on second failure, noting the gap.

**Commit:**
```bash
git add -A && git commit -m "deep-research: phase 1 (Haiku file mapping) complete"
```

## Step 4 — Pre-Phase 2: Quality Gate + Analysis Scoping (Orchestrator Dispatch)

Dispatch the orchestrator for quality evaluation and Phase 2 prompt generation:

```
Phase: 1.5 — Pre-Phase 2 Quality Gate

Pipeline: A (Repo Research)
Target: {repo-path}
Scratch directory: {scratch-dir}

Phase 1 worker outputs are at:
{list each file in {scratch-dir}/phase-1/}

Read the Phase 1 outputs, evaluate quality (completeness, actual values,
cross-subsystem connections). Write Sonnet standalone analysis worker prompts
using templates from agent-prompts.md. Include the Phase 1 output content in
each Sonnet prompt (paste it into the template's input section).

Decisions log: {scratch-dir}/decisions.md
Read decisions.md first — it contains your Phase 0 judgments.

Write your outputs to:
1. Dispatch manifest: {scratch-dir}/dispatch-manifest.md
2. Worker prompts: {scratch-dir}/prompts/{worker-id}.md (one per chunk)
3. Decisions log: {scratch-dir}/decisions.md (READ first, APPEND Phase 1.5 section)
```

**Verify:** Read manifest. Confirm status is `DISPATCH_WORKERS`.

## Step 5 — Phase 2: Standalone Analysis (Sonnet Workers)

Read the dispatch manifest. For each worker:

1. Read the prompt file
2. Dispatch the worker:
   - `model: "sonnet"`
   - `run_in_background: true`
   - `prompt:` prompt file content

Wait for all workers to complete.

**Verify:** Check output files in `{scratch-dir}/phase-2/`. Re-dispatch once on failure; skip on second.

**Commit:**
```bash
git add -A && git commit -m "deep-research: phase 2 (Sonnet analysis) complete"
```

## Step 6 — Phase 3: Comparison (CONDITIONAL)

**Skip this step if `--compare` was NOT provided.** Jump to Step 7.

If comparison is in scope, dispatch the orchestrator for comparison prompt generation:

```
Phase: 2.5 — Pre-Phase 3 Comparison Scoping

Pipeline: A (Repo Research)
Target: {repo-path}
Comparison target: {project-path}
Scratch directory: {scratch-dir}

Phase 2 worker outputs are at:
{list each file in {scratch-dir}/phase-2/}

Read the Phase 2 analyses and write Sonnet comparison worker prompts
using templates from agent-prompts.md. Include the Phase 2 output content
in each comparison prompt. List the project files to compare against.

Decisions log: {scratch-dir}/decisions.md
Read decisions.md first — it contains Phase 0 and Phase 1.5 judgments.

Write your outputs to:
1. Dispatch manifest: {scratch-dir}/dispatch-manifest.md
2. Worker prompts: {scratch-dir}/prompts/{worker-id}.md (one per chunk)
3. Decisions log: {scratch-dir}/decisions.md (READ first, APPEND Phase 2.5 section)
```

**Verify:** Read manifest. Dispatch Sonnet comparison workers same as Step 5.

Wait, verify, commit:
```bash
git add -A && git commit -m "deep-research: phase 3 (Sonnet comparison) complete"
```

## Step 7 — Phase 4: Synthesis (Orchestrator Dispatch)

Dispatch the orchestrator for final synthesis (`subagent_type: "deep-research:deep-research-orchestrator"`):

```
Phase: 4 — Synthesis

Pipeline: A (Repo Research)
Target: {repo-path}
{If comparison ran: "Comparison target: {project-path}"}
Scratch directory: {scratch-dir}

Phase 2 worker outputs:
{list each file in {scratch-dir}/phase-2/}

{If Phase 3 ran:}
Phase 3 comparison outputs:
{list each file in {scratch-dir}/phase-3/}

Cross-reference all analyses and produce the final synthesis document(s).
{If comparison: "Produce BOTH an ASSESSMENT.md and GAP-ANALYSIS.md."}
{If no comparison: "Produce an ASSESSMENT.md."}

Use the Phase 4 synthesis template from agent-prompts.md.

Decisions log: {scratch-dir}/decisions.md
Read decisions.md first — it contains all prior phase judgments.

Write your outputs to:
1. Final document: {output-path}
{If comparison: "2. Gap analysis: {output-path with -gap-analysis suffix}"}
2. Dispatch manifest: {scratch-dir}/dispatch-manifest.md (set status to COMPLETE)
3. Decisions log: {scratch-dir}/decisions.md (READ first, APPEND Phase 4 section)
```

**Verify:** Read manifest. Confirm status is `COMPLETE`. Verify final document exists and has substantive content.

**Commit:**
```bash
git add -A && git commit -m "deep-research: phase 4 (synthesis) complete"
```

## Step 8 — Archive and Report

1. Archive the paper trail:
   ```bash
   mkdir -p docs/research/archive/YYYY-MM-DD-{topic-slug}
   cp {scratch-dir}/decisions.md docs/research/archive/YYYY-MM-DD-{topic-slug}/
   cp -r {scratch-dir}/prompts docs/research/archive/YYYY-MM-DD-{topic-slug}/
   cp -r {scratch-dir}/phase-1 docs/research/archive/YYYY-MM-DD-{topic-slug}/
   cp -r {scratch-dir}/phase-2 docs/research/archive/YYYY-MM-DD-{topic-slug}/
   cp {scratch-dir}/dispatch-manifest.md docs/research/archive/YYYY-MM-DD-{topic-slug}/
   ```
   If Phase 3 ran: also copy `phase-3/`.

2. Delete scratch directory:
   ```bash
   rm -rf {scratch-dir}
   ```

3. Commit:
   ```bash
   git add -A && git commit -m "deep-research: archive paper trail, clean scratch"
   ```

4. Report to the PM:
   ```
   Research complete. Final document at {output-path}.
   Paper trail at docs/research/archive/YYYY-MM-DD-{topic-slug}/ ({N} files).

   If this research won't be revisited, you can delete the paper trail:
   rm -rf docs/research/archive/YYYY-MM-DD-{topic-slug}/
   ```

5. Present the executive summary from the synthesis document to the PM for discussion.

## Error Handling

- If any orchestrator dispatch returns `ERROR:` status — abort pipeline, report to PM with the error reason
- If a worker fails twice — skip it, note the gap in the next orchestrator dispatch prompt
- If decisions.md appears corrupted (missing expected phase headers) — re-dispatch the prior orchestrator phase
- See `relay-protocol.md` for the full error handling table
