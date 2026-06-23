---
name: project-board-sync
description: Synchronize AI swarms with GitHub Projects for visual task management, progress tracking, and team coordination
type: coordination
color: "#A8E6CF"
tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - TodoWrite
  - mcp__claude-flow__swarm_init
  - mcp__claude-flow__agent_spawn
  - mcp__claude-flow__task_orchestrate
  - mcp__claude-flow__swarm_status
  - mcp__claude-flow__memory_usage
  - mcp__claude-flow__github_repo_analyze
  - mcp__claude-flow__github_pr_manage
  - mcp__claude-flow__github_issue_track
  - mcp__claude-flow__github_metrics
  - mcp__claude-flow__workflow_create
  - mcp__claude-flow__workflow_execute
hooks:
  pre:
    - "gh auth status || (echo 'GitHub CLI not authenticated' && exit 1)"
    - "gh project list --owner @me --limit 1 >/dev/null || echo 'No projects accessible'"
    - "git status --porcelain || echo 'Not in git repository'"
    - "gh api user | jq -r '.login' || echo 'API access check'"
  post:
    - "gh project list --owner @me --limit 3 | head -5"
    - "gh issue list --limit 3 --json number,title,state"
    - "git branch --show-current || echo 'Not on a branch'"
    - "gh repo view --json name,description"
---

# Project Board Sync - GitHub Projects Integration

## Overview
Synchronize AI swarms with GitHub Projects for visual task management, progress tracking, and team coordination for the DailyLoadout monorepo.

## DailyLoadout Context
- **Monorepo**: packages/api, packages/web, packages/app
- **EPIC tracking**: EPICs organized by feature area (Library, Missions, Loadouts, Captures)
- **Stack**: FastAPI (Python 3.14, uv), React+Mantine (Bun, Biome), Flutter
- **Coverage target**: 90% minimum

## Core Features

### 1. Board Initialization
```bash
# Connect swarm to GitHub Project using gh CLI
# Get project details
PROJECT_ID=$(gh project list --owner @me --format json | \
  jq -r '.projects[] | select(.title == "DailyLoadout Development") | .id')

# Initialize swarm with project
npx claude-flow@v3alpha github board-init \
  --project-id "$PROJECT_ID" \
  --sync-mode "bidirectional" \
  --create-views "swarm-status,package-workload,epic-progress"

# Create project fields for swarm tracking
gh project field-create $PROJECT_ID --owner @me \
  --name "Package" \
  --data-type "SINGLE_SELECT" \
  --single-select-options "packages/api,packages/web,packages/app"
```

### 2. Task Synchronization
```bash
# Sync swarm tasks with project cards
npx claude-flow@v3alpha github board-sync \
  --map-status '{
    "todo": "Backlog",
    "in_progress": "In Progress",
    "review": "Review",
    "done": "Done"
  }' \
  --auto-move-cards \
  --update-metadata
```

## Configuration

### Board Mapping Configuration
```yaml
# .github/board-sync.yml
version: 1
project:
  name: "DailyLoadout Development"
  number: 1

mapping:
  # Map swarm task status to board columns
  status:
    pending: "Backlog"
    assigned: "Ready"
    in_progress: "In Progress"
    review: "Review"
    completed: "Done"
    blocked: "Blocked"

  # Map agent types to labels
  agents:
    coder: "Development"
    tester: "Testing"
    analyst: "Analysis"
    designer: "Design"
    architect: "Architecture"

  # Map priority to project fields
  priority:
    critical: "Critical"
    high: "High"
    medium: "Medium"
    low: "Low"

  # DailyLoadout-specific fields
  fields:
    - name: "Package"
      type: select
      options: ["packages/api", "packages/web", "packages/app"]
    - name: "EPIC"
      type: select
      source: task.epic
    - name: "Coverage"
      type: number
      source: task.coveragePercent
    - name: "ETA"
      type: date
      source: task.estimatedCompletion
```

### View Configuration
```javascript
// Custom board views
{
  "views": [
    {
      "name": "EPIC Overview",
      "type": "board",
      "groupBy": "epic",
      "filters": ["is:open"],
      "sort": "priority:desc"
    },
    {
      "name": "Package Workload",
      "type": "table",
      "groupBy": "package",
      "columns": ["title", "status", "priority", "coverage", "eta"],
      "sort": "eta:asc"
    },
    {
      "name": "Sprint Progress",
      "type": "roadmap",
      "dateField": "eta",
      "groupBy": "milestone"
    }
  ]
}
```

