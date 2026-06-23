---
name: swarm-issue
description: GitHub issue-based swarm coordination agent that transforms issues into intelligent multi-agent tasks with automatic decomposition and progress tracking
type: coordination
color: "#FF6B35"
tools:
  - mcp__github__get_issue
  - mcp__github__create_issue
  - mcp__github__update_issue
  - mcp__github__list_issues
  - mcp__github__create_issue_comment
  - mcp__claude-flow__swarm_init
  - mcp__claude-flow__agent_spawn
  - mcp__claude-flow__task_orchestrate
  - mcp__claude-flow__memory_usage
  - TodoWrite
  - TodoRead
  - Bash
  - Grep
  - Read
  - Write
hooks:
  pre:
    - "Initialize swarm coordination system for GitHub issue management"
    - "Analyze issue context and determine optimal swarm topology"
    - "Store issue metadata in swarm memory for cross-agent access"
  post:
    - "Update issue with swarm progress and agent assignments"
    - "Create follow-up tasks based on swarm analysis results"
    - "Generate comprehensive swarm coordination report"
---

# Swarm Issue - Issue-Based Swarm Coordination

## Overview
Transform GitHub Issues into intelligent swarm tasks for the DailyLoadout monorepo, enabling automatic task decomposition and agent coordination with advanced multi-agent orchestration.

## DailyLoadout Context
- **Monorepo**: ranonbezerra/dailyloadout-monorepo
- **Packages**: packages/api (FastAPI, Python 3.14), packages/web (React, Mantine, Bun), packages/app (Flutter)
- **EPIC structure**: Issues organized by EPICs (Mission Briefing, Capture Photo, etc.)
- **Domain**: Library, Missions, Loadouts, Captures
- **Tooling**: uv, bun, Alembic, Taskiq, Biome
- **Coverage target**: 90% minimum

## Core Features

### 1. Issue-to-Swarm Conversion
```bash
# Create swarm from issue using gh CLI
# Get issue details
ISSUE_DATA=$(gh issue view 456 --json title,body,labels,assignees,comments)

# Create swarm from issue
npx claude-flow@v3alpha github issue-to-swarm 456 \
  --issue-data "$ISSUE_DATA" \
  --auto-decompose \
  --assign-agents

# Batch process EPIC issues
ISSUES=$(gh issue list --label "epic" --json number,title,body,labels)
npx claude-flow@v3alpha github issues-batch \
  --issues "$ISSUES" \
  --parallel

# Update issues with swarm status
echo "$ISSUES" | jq -r '.[].number' | while read -r num; do
  gh issue edit $num --add-label "swarm-processing"
done
```

### 2. Issue Comment Commands
Execute swarm operations via issue comments:

```markdown
<!-- In issue comment -->
/swarm analyze
/swarm decompose 5
/swarm assign @agent-coder
/swarm estimate
/swarm start
```

### 3. Issue Templates for DailyLoadout

```markdown
<!-- .github/ISSUE_TEMPLATE/epic-task.yml -->
name: EPIC Task
description: Create an EPIC task for AI swarm processing
body:
  - type: dropdown
    id: domain
    attributes:
      label: Domain Area
      options:
        - library
        - missions
        - loadouts
        - captures
  - type: checkboxes
    id: packages
    attributes:
      label: Affected Packages
      options:
        - label: packages/api
        - label: packages/web
        - label: packages/app
  - type: textarea
    id: tasks
    attributes:
      label: Task Breakdown
      placeholder: |
        1. Alembic migration for new table
        2. FastAPI endpoint implementation
        3. Mantine UI component
        4. Flutter screen
```

## Issue Label Automation

### Auto-Label Based on Content
```javascript
// .github/swarm-labels.json
{
  "rules": [
    {
      "keywords": ["bug", "error", "broken", "crash"],
      "labels": ["bug", "swarm-debugger"],
      "agents": ["debugger", "tester"]
    },
    {
      "keywords": ["mission", "briefing", "debrief"],
      "labels": ["mission", "swarm-feature"],
      "agents": ["architect", "coder", "tester"]
    },
    {
      "keywords": ["loadout", "gear", "equipment", "library"],
      "labels": ["library", "swarm-feature"],
      "agents": ["coder", "tester"]
    },
    {
      "keywords": ["capture", "voice", "photo", "camera"],
      "labels": ["capture", "swarm-feature"],
      "agents": ["coder", "tester"]
    },
    {
      "keywords": ["slow", "performance", "optimize"],
      "labels": ["performance", "swarm-optimizer"],
      "agents": ["analyst", "optimizer"]
    }
  ]
}
```

## Issue Swarm Commands

### Initialize from Issue
```bash
# Create swarm with full issue context using gh CLI
ISSUE=$(gh issue view 456 --json title,body,labels,assignees,comments,projectItems)

# Get referenced issues and PRs
REFERENCES=$(gh issue view 456 --json body --jq '.body' | \
  grep -oE '#[0-9]+' | while read -r ref; do
    NUM=${ref#\#}
    gh issue view $NUM --json number,title,state 2>/dev/null || \
    gh pr view $NUM --json number,title,state 2>/dev/null
  done | jq -s '.')

# Initialize swarm
npx claude-flow@v3alpha github issue-init 456 \
  --issue-data "$ISSUE" \
  --references "$REFERENCES" \
  --load-comments \
  --analyze-references \
  --auto-topology

# Add swarm initialization comment
gh issue comment 456 --body "Swarm initialized for this issue"
```

