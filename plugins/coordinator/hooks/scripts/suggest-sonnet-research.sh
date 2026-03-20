#!/bin/bash
# PreToolUse hook: remind Opus to consider Sonnet delegation for web research.
# Uses "allow" — never blocks, just injects a nudge into Claude's context.
# Claude exercises judgment: single URL from the user = DIY. Multi-query
# research or code-writing = consider delegating to Sonnet subagent.

cat << 'HOOK_OUTPUT'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "DELEGATION CHECK: You're about to do web research as Opus. Ask yourself: is this a single page the user linked you to, or a research task involving multiple searches? For single lookups, proceed — dispatching a subagent costs more in overhead than it saves. For multi-query research or bulk documentation reading, delegate to a Sonnet subagent (model: 'sonnet') to fetch, summarize, and return a tight result. Same principle applies to code implementation: if you're about to write boilerplate or mechanical code, consider whether an executor agent should be doing the typing."
  }
}
HOOK_OUTPUT