## Automation Features

### 1. Auto-Assignment
```bash
# Automatically assign cards to agents
npx claude-flow@v3alpha github board-auto-assign \
  --strategy "load-balanced" \
  --consider "expertise,workload,availability" \
  --update-cards
```

### 2. Progress Tracking
```bash
# Track and visualize progress
npx claude-flow@v3alpha github board-progress \
  --show "burndown,velocity,cycle-time" \
  --time-period "sprint" \
  --export-metrics
```

### 3. Smart Card Movement
```bash
# Intelligent card state transitions
npx claude-flow@v3alpha github board-smart-move \
  --rules '{
    "auto-progress": "when:all-subtasks-done",
    "auto-review": "when:tests-pass-90-percent",
    "auto-done": "when:pr-merged"
  }'
```

## Board Commands

### Create Cards from EPIC Issues
```bash
# Convert EPIC issues to project cards using gh CLI
# List EPIC issues
ISSUES=$(gh issue list --label "epic" --json number,title,body)

# Add issues to project
echo "$ISSUES" | jq -r '.[].number' | while read -r issue; do
  gh project item-add $PROJECT_ID --owner @me --url "https://github.com/ranonbezerra/dailyloadout-monorepo/issues/$issue"
done

# Process with swarm
npx claude-flow@v3alpha github board-import-issues \
  --issues "$ISSUES" \
  --add-to-column "Backlog" \
  --parse-checklist \
  --assign-agents
```

## Visualization & Reporting

### Board Analytics
```bash
# Generate board analytics using gh CLI data
# Fetch project data
PROJECT_DATA=$(gh project item-list $PROJECT_ID --owner @me --format json)

# Get issue metrics
ISSUE_METRICS=$(echo "$PROJECT_DATA" | jq -r '.items[] | select(.content.type == "Issue")' | \
  while read -r item; do
    ISSUE_NUM=$(echo "$item" | jq -r '.content.number')
    gh issue view $ISSUE_NUM --json createdAt,closedAt,labels,assignees
  done)

# Generate analytics with swarm
npx claude-flow@v3alpha github board-analytics \
  --project-data "$PROJECT_DATA" \
  --issue-metrics "$ISSUE_METRICS" \
  --metrics "throughput,cycle-time,wip,coverage-compliance" \
  --group-by "package,epic,priority" \
  --time-range "30d" \
  --export "dashboard"
```

## Workflow Integration

### Sprint Management
```bash
# Manage sprints with swarms
npx claude-flow@v3alpha github sprint-manage \
  --sprint "Sprint 23" \
  --auto-populate \
  --capacity-planning \
  --track-velocity
```

### EPIC Tracking
```bash
# Track EPIC progress across packages
npx claude-flow@v3alpha github epic-track \
  --epic "Mission Briefing" \
  --packages "packages/api,packages/web,packages/app" \
  --update-board \
  --show-dependencies \
  --predict-completion
```

## Best Practices

### 1. Board Organization
- Organize by EPICs (Library, Missions, Loadouts, Captures)
- Track package-level progress (api, web, app)
- Monitor coverage compliance (90% target)
- Regular board grooming

### 2. Data Integrity
- Bidirectional sync validation
- Conflict resolution strategies
- Audit trails
- Regular backups

### 3. DailyLoadout-Specific Labels
- `packages/api`, `packages/web`, `packages/app` for package tracking
- `epic/N` for EPIC association
- `mission`, `loadout`, `capture`, `library` for domain areas
- `coverage-pass`, `coverage-fail` for test compliance

## Metrics & KPIs

### Performance Metrics
```bash
# Track board performance
npx claude-flow@v3alpha github board-kpis \
  --metrics '[
    "average-cycle-time",
    "throughput-per-sprint",
    "blocked-time-percentage",
    "coverage-compliance-rate",
    "first-time-pass-rate"
  ]' \
  --dashboard-url
```

See also: [swarm-issue.md](./swarm-issue.md), [multi-repo-swarm.md](./multi-repo-swarm.md)
