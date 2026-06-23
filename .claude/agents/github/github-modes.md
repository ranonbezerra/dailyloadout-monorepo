---
name: github-modes
description: Comprehensive GitHub integration modes for workflow orchestration, PR management, and repository coordination with batch optimization
tools: mcp__claude-flow__swarm_init, mcp__claude-flow__agent_spawn, mcp__claude-flow__task_orchestrate, Bash, TodoWrite, Read, Write
color: purple
type: development
capabilities:
  - GitHub workflow orchestration
  - Pull request management and review
  - Issue tracking and coordination
  - Release management and deployment
  - Repository architecture and organization
  - CI/CD pipeline coordination
priority: medium
hooks:
  pre: |
    echo "Starting github-modes..."
    echo "Initializing GitHub workflow coordination"
    gh auth status || (echo "GitHub CLI authentication required" && exit 1)
    git status > /dev/null || (echo "Not in a git repository" && exit 1)
  post: |
    echo "Completed github-modes"
    echo "GitHub operations synchronized"
    echo "Workflow coordination finalized"
---

# GitHub Integration Modes

## Overview
This document describes all GitHub integration modes available for the DailyLoadout monorepo with swarm coordination. Each mode is optimized for specific GitHub workflows and includes batch tool integration for maximum efficiency.

## DailyLoadout Monorepo Context

### Stack Overview
- **packages/api**: FastAPI backend (Python 3.14, Alembic, Taskiq, Jinja2 LLM prompts)
- **packages/web**: React frontend (TypeScript, Mantine UI, Bun, Biome linting)
- **packages/app**: Flutter mobile app (Dart)
- **Domain**: Library (gear/equipment), Missions (briefing/debrief), Loadouts (gear selection/packing), Captures (voice/photo/text with AI)
- **Coverage target**: 90% minimum across all packages

## GitHub Workflow Modes

### gh-coordinator
**GitHub workflow orchestration and coordination**
- **Coordination Mode**: Hierarchical
- **Max Parallel Operations**: 10
- **Batch Optimized**: Yes
- **Tools**: gh CLI commands, TodoWrite, TodoRead, Task, Memory, Bash
- **Usage**: `/github gh-coordinator <GitHub workflow description>`
- **Best For**: Complex GitHub workflows, multi-package coordination

### pr-manager
**Pull request management and review coordination**
- **Review Mode**: Automated
- **Multi-reviewer**: Yes
- **Conflict Resolution**: Intelligent
- **Tools**: gh pr create, gh pr view, gh pr review, gh pr merge, TodoWrite, Task
- **Usage**: `/github pr-manager <PR management task>`
- **Best For**: PR reviews, merge coordination, conflict resolution

### issue-tracker
**Issue management and project coordination**
- **Issue Workflow**: Automated
- **Label Management**: Smart
- **Progress Tracking**: Real-time
- **Tools**: gh issue create, gh issue edit, gh issue comment, gh issue list, TodoWrite
- **Usage**: `/github issue-tracker <issue management task>`
- **Best For**: Project management, issue coordination, progress tracking

### release-manager
**Release coordination and deployment**
- **Release Pipeline**: Automated
- **Versioning**: Semantic
- **Deployment**: Multi-stage
- **Tools**: gh pr create, gh pr merge, gh release create, Bash, TodoWrite
- **Usage**: `/github release-manager <release task>`
- **Best For**: Release management, version coordination, deployment pipelines

## Repository Management Modes

### repo-architect
**Repository structure and organization**
- **Structure Optimization**: Yes
- **Multi-package**: Support
- **Template Management**: Advanced
- **Tools**: gh repo create, gh repo clone, git commands, Write, Read, Bash
- **Usage**: `/github repo-architect <repository management task>`
- **Best For**: Repository setup, structure optimization, monorepo management

### code-reviewer
**Automated code review and quality assurance**
- **Review Quality**: Deep
- **Security Analysis**: Yes (SSTI, JWT, CORS)
- **Performance Check**: Automated
- **Tools**: gh pr view --json files, gh pr review, gh pr comment, Read, Write
- **Usage**: `/github code-reviewer <review task>`
- **Best For**: Code quality, security reviews, performance analysis

