#!/usr/bin/env bash
# rename-personas.sh — Renames persona display names across plugin prose files.
# Skips YAML frontmatter and filenames. Safe for multi-byte names (Zolí, Palí).
# Usage: rename-personas.sh [--dry-run] OLD NEW [OLD NEW ...]
# Example: rename-personas.sh Patrik "Alex" Zolí "Jordan"

set -euo pipefail

# ---------------------------------------------------------------------------
# Persona registry (for validation warnings)
# Name        | Plugin        | Agent File
# Patrik      | coordinator   | agents/patrik-code-review.md
# Zolí        | coordinator   | agents/zoli-ambition-advocate.md
# Sid         | game-dev      | agents/sid-game-dev.md
# Palí        | web-dev       | agents/pali-frontend-reviewer.md
# Fru         | web-dev       | agents/fru-ux-reviewer.md
# Camelia     | data-science  | agents/camelia-data-scientist.md
# ---------------------------------------------------------------------------
KNOWN_PERSONAS=("Patrik" "Zolí" "Sid" "Palí" "Fru" "Camelia")

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGINS_DIR="$REPO_ROOT/plugins"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  shift
fi

if (( $# % 2 != 0 )); then
  echo "Error: arguments after [--dry-run] must be OLD NEW pairs." >&2
  echo "Usage: $(basename "$0") [--dry-run] OLD NEW [OLD NEW ...]" >&2
  exit 1
fi

if (( $# == 0 )); then
  echo "Error: no OLD NEW pairs provided." >&2
  exit 1
fi

declare -a OLDS=()
declare -a NEWS=()
while (( $# > 0 )); do
  old="$1"; new="$2"; shift 2
  OLDS+=("$old")
  NEWS+=("$new")
  # Warn if OLD is not a known persona
  known=false
  for p in "${KNOWN_PERSONAS[@]}"; do
    [[ "$p" == "$old" ]] && known=true && break
  done
  if ! $known; then
    echo "Warning: '$old' is not a known persona name (proceeding anyway)." >&2
  fi
done

# ---------------------------------------------------------------------------
# Frontmatter-safe replacement using perl with full Unicode support.
# Rewrites the file in-place; only touches the body, not the YAML frontmatter.
# Handles both LF and CRLF line endings (common on Windows/Git Bash).
# ---------------------------------------------------------------------------
replace_in_prose() {
  local old="$1" new="$2" file="$3"
  # -0777 slurps whole file; -i -pe enables in-place edit with implicit $_ loop.
  # No -CSD: byte-mode matching is correct here — shell expands $old as UTF-8 bytes,
  # and file bytes are also UTF-8. -CSD causes mismatch with multi-byte characters.
  perl -0777 -i -pe "
    if (/\A---\r?\n(.*?\r?\n)---\r?\n(.*)/s) {
      my (\$fm, \$body) = (\$1, \$2);
      \$body =~ s/\Q$old\E/$new/g;
      \$_ = \"---\\n\$fm---\\n\$body\";
    } else {
      s/\Q$old\E/$new/g;
    }
  " "$file"
}

# Count prose occurrences (respecting frontmatter) without modifying the file.
count_prose_matches() {
  local old="$1" file="$2"
  # -0777 slurps whole file; -ne enables implicit $_ loop required for slurping.
  # No -CSD: same rationale as replace_in_prose.
  perl -0777 -ne "
    my \$count = 0;
    if (/\A---\r?\n(.*?\r?\n)---\r?\n(.*)/s) {
      my \$body = \$2;
      \$count++ while \$body =~ /\Q$old\E/g;
    } else {
      \$count++ while /\Q$old\E/g;
    }
    print \$count;
  " "$file"
}

# ---------------------------------------------------------------------------
# Collect target files
# ---------------------------------------------------------------------------
mapfile -d '' FILES < <(find "$PLUGINS_DIR" \( -name "*.md" -o -name "*.sh" \) -print0)

# ---------------------------------------------------------------------------
# Dry-run: report counts, no modifications
# ---------------------------------------------------------------------------
if $DRY_RUN; then
  echo "Dry-run mode — no files will be modified."
  echo ""
  for i in "${!OLDS[@]}"; do
    old="${OLDS[$i]}"; new="${NEWS[$i]}"
    total_replacements=0; total_files=0
    for file in "${FILES[@]}"; do
      count="$(count_prose_matches "$old" "$file")"
      if (( count > 0 )); then
        echo "  [${old} → ${new}] $file: $count match(es)"
        (( total_replacements += count )) || true
        (( total_files += 1 )) || true
      fi
    done
    echo "  ${old} → ${new}: $total_replacements replacement(s) across $total_files file(s)"
    echo ""
  done
  exit 0
fi

# ---------------------------------------------------------------------------
# Live run: apply replacements and report summary
# ---------------------------------------------------------------------------
declare -A PAIR_REPLACEMENTS=()
declare -A PAIR_FILES=()
for i in "${!OLDS[@]}"; do
  PAIR_REPLACEMENTS["${OLDS[$i]}"]=0
  PAIR_FILES["${OLDS[$i]}"]=0
done

total_files_modified=0

for file in "${FILES[@]}"; do
  file_modified=false
  for i in "${!OLDS[@]}"; do
    old="${OLDS[$i]}"; new="${NEWS[$i]}"
    count="$(count_prose_matches "$old" "$file")"
    if (( count > 0 )); then
      replace_in_prose "$old" "$new" "$file"
      PAIR_REPLACEMENTS["$old"]=$(( PAIR_REPLACEMENTS["$old"] + count ))
      PAIR_FILES["$old"]=$(( PAIR_FILES["$old"] + 1 ))
      file_modified=true
    fi
  done
  if $file_modified; then
    (( total_files_modified += 1 )) || true
  fi
done

echo "Persona renames:"
for i in "${!OLDS[@]}"; do
  old="${OLDS[$i]}"; new="${NEWS[$i]}"
  echo "  ${old} → ${new}: ${PAIR_REPLACEMENTS[$old]} replacements across ${PAIR_FILES[$old]} files"
done
echo ""
echo "Total files modified: $total_files_modified"
