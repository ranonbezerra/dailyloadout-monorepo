# /new-issue

Create a new issue on GitHub or Linear.

## Usage
```
/new-issue
/new-issue --linear
/new-issue --github
```

If no flag, ask the user which tracker to use.

## Steps

### 1. Collect information
Ask the user:
- **Title**: brief description (max 80 chars)
- **Type**: feature | bug | chore | refactor | docs | test
- **System**: api | web | app | infra
- **Description**: what needs to be done and why
- **Acceptance criteria**: list of verifiable items
- **Priority**: urgent | high | medium | low

### 2a. Create GitHub issue

```bash
gh issue create \
  --title "<type>: <title>" \
  --body "$(cat <<'EOF'
## Context
[description]

## Acceptance criteria
- [ ] item 1
- [ ] item 2

## System affected
[api | web | app | infra]
EOF
)" \
  --label "<type>"
```

### 2b. Create Linear issue

- `mcp__linear-server__list_teams` -> get DailyLoadout team
- `mcp__linear-server__list_projects` -> get correct project based on system
- `mcp__linear-server__list_issue_labels` -> list available labels
- `mcp__linear-server__save_issue` with:

```json
{
  "title": "Title",
  "description": "## Context\n[context]\n\n## Acceptance criteria\n- [ ] item 1\n- [ ] item 2\n\n## System affected\n[api | web | app | infra]",
  "teamId": "<team-id>",
  "projectId": "<project-id>",
  "priority": 2
}
```

### 3. Confirm

```
## Issue created!

**ID:** #42 / DL-24
**Title:** [title]
**URL:** [url]

To start working: /start #42 (or /start DL-24)
```
