#!/bin/bash
# PreToolUse hook: nudge the EM to delegate holodeck MCP tool calls to domain agents.
# Uses "allow" — doesn't block, but injects a strong reminder that the EM should
# be orchestrating, not typing Python or calling MCP tools directly.

cat << 'HOOK_OUTPUT'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "DELEGATION REQUIRED: You are about to call a holodeck MCP tool directly. The EM orchestrates — domain agents execute. Use the dedicated holodeck infrastructure:\n\n- World building / level design / actor placement → Agent(subagent_type='holodeck-control:ue-world-builder')\n- Asset creation / Blueprint editing / materials → Agent(subagent_type='holodeck-control:ue-asset-author')\n- Gameplay systems / abilities / AI / game mode → Agent(subagent_type='holodeck-control:ue-gameplay-engineer')\n- Project config / plugins / build / packaging → Agent(subagent_type='holodeck-control:ue-infra-engineer')\n- For multi-domain tasks, decompose and dispatch domain agents sequentially with verification between steps.\n- UE documentation lookup → Agent(subagent_type='game-dev:sid-game-dev') or /ue-lookup command\n- Python script execution in editor → Agent(subagent_type='holodeck-docs:ue-python-executor') or /run-python command\n- Blueprint inspection → Agent(subagent_type='game-dev:ue-blueprint-inspector')\n\nDo NOT call MCP tools directly or spin up a generic Agent — use the typed subagent_type to get the right agent with the right tools and system prompt.\n\nOnly proceed with direct MCP calls if: (1) you are verifying an agent's output with a single quick inspection, or (2) the operation is trivially simple and dispatching an agent would be pure overhead."
  }
}
HOOK_OUTPUT
