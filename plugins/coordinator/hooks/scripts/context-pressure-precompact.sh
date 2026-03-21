#!/bin/bash
# PreCompact sentinel — writes marker for next UserPromptSubmit to detect.
# Output is IGNORED by Claude Code for PreCompact events.
#
# Assumption: session_id is UUID format (hex + hyphens, filename-safe).
# If the runtime changes session_id format, fall back to md5 hash pattern
# (see executor-exit-watchdog.sh lines 33-40).
set -euo pipefail

HOOK_INPUT=$(cat)

# Extract session_id — prefer jq, fall back to grep for environments without it
if command -v jq &>/dev/null; then
  SESSION_ID=$(echo "$HOOK_INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)
else
  SESSION_ID=$(echo "$HOOK_INPUT" | sed -n 's/.*"session_id"\s*:\s*"\([^"]*\)".*/\1/p' | head -1)
fi

if [[ -z "$SESSION_ID" ]]; then
  exit 0  # fail-open: no session_id, can't write sentinel
fi

touch "/tmp/compaction-occurred-${SESSION_ID}"