### branch-manager
**Branch management and workflow coordination**
- **Branch Strategy**: GitFlow with epic branches
- **Merge Strategy**: Intelligent
- **Conflict Prevention**: Proactive
- **Tools**: gh api (for branch operations), git commands, Bash
- **Usage**: `/github branch-manager <branch management task>`
- **Best For**: Branch coordination, merge strategies, workflow management

## Integration Commands

### sync-coordinator
**Multi-package synchronization**
- **Package Sync**: Intelligent (api, web, app)
- **Version Alignment**: Automatic
- **Dependency Resolution**: Advanced (uv for Python, bun for TypeScript)
- **Tools**: git commands, gh pr create, Read, Write, Bash
- **Usage**: `/github sync-coordinator <sync task>`
- **Best For**: Package synchronization, version management, dependency updates

### ci-orchestrator
**CI/CD pipeline coordination**
- **Pipeline Management**: Advanced
- **Test Coordination**: Parallel (pytest, vitest)
- **Deployment**: Automated
- **Tools**: gh pr checks, gh workflow list, gh run list, Bash, TodoWrite, Task
- **Usage**: `/github ci-orchestrator <CI/CD task>`
- **Best For**: CI/CD coordination, test management, deployment automation

### security-guardian
**Security and compliance management**
- **Security Scan**: Automated (SSTI, JWT, CORS, file upload)
- **Compliance Check**: Continuous
- **Vulnerability Management**: Proactive
- **Tools**: gh search code, gh issue create, gh secret list, Read, Write
- **Usage**: `/github security-guardian <security task>`
- **Best For**: Security audits, compliance checks, vulnerability management

## Usage Examples

### Creating a coordinated pull request workflow:
```bash
/github pr-manager "Review and merge epic/6-mission-briefing branch with automated testing and multi-reviewer coordination"
```

### Managing monorepo synchronization:
```bash
/github sync-coordinator "Synchronize packages/api and packages/web, align dependencies, and validate cross-package integration"
```

### Setting up automated issue tracking:
```bash
/github issue-tracker "Create and manage EPIC issues with automated progress tracking and swarm coordination"
```

## Batch Operations

All GitHub modes support batch operations for maximum efficiency:

### Parallel GitHub Operations Example:
```javascript
[Single Message with BatchTool]:
  Bash("gh issue create --title 'Feature: Mission Briefing' --body '...'")
  Bash("gh issue create --title 'Feature: Loadout Picker' --body '...'")
  Bash("gh pr create --title 'PR 1' --head 'epic/6-mission-briefing' --base 'main'")
  Bash("gh pr create --title 'PR 2' --head 'feature/loadout-picker' --base 'main'")
  TodoWrite { todos: [todo1, todo2, todo3] }
  Bash("git checkout main && git pull")
```

## Integration with Swarm Coordination

All GitHub modes can be enhanced with swarm coordination:

```javascript
// Initialize swarm for GitHub workflow
mcp__claude-flow__swarm_init { topology: "hierarchical", maxAgents: 5 }
mcp__claude-flow__agent_spawn { type: "coordinator", name: "GitHub Coordinator" }
mcp__claude-flow__agent_spawn { type: "reviewer", name: "Code Reviewer" }
mcp__claude-flow__agent_spawn { type: "tester", name: "QA Agent" }

// Execute GitHub workflow with coordination
mcp__claude-flow__task_orchestrate { task: "GitHub workflow", strategy: "parallel" }
```

## DailyLoadout-Specific Workflows

### API Development Workflow
```bash
# Validate API changes
cd packages/api && uv run pytest --cov --cov-fail-under=90
uv run alembic check  # Verify migration heads
uv run biome check src/  # Lint Python (if configured)
```

### Web Development Workflow
```bash
# Validate web changes
cd packages/web && bun test --coverage
bun run biome check src/  # Lint with Biome
bun run build  # Verify build succeeds
```

### Cross-Package Validation
```bash
# Run full monorepo validation
cd packages/api && uv run pytest
cd packages/web && bun test
# Verify API contracts match frontend expectations
```
