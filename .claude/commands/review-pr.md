# /review-pr

Analyze the PR diff and provide a structured code review.

## Usage
```
/review-pr [PR number]
```

## Execution

```bash
gh pr diff $ARGUMENTS
gh pr view $ARGUMENTS --json title,body,author,additions,deletions,files
```

If no arguments, use the PR associated with the current branch:
```bash
gh pr diff
gh pr view --json title,body,author,additions,deletions,files
```

## Review checklist

### Architecture and patterns
- [ ] No business logic in router
- [ ] No direct DB access in service
- [ ] Layer discipline respected (Router -> Service -> Repository -> Model)
- [ ] Pydantic v2 schemas with ConfigDict

### LLM integration
- [ ] LLM outputs validated (anti-hallucination check)
- [ ] Prompt templates in `prompts/*.j2`
- [ ] Graceful fallback on LLM failure
- [ ] No sensitive data sent to LLM prompts

### Security
- [ ] No hardcoded secrets
- [ ] JWT validated before operations
- [ ] User isolation (no cross-user data access)
- [ ] Input validated at API boundary

### Quality
- [ ] Tests covering new scenarios
- [ ] `ruff` + `mypy` clean
- [ ] `biome` clean (if web changes)
- [ ] No `print()` debug statements
- [ ] No unused imports
- [ ] Coverage >= 90%

### Data integrity
- [ ] Migrations have proper downgrade paths
- [ ] Foreign keys and indexes present
- [ ] One-active-mission constraint respected
- [ ] Capture status transitions valid

## Review format

```markdown
## Code Review — [PR title]

### Summary
[What this PR does — 2-3 lines]

### Critical issues (block merge)
- [description + file:line + suggested fix]

### Warnings (should fix)
- [description + file:line]

### Suggestions (consider improving)
- [description]

### Verdict
Approved / Approved with reservations / Blocked
```
