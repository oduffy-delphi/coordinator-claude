#!/bin/bash
# sync-from-private.sh — one-way push from private repo to public repo
#
# Copies plugins from ~/.claude/plugins/oduffy-custom/ into the public
# coordinator-claude repo, rewriting internal path references in .md files
# and auditing for personal data that shouldn't ship publicly.
#
# Usage: setup/sync-from-private.sh [--dry-run] [--force] [--include-repomap] [--allow-deletions]

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PRIVATE_ROOT="$HOME/.claude"
PUBLIC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PLUGINS=(coordinator game-dev web-dev data-science notebooklm)

# Patterns that are expected and need no action
EXPECTED_PATTERNS=(
    'oduffy-delphi'
    "O'Duffy"
    'Dónal'
    'work/striker/'
)

# Patterns that require manual review before publishing (grep -P regex)
# Note: `striker` and bare `oduffy` are checked with context logic below, not here
REVIEW_PATTERNS=(
    'C:\\\\Users\\\\oduffy'
    'C:\\Users\\oduffy'
    'X:\\\\'
    'X:\\'
    '\bbetta\b'
    '\bBetta-Air\b'
)

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

DRY_RUN=false
FORCE=false
INCLUDE_REPOMAP=false
ALLOW_DELETIONS=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)         DRY_RUN=true ;;
        --force)           FORCE=true ;;
        --include-repomap) INCLUDE_REPOMAP=true ;;
        --allow-deletions) ALLOW_DELETIONS=true ;;
        *) echo "Unknown flag: $arg"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Collect files under a directory, excluding .claude-plugin/ and *.local.md
list_files() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then return; fi
    find "$dir" -type f \
        ! -path "*/.claude-plugin/*" \
        ! -name "*.local.md" \
        | sed "s|^$dir/||" \
        | sort
}

# ---------------------------------------------------------------------------
# Build plan
# ---------------------------------------------------------------------------

declare -a NEW_FILES=()
declare -a MODIFIED_FILES=()
declare -a DELETED_FILES=()
declare -a UNKNOWN_FILES=()
UNCHANGED_COUNT=0

for plugin in "${PLUGINS[@]}"; do
    private_dir="$PRIVATE_ROOT/plugins/oduffy-custom/$plugin"
    public_dir="$PUBLIC_ROOT/plugins/$plugin"

    private_files=$(list_files "$private_dir")
    public_files=$(list_files "$public_dir")

    # Files in private
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        if [[ ! -f "$public_dir/$f" ]]; then
            NEW_FILES+=("$plugin/$f")
        elif ! diff -q "$private_dir/$f" "$public_dir/$f" &>/dev/null; then
            MODIFIED_FILES+=("$plugin/$f")
        else
            ((UNCHANGED_COUNT++)) || true
        fi
    done <<< "$private_files"

    # Files in public but not private
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        if [[ ! -f "$private_dir/$f" ]]; then
            if $ALLOW_DELETIONS; then
                DELETED_FILES+=("$plugin/$f")
            else
                UNKNOWN_FILES+=("$plugin/$f")
            fi
        fi
    done <<< "$public_files"
done

# Repomap entries
declare -a REPOMAP_NEW=()
declare -a REPOMAP_MODIFIED=()
if $INCLUDE_REPOMAP; then
    private_rm="$PRIVATE_ROOT/.github/scripts"
    public_rm="$PUBLIC_ROOT/.github/scripts"
    repomap_candidates=(generate-repomap.py requirements-repomap.txt)
    # Add .scm files dynamically
    if [[ -d "$private_rm/treesitter-queries" ]]; then
        while IFS= read -r scm; do
            repomap_candidates+=("treesitter-queries/$(basename "$scm")")
        done < <(find "$private_rm/treesitter-queries" -name "*.scm" | sort)
    fi
    for f in "${repomap_candidates[@]}"; do
        if [[ ! -f "$public_rm/$f" ]]; then
            REPOMAP_NEW+=(".github/scripts/$f")
        elif ! diff -q "$private_rm/$f" "$public_rm/$f" &>/dev/null; then
            REPOMAP_MODIFIED+=(".github/scripts/$f")
        else
            ((UNCHANGED_COUNT++)) || true
        fi
    done
fi

# ---------------------------------------------------------------------------
# Display plan
# ---------------------------------------------------------------------------

echo ""
echo "Sync plan: $PRIVATE_ROOT/plugins/oduffy-custom/ → $PUBLIC_ROOT/plugins/"
echo "────────────────────────────────────────────────────────────"

