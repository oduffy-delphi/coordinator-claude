#!/bin/bash
# SessionStart hook: inject project orientation documents into context
# Convention-based discovery — reads what exists, skips what doesn't.
# Subsumes the old repomap-sessionstart.sh (staleness check + content injection).

# RAM cache check — prefer compact cache over raw docs
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
CACHE="${REPO_ROOT:-.}/.claude/orientation_cache.md"

if [ -f "$CACHE" ]; then
    # Extract git HEAD from YAML frontmatter (portable across GNU/BSD sed)
    CACHE_HEAD=$(grep '^git_head_at_generation:' "$CACHE" | head -1 | sed 's/.*: *//; s/["'"'"'[:space:]]//g')

    # File age check
    if [[ "$OSTYPE" == "darwin"* ]]; then
        file_epoch=$(stat -f %m "$CACHE" 2>/dev/null)
    else
        file_epoch=$(stat -c %Y "$CACHE" 2>/dev/null)
    fi

    if [ -z "$file_epoch" ]; then
        # Cannot stat — treat as stale
        :
    else
        now_epoch=$(date +%s)
        age_hours=$(( (now_epoch - file_epoch) / 3600 ))
        # Review: patrik — short-circuit: cache < 1h old is always fresh enough,
        # even on high-velocity days (50+ commits). Avoids fallthrough to raw injection.
        age_minutes=$(( (now_epoch - file_epoch) / 60 ))
        if [ "$age_minutes" -lt 60 ]; then
            echo ""
            echo "── Orientation (RAM cache, ${age_minutes}m old, fresh) ──"
            cat "$CACHE"
            echo ""
            echo "── Orientation: 1 document loaded (from cache) ──"
            exit 0
        fi
        commits_since=$(git rev-list --count "${CACHE_HEAD}..HEAD" 2>/dev/null || echo "999")

        if [ "$age_hours" -lt 24 ] && [ "$commits_since" -lt 50 ]; then
            echo ""
            echo "── Orientation (RAM cache, ${age_hours}h old, ${commits_since} commits since) ──"
            cat "$CACHE"
            echo ""
            echo "── Orientation: 1 document loaded (from cache) ──"
            exit 0
        fi
    fi
fi

# Fall through to raw doc injection (current behavior)

MAX_LINES=150

inject_doc() {
    local label="$1"
    shift
    for path in "$@"; do
        if [ -f "$path" ]; then
            echo ""
            echo "── $label ($path) ──"
            head -n "$MAX_LINES" "$path"
            local total
            total=$(wc -l < "$path" | tr -d ' ')
            if [ "$total" -gt "$MAX_LINES" ]; then
                echo "[... truncated at $MAX_LINES of $total lines — read full file for details]"
            fi
            return 0
        fi
    done
    return 1
}

repomap_with_staleness() {
    local path=".claude/repomap.md"
    if [ ! -f "$path" ]; then
        echo ""
        echo "── Repo Map: NOT FOUND ──"
        echo "No repository map. Run /generate-repomap to create one."
        return 1
    fi

    # Staleness check
    if [[ "$OSTYPE" == "darwin"* ]]; then
        file_epoch=$(stat -f %m "$path" 2>/dev/null)
    else
        file_epoch=$(stat -c %Y "$path" 2>/dev/null)
    fi

    local stale_msg=""
    if [ -n "$file_epoch" ]; then
        now_epoch=$(date +%s)
        age_hours=$(( (now_epoch - file_epoch) / 3600 ))
        if [ "$age_hours" -ge 24 ]; then
            stale_msg=" ⚠ STALE (${age_hours}h old) — run /generate-repomap to refresh"
        fi
    fi

    echo ""
    echo "── Repo Map ($path)${stale_msg} ──"
    head -n "$MAX_LINES" "$path"
    local total
    total=$(wc -l < "$path" | tr -d ' ')
    if [ "$total" -gt "$MAX_LINES" ]; then
        echo "[... truncated at $MAX_LINES of $total lines — read full file for details]"
    fi
    return 0
}

found=0

# 1. Repo map (with staleness check)
repomap_with_staleness && found=$((found + 1))

# 2. Directory
inject_doc "Directory" "DIRECTORY.md" "docs/DIRECTORY.md" && found=$((found + 1))

# Action items and roadmap are loaded by /session-start (operational context),
# not at boot (structural context). Quick sessions don't need them.

echo ""
if [ "$found" -gt 0 ]; then
    echo "── Orientation: $found document(s) loaded ──"
else
    echo "── Orientation: no standard documents found (repomap, DIRECTORY.md) ──"
fi
