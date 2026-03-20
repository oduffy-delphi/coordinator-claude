---
description: Generate a ranked repository map for LLM context injection
allowed-tools: ["Bash", "Read"]
argument-hint: "[--budget N] [--project-root PATH] [--profile PROFILE]"
---

# Generate Repository Map

Generate a structural map of the current repository, ranked by git activity, fitted to a token budget. Output goes to `.claude/repomap.md` in the project root.

## Instructions

### Locate the Script

The `generate-repomap.py` script ships with the repo under `.github/scripts/`. Find it by checking these locations in order:

1. `${CLAUDE_PLUGIN_ROOT}/../../.github/scripts/generate-repomap.py` — if the full repo is installed as a plugin
2. The repo clone directory (if the user cloned rather than copied plugins)

```bash
# Find the script
REPOMAP_SCRIPT=""
for candidate in \
  "${CLAUDE_PLUGIN_ROOT}/../../.github/scripts/generate-repomap.py" \
  "$(git -C "${CLAUDE_PLUGIN_ROOT}" rev-parse --show-toplevel 2>/dev/null)/.github/scripts/generate-repomap.py"; do
  if [ -f "$candidate" ]; then
    REPOMAP_SCRIPT="$candidate"
    break
  fi
done

if [ -z "$REPOMAP_SCRIPT" ]; then
  echo "ERROR: generate-repomap.py not found. Clone the full coordinator-claude repo, or ensure .github/scripts/ is alongside the plugins/ directory."
  exit 1
fi
```

### Running the Generator

**Default invocation** (no arguments):
```bash
python3 "$REPOMAP_SCRIPT" \
  --project-root "${PROJECT_ROOT:-.}" \
  --budget 4000 \
  --profile balanced
```

**With user arguments:** If `$ARGUMENTS` is provided, pass the entire argument string to the script. The script handles its own defaults for any flags not specified:
```bash
python3 "$REPOMAP_SCRIPT" $ARGUMENTS
```

User arguments always take full precedence — do not merge individual flags with defaults.

After generation, briefly report:
- Number of files included vs total
- Approximate token count
- Output path

The map is cached — subsequent runs only re-parse changed files.

### Task-Scoped Maps

For generating maps focused on specific task areas:

```bash
python3 "$REPOMAP_SCRIPT" \
  --project-root /path/to/project \
  --task "Implement the camera follow system for the drone actor" \
  --focus-files "src/core/Camera/CameraFollowComponent.cpp,src/core/Player/PlayerActor.h"
```

- `--task`: Natural language description of the current task. Path-like tokens in the description are matched against project files.
- `--focus-files`: Comma-separated list of file paths (relative to project root) to boost. These files and their graph neighbors get priority.
- When either flag is used, output defaults to `.claude/repomap-task.md` instead of `.claude/repomap.md`.
- Task-scoped maps are awareness-based — the coordinator decides when to generate them, not every dispatch.

### Error Handling

If the script fails:
1. **Python not found:** Check that `python3` is on PATH. On Windows, `python` may be the correct command — try both.
2. **Script not found:** The script discovery block above should locate it. If not found, the user needs to clone the full `coordinator-claude` repo (not just copy `plugins/`), or place `generate-repomap.py` alongside the plugins directory at `.github/scripts/`.
3. **Non-zero exit code:** Report the script's stderr output to the user. Common causes: missing dependencies (run `pip install tree-sitter tree-sitter-language-pack`), permission errors on the cache file, or invalid `--project-root` path.
4. **No output generated:** Check that the project root contains trackable files (not an empty directory).
