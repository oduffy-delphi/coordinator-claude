# Getting Started with coordinator-em

This guide walks you through installing the coordinator-em plugins and running your first session.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed and authenticated
- A Claude API key or Claude Pro/Team subscription

## Installation

### Step 1: Clone the repository

```bash
git clone https://github.com/oduffy-delphi/coordinator-em.git
cd coordinator-em
```

### Step 2: Create the plugins directory

```bash
mkdir -p ~/.claude/plugins/coordinator-em
```

### Step 3: Copy plugins

```bash
cp -r plugins/* ~/.claude/plugins/coordinator-em/
```

### Step 4: Register the marketplace

Tell Claude Code where to find the plugins by adding an entry to `~/.claude/plugins/known_marketplaces.json`. Create the file if it doesn't exist:

```json
{
  "marketplaces": [
    {
      "name": "coordinator-em",
      "path": "/home/{USERNAME}/.claude/plugins/coordinator-em"
    }
  ]
}
```

Replace `{USERNAME}` with your actual username. On macOS, your home directory is typically `/Users/{USERNAME}`.

### Step 5: Register plugins in installed_plugins.json

Create or edit `~/.claude/plugins/installed_plugins.json`:

```json
{
  "plugins": {
    "coordinator@coordinator-em": [{
      "scope": "user",
      "installPath": "/home/{USERNAME}/.claude/plugins/coordinator-em/coordinator",
      "version": "1.3.0",
      "installedAt": "2026-03-20T00:00:00Z",
      "lastUpdated": "2026-03-20T00:00:00Z"
    }],
    "web-dev@coordinator-em": [{
      "scope": "user",
      "installPath": "/home/{USERNAME}/.claude/plugins/coordinator-em/web-dev",
      "version": "1.3.0",
      "installedAt": "2026-03-20T00:00:00Z",
      "lastUpdated": "2026-03-20T00:00:00Z"
    }],
    "data-science@coordinator-em": [{
      "scope": "user",
      "installPath": "/home/{USERNAME}/.claude/plugins/coordinator-em/data-science",
      "version": "1.3.0",
      "installedAt": "2026-03-20T00:00:00Z",
      "lastUpdated": "2026-03-20T00:00:00Z"
    }],
    "game-dev@coordinator-em": [{
      "scope": "user",
      "installPath": "/home/{USERNAME}/.claude/plugins/coordinator-em/game-dev",
      "version": "1.3.0",
      "installedAt": "2026-03-20T00:00:00Z",
      "lastUpdated": "2026-03-20T00:00:00Z"
    }]
  }
}
```

> **Note:** `game-dev` is included but disabled by default (see Step 6). Install it but leave it disabled unless you're working on Unreal Engine projects.

### Step 6: Enable plugins in settings.json

Create or edit `~/.claude/settings.json` to enable the plugins:

```json
{
  "enabledPlugins": {
    "coordinator@coordinator-em": true,
    "web-dev@coordinator-em": true,
    "data-science@coordinator-em": true,
    "game-dev@coordinator-em": false
  },
  "extraKnownMarketplaces": [
    "/home/{USERNAME}/.claude/plugins/coordinator-em"
  ]
}
```

Enable `game-dev@coordinator-em` only if you're working on game development projects.

### Step 7: Restart Claude Code

Changes take effect on the next session start. Open a new terminal or restart Claude Code.

Verify by running `/reload-plugins` — you should see the coordinator components (agents, commands, skills) in the count.

## First Run

Start a Claude Code session in any project directory and run:

```
/session-start
```

This orients the session: loads orientation documents, surfaces pending work, and sets up the EM operating mode.

### What to expect

On first run, `/session-start` will:
1. Check for orientation documents (repo map, DIRECTORY.md)
2. Report any pending handoffs
3. Set the EM role and load pipeline awareness
4. Offer to help you choose what to work on

If this is a brand new project, run `/project-onboarding` to bootstrap the tracking infrastructure (tracker, tasks directory, archive).

## Per-Project Configuration

Create `.claude/coordinator.local.md` in your project root to configure which domain plugins activate:

```yaml
---
project_type: web
---
```

Valid `project_type` values:
- `web` — activates Palí (frontend) + Fru (UX) reviewers
- `data-science` — activates Camelia (ML/data) reviewer
- `game` — activates Sid (Unreal Engine) reviewer
- `pure-docs` — documentation projects, coordinator only

Without a config file, the coordinator defaults to core-only mode (Patrik + Zolí universal reviewers).

You can also explicitly list reviewers:

```yaml
---
active_reviewers:
  - patrik
  - sid
  - camelia
---
```

## Troubleshooting

### Plugins not showing as skills/commands

1. Check `enabledPlugins` in `settings.json` — must be `true`
2. Check `installed_plugins.json` — must have entry with correct `installPath`
3. Verify the install path exists and contains the plugin files
4. Restart Claude Code (changes take effect on next session)

### `claude plugin install` fails silently

This is a known issue with directory-based local marketplaces. Use the manual JSON entries described in Steps 5-6 instead.

### Plugin cache out of sync

If you edit plugin files and changes don't appear in sessions, the cache may be stale. Plugin cache lives at `~/.claude/plugins/cache/`. Deleting it forces a rebuild on next session start.

## Next Steps

- Read [docs/architecture.md](architecture.md) to understand how the system works
- Read [docs/customization.md](customization.md) to learn how to adapt personas and add skills
- Try `/review-dispatch` to route code to a reviewer
- Try `/deep-research` for multi-agent codebase or internet research
- Try `/delegate-execution` to dispatch an executor agent on a well-specified task
