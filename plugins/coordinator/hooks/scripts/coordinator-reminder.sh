#!/bin/bash
# Context-aware coordinator reminder
# Full EM model for project_type: meta (~/.claude repo)
# Light-touch reminder for all other projects

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Find repo root (works regardless of CWD)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

# Default: no coordinator.local.md found
PROJECT_TYPE=""

if [ -n "$REPO_ROOT" ]; then
  LOCAL_MD="$REPO_ROOT/.claude/coordinator.local.md"
  if [ -f "$LOCAL_MD" ]; then
    # Extract project_type from YAML frontmatter
    PROJECT_TYPE=$(sed -n '/^---$/,/^---$/{ /^project_type:/{ s/^project_type:[[:space:]]*//; p; } }' "$LOCAL_MD")
  fi
fi

if [ "$PROJECT_TYPE" = "meta" ]; then
  # Full EM operating model for the orchestration infrastructure repo
  cat <<'EOF'
# Coordinator — Meta Project Mode
You are the EM operating on your own orchestration infrastructure.
- TodoWrite flight recorder: create IMMEDIATELY when a goal is set
- Research 2+ queries → delegate to Explore/Enricher agents
- Code implementation → delegate to Executor agents
- Reviews → /review-dispatch; 2+ independent tasks → parallel dispatch
- Write-ahead status: update Status fields BEFORE starting work, not after
- Agent outputs → write to disk immediately, verify before proceeding
- Skills/templates are tested infrastructure — follow them, don't improvise
EOF
else
  # Light-touch reminder for project repos
  cat <<'EOF'
Coordinator infrastructure is available for complex work:
- /review-dispatch — route artifacts to domain + architecture reviewers
- /enrich-and-review — enrich specs with codebase research
- /delegate-execution — dispatch executor agents for implementation
Use these when they add value. For direct requests, just do the work.
EOF
fi
