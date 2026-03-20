#!/bin/bash
# coordinator-claude installation helper
#
# This script installs coordinator-claude plugins to your Claude Code plugins directory.
# It handles the copy step only — you still need to register plugins in JSON config files.
# See docs/getting-started.md for the full installation guide.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGINS_SOURCE="$REPO_ROOT/plugins"
CLAUDE_DIR="${HOME}/.claude"
PLUGINS_TARGET="$CLAUDE_DIR/plugins/coordinator-claude"

echo "coordinator-claude installer"
echo "========================"
echo ""

# Check Claude Code is installed
if ! command -v claude &>/dev/null; then
    echo "ERROR: Claude Code CLI not found."
    echo "Install it from: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi

echo "Claude Code: found"
echo "Install source: $PLUGINS_SOURCE"
echo "Install target: $PLUGINS_TARGET"
echo ""

# Confirm before proceeding
read -p "Proceed with installation? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Create target directory
mkdir -p "$PLUGINS_TARGET"

# Copy plugins
echo "Copying plugins..."
cp -r "$PLUGINS_SOURCE/"* "$PLUGINS_TARGET/"
echo "  OK: plugins copied to $PLUGINS_TARGET"

echo ""
echo "Installation complete!"
echo ""
echo "NEXT STEPS (manual):"
echo ""
echo "1. Register plugins in ~/.claude/plugins/installed_plugins.json"
echo "   See docs/getting-started.md for the exact JSON to add."
echo ""
echo "2. Enable plugins in ~/.claude/settings.json:"
echo "   Add to enabledPlugins:"
echo '   "coordinator@coordinator-claude": true'
echo '   "web-dev@coordinator-claude": true'
echo '   "data-science@coordinator-claude": true'
echo '   "game-dev@coordinator-claude": false  # enable only for game dev projects'
echo ""
echo "3. Restart Claude Code"
echo ""
echo "4. Run /session-start to verify the plugins loaded"
echo ""
echo "Full guide: docs/getting-started.md"