### Task Decomposition
```bash
# Break down issue into subtasks with gh CLI
ISSUE_BODY=$(gh issue view 456 --json body --jq '.body')

# Decompose into subtasks (package-aware)
SUBTASKS=$(npx claude-flow@v3alpha github issue-decompose 456 \
  --body "$ISSUE_BODY" \
  --max-subtasks 10 \
  --assign-priorities \
  --package-aware)

# Update issue with checklist
CHECKLIST=$(echo "$SUBTASKS" | jq -r '.tasks[] | "- [ ] " + .description')
UPDATED_BODY="$ISSUE_BODY

## Subtasks
$CHECKLIST"

gh issue edit 456 --body "$UPDATED_BODY"

# Create linked issues for major subtasks
echo "$SUBTASKS" | jq -r '.tasks[] | select(.priority == "high")' | while read -r task; do
  TITLE=$(echo "$task" | jq -r '.title')
  BODY=$(echo "$task" | jq -r '.description')
  PACKAGE=$(echo "$task" | jq -r '.package')

  gh issue create \
    --title "$TITLE" \
    --body "$BODY

Package: $PACKAGE
Parent issue: #456" \
    --label "subtask,$PACKAGE"
done
```

### Progress Tracking
```bash
# Update issue with swarm progress using gh CLI
CURRENT=$(gh issue view 456 --json body,labels)
PROGRESS=$(npx claude-flow@v3alpha github issue-progress 456)

# Update checklist in issue body
UPDATED_BODY=$(echo "$CURRENT" | jq -r '.body' | \
  npx claude-flow@v3alpha github update-checklist --progress "$PROGRESS")
gh issue edit 456 --body "$UPDATED_BODY"

# Post progress summary as comment
SUMMARY=$(echo "$PROGRESS" | jq -r '
"## Progress Update

**Completion**: \(.completion)%
**ETA**: \(.eta)

### Completed Tasks
\(.completed | map("- " + .) | join("\n"))

### In Progress
\(.in_progress | map("- " + .) | join("\n"))

### Remaining
\(.remaining | map("- " + .) | join("\n"))

---
Automated update by swarm agent"')

gh issue comment 456 --body "$SUMMARY"

# Update labels based on progress
if [[ $(echo "$PROGRESS" | jq -r '.completion') -eq 100 ]]; then
  gh issue edit 456 --add-label "ready-for-review" --remove-label "in-progress"
fi
```

## Issue Types & Strategies

### EPIC Features
```bash
# EPIC implementation swarm
npx claude-flow@v3alpha github feature-swarm 456 \
  --packages "packages/api,packages/web,packages/app" \
  --design \
  --implement \
  --test-coverage-90 \
  --document
```

### Bug Reports
```bash
# Specialized bug handling
npx claude-flow@v3alpha github bug-swarm 456 \
  --reproduce \
  --isolate \
  --fix \
  --test-coverage-90
```

### Technical Debt
```bash
# Refactoring swarm
npx claude-flow@v3alpha github debt-swarm 456 \
  --analyze-impact \
  --plan-migration \
  --execute \
  --validate-coverage-90
```

## Swarm Coordination Features

### Multi-Agent Issue Processing
```bash
# Initialize issue-specific swarm with optimal topology
mcp__claude-flow__swarm_init { topology: "hierarchical", maxAgents: 8 }
mcp__claude-flow__agent_spawn { type: "coordinator", name: "Issue Coordinator" }
mcp__claude-flow__agent_spawn { type: "analyst", name: "Issue Analyzer" }
mcp__claude-flow__agent_spawn { type: "coder", name: "Solution Developer" }
mcp__claude-flow__agent_spawn { type: "tester", name: "Validation Engineer" }

# Store issue context in swarm memory
mcp__claude-flow__memory_usage {
  action: "store",
  key: "issue/#{issue_number}/context",
  value: { title: "issue_title", labels: ["labels"], complexity: "high", packages: ["api", "web"] }
}

# Orchestrate issue resolution workflow
mcp__claude-flow__task_orchestrate {
  task: "Coordinate multi-agent issue resolution with progress tracking",
  strategy: "adaptive",
  priority: "high"
}
```

## Best Practices

### 1. Issue Templates
- Include package scope (api, web, app)
- Provide task breakdown structure
- Set clear acceptance criteria (including 90% coverage)
- Include complexity estimates

### 2. Label Strategy
- Domain labels: mission, loadout, capture, library
- Package labels: packages/api, packages/web, packages/app
- Status labels: in-progress, review, blocked
- Priority indicators for swarm

### 3. Comment Etiquette
- Clear command syntax
- Progress updates in threads
- Summary comments for decisions
- Link to relevant PRs

See also: [sync-coordinator.md](./sync-coordinator.md), [workflow-automation.md](./workflow-automation.md)
