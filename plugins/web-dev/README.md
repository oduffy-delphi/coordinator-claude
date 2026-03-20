# web-dev

Web development domain plugin. Enable for frontend, full-stack, and UI-focused projects.

## Components

**Agents:**
- `pali-frontend-reviewer` (Opus) — Frontend code reviewer focused on design system adherence, token validation, component patterns, and CSS architecture. Pragmatic — "close enough" to design specs is often correct when it means using standard utilities.
- `fru-ux-reviewer` (Opus) — UX flow reviewer focused on trust signals, clarity assessment, and intuitive flow design. Reviews user-facing features for usability.

**Routing:** Registers Pali and Fru for web dev signals with Patrik (coordinator) as backstop.

## Enabling

Add to your project's `.claude/coordinator.local.md`:

```yaml
---
project_type: web
---
```

Or explicitly list reviewers:

```yaml
---
active_reviewers:
  - patrik
  - pali
  - fru
---
```

## Review Sequencing

For web features, the typical review sequence is:
1. **Pali** (domain) — design system adherence, token validation
2. **Patrik** (generalist) — architecture, code quality

For UX-heavy changes, Fru reviews the flow before Pali reviews the implementation.