for f in "${NEW_FILES[@]+"${NEW_FILES[@]}"}";      do echo "  + $f"; done
for f in "${MODIFIED_FILES[@]+"${MODIFIED_FILES[@]}"}"; do echo "  ~ $f"; done
for f in "${DELETED_FILES[@]+"${DELETED_FILES[@]}"}";  do echo "  - $f"; done
for f in "${UNKNOWN_FILES[@]+"${UNKNOWN_FILES[@]}"}";  do echo "  ? $f  (public-only; preserved — use --allow-deletions to remove)"; done
for f in "${REPOMAP_NEW[@]+"${REPOMAP_NEW[@]}"}";      do echo "  + $f"; done
for f in "${REPOMAP_MODIFIED[@]+"${REPOMAP_MODIFIED[@]}"}"; do echo "  ~ $f"; done

echo "  = $UNCHANGED_COUNT unchanged file(s)"
echo ""

TOTAL_CHANGES=$(( ${#NEW_FILES[@]} + ${#MODIFIED_FILES[@]} + ${#DELETED_FILES[@]} + ${#REPOMAP_NEW[@]} + ${#REPOMAP_MODIFIED[@]} ))

if [[ $TOTAL_CHANGES -eq 0 ]]; then
    echo "Nothing to sync."
    exit 0
fi

$DRY_RUN && { echo "(dry-run — exiting without changes)"; exit 0; }

# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------

if ! $FORCE; then
    read -p "Apply $TOTAL_CHANGES change(s)? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# Apply changes
# ---------------------------------------------------------------------------

declare -a COPIED_FILES=()

copy_and_rewrite() {
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    if [[ "$dst" == *.md ]]; then
        # sed -i syntax differs: macOS requires '' arg, Linux/Git Bash do not
        local sed_i=(-i)
        [[ "$(uname)" == "Darwin" ]] && sed_i=(-i '')
        sed "${sed_i[@]}" 's|plugins/oduffy-custom/|plugins/|g' "$dst"
        sed "${sed_i[@]}" 's|oduffy-custom|coordinator-claude|g' "$dst"
    fi
    COPIED_FILES+=("$dst")
}

for entry in "${NEW_FILES[@]+"${NEW_FILES[@]}"}" "${MODIFIED_FILES[@]+"${MODIFIED_FILES[@]}"}"; do
    plugin="${entry%%/*}"
    rel="${entry#*/}"
    src="$PRIVATE_ROOT/plugins/oduffy-custom/$plugin/$rel"
    dst="$PUBLIC_ROOT/plugins/$plugin/$rel"
    echo "  copying $entry"
    copy_and_rewrite "$src" "$dst"
done

for entry in "${DELETED_FILES[@]+"${DELETED_FILES[@]}"}"; do
    dst="$PUBLIC_ROOT/plugins/${entry}"
    echo "  deleting $entry"
    rm -f "$dst"
done

for entry in "${REPOMAP_NEW[@]+"${REPOMAP_NEW[@]}"}" "${REPOMAP_MODIFIED[@]+"${REPOMAP_MODIFIED[@]}"}"; do
    rel="${entry#.github/scripts/}"
    src="$PRIVATE_ROOT/.github/scripts/$rel"
    dst="$PUBLIC_ROOT/.github/scripts/$rel"
    echo "  copying $entry"
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    COPIED_FILES+=("$dst")
done

echo ""
echo "Sync complete."

# ---------------------------------------------------------------------------
# Personal data audit
# ---------------------------------------------------------------------------

if [[ ${#COPIED_FILES[@]} -eq 0 ]]; then exit 0; fi

echo ""
echo "Personal data audit..."
echo "────────────────────────────────────────────────────────────"

REVIEW_FOUND=false

# perl_match PATTERN FILE — portable grep -P alternative (macOS BSD grep lacks -P)
perl_match() { perl -ne "\$f=1 if /$1/; END{exit !\$f}" "$2" 2>/dev/null; }
perl_any()   { perl -ne "print if /$1/" "$2" 2>/dev/null; }

for f in "${COPIED_FILES[@]}"; do
    for pat in "${REVIEW_PATTERNS[@]}"; do
        if perl_match "$pat" "$f"; then
            echo "  REVIEW  [$pat]  $f"
            REVIEW_FOUND=true
        fi
    done
    # Bare `oduffy` not in an expected context (oduffy-delphi or O'Duffy)
    if perl_match '\boduffy\b' "$f"; then
        if perl_any '\boduffy\b' "$f" | perl -ne "\$f=1 if !/oduffy-delphi|O'Duffy/; END{exit !\$f}"; then
            echo "  REVIEW  [bare oduffy]  $f"
            REVIEW_FOUND=true
        fi
    fi
    # `striker` not in a branch-example context (work/striker/)
    if perl_match '\bstriker\b' "$f"; then
        if perl_any '\bstriker\b' "$f" | perl -ne '$f=1 if !/work\/striker\//; END{exit !$f}'; then
            echo "  REVIEW  [striker outside branch example]  $f"
            REVIEW_FOUND=true
        fi
    fi
done

if $REVIEW_FOUND; then
    echo ""
    echo "REVIEW items found — inspect the files above before publishing."
    exit 1
else
    echo "  Clean — no personal data patterns found."
fi
