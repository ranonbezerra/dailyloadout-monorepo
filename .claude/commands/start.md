# /start

Begin work on an issue (GitHub or Linear): read the issue, create a branch, and generate an implementation plan.

## Usage
```
/start <issue-ref>
```
- GitHub: `/start #42` or `/start 42`
- Linear: `/start DL-24` or `/start DL-24`
- No argument: detect from current branch name

## Steps

### 1. Identify the issue
- If `$ARGUMENTS` matches `DL-\d+` pattern -> Linear issue
- If `$ARGUMENTS` is a number or `#\d+` -> GitHub issue
- If not provided, run `git branch --show-current` and extract the identifier
- If neither works, ask the user

### 2. Read the issue

**GitHub:**
```bash
gh issue view <number> --json title,body,labels,state,comments
```

**Linear:**
Execute in parallel:
- `mcp__linear-server__get_issue` with the identifier -> read title, description, state, labels, project, sub-issues
- `mcp__linear-server__list_comments` -> read all comments (may contain technical decisions)
- If parent issue exists, read it too
- If related issues are mentioned, read them for context

### 3. Analyze the codebase
Based on the issue, identify and read the relevant files:
- Use Glob to find files by pattern
- Use Grep to search for references to entities mentioned in the issue
- Read `CLAUDE.md`, `ARCHITECTURE.md`, and `PRODUCT.md` sections relevant to the feature
- Identify existing patterns that must be followed

### 4. Update issue status (Linear only)
- `mcp__linear-server__list_issue_statuses` -> get "In Progress" status ID
- `mcp__linear-server__save_issue` -> update state

### 5. Create the branch
Determine the correct prefix:
- `feat/` -> new functionality
- `fix/` -> bug fix
- `chore/` -> maintenance, config
- `refactor/` -> refactoring without new feature
- `test/` -> tests only
- `docs/` -> documentation only

```bash
git checkout main
git pull origin main
git checkout -b <prefix>/<issue-id>-short-description
```

### 6. Create implementation plan

Based on everything read:

```markdown
## Implementation Plan — [ID] Title

### Context
[What needs to be done and why — 3-5 lines]

### Systems affected
- **packages/api**: [modules, endpoints, migrations, tasks]
- **packages/web**: [pages, components, hooks]
- **packages/app**: [screens, BLoCs, repositories]
- **Database**: [schema changes]

### Implementation steps

#### Step 1: [Name]
- File: `path/to/file.py`
- What to do: [precise description]
- Pattern to follow: [reference to existing code]

#### Step N: Tests
- Create/update tests for modified services
- Coverage target: >= 90%

### Definition of Done
- [ ] All acceptance criteria met
- [ ] pytest passing
- [ ] ruff + mypy clean
- [ ] biome clean (if web changes)
- [ ] flutter analyze clean (if app changes)
- [ ] Alembic migration created (if schema change)
```

### 7. Confirm to user

```
## Ready to start [ID]

**Branch:** feat/<id>-description
**Issue:** <title>
**Tracker:** GitHub / Linear

[Summary of the plan with the N main steps]
```

## Important rules
- **Read the issue comments** — they often contain technical decisions
- **Follow codebase patterns** — never invent new patterns without justification
- **Branch always from updated main** — `git pull` before creating
- **Plan before code** — this command creates the plan; implementation comes after
- **Update Linear status** — if using Linear, always set to In Progress
