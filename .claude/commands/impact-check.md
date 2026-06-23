# /impact-check

Analyze the impact of a change across all systems before implementing.

## Usage
```
/impact-check <description of change>
```

Example: `/impact-check add playtime tracking to missions`

## Steps

Use the Task tool to launch parallel searches:

```
Task("Explore packages/api: find all files related to: $ARGUMENTS")
Task("Explore packages/web: find all files related to: $ARGUMENTS")
```

### Impact analysis

Produce a report:

```markdown
## Impact Analysis — [Change]

### packages/api
**Files affected:**
- `core/{domain}/service.py` — [why]
- `core/{domain}/schemas.py` — [why]
- `infrastructure/db/models/{domain}.py` — [why]

**Migration needed:** yes/no
- If yes: describe columns/tables to add

**Endpoints affected:** [list]

**Tests to update:** [list]

**LLM integration impact:** [if affects prompts, validation, or extraction]

### packages/web
**Files affected:**
- `types/{domain}.ts` — [why]
- `hooks/use{Domain}.ts` — [why]
- `pages/{Domain}Page.tsx` — [why]

**API contract changes:** [new fields, changed types]

### packages/app (if applicable)
**Files affected:** [list or "no impact at this stage"]

### Background jobs impact
[Any Taskiq tasks affected or new tasks needed]

### Recommended implementation order
1. [first step]
2. [second step]
...

### Risks
- [risk 1]
- [risk 2]
```
