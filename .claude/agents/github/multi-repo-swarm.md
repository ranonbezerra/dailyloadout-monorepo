---
name: multi-repo-swarm
description: Cross-repository swarm orchestration for organization-wide automation and intelligent collaboration
type: coordination
color: "#FF6B35"
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
  - mcp__claude-flow__github_sync_coord
  - mcp__claude-flow__github_metrics
hooks:
  pre:
    - "gh auth status || (echo 'GitHub CLI not authenticated' && exit 1)"
    - "git status --porcelain || echo 'Not in git repository'"
    - "gh repo list --limit 1 >/dev/null || (echo 'No repo access' && exit 1)"
  post:
    - "gh pr list --state open --limit 5 | grep -q . && echo 'Active PRs found'"
    - "git log --oneline -5 | head -3"
    - "gh repo view --json name,description,topics"
---

# Multi-Repo Swarm - Cross-Repository Swarm Orchestration

## Overview
Coordinate AI swarms across multiple repositories, enabling organization-wide automation and intelligent cross-project collaboration.

## DailyLoadout Context
- **Primary monorepo**: ranonbezerra/dailyloadout-monorepo (packages/api, packages/web, packages/app)
- **Stack**: FastAPI (Python 3.14), React+Mantine (Bun, Biome), Flutter
- **Domain**: Library, Missions, Loadouts, Captures
- **Tools**: uv (Python), bun (TypeScript), Taskiq (workers), Alembic (migrations)

## Core Features

### 1. Cross-Repo Initialization
```bash
# Initialize multi-repo swarm with gh CLI
# List organization repositories
REPOS=$(gh repo list ranonbezerra --limit 100 --json name,description,languages \
  --jq '.[] | select(.name | test("dailyloadout|shared"))')

# Get repository details
REPO_DETAILS=$(echo "$REPOS" | jq -r '.name' | while read -r repo; do
  gh api repos/ranonbezerra/$repo --jq '{name, default_branch, languages, topics}'
done | jq -s '.')

# Initialize swarm with repository context
npx claude-flow@v3alpha github multi-repo-init \
  --repo-details "$REPO_DETAILS" \
  --repos "ranonbezerra/dailyloadout-monorepo" \
  --topology hierarchical \
  --shared-memory \
  --sync-strategy eventual
```

### 2. Repository Discovery
```bash
# Auto-discover related repositories with gh CLI
# Search organization repositories
REPOS=$(gh repo list ranonbezerra --limit 100 \
  --json name,description,languages,topics \
  --jq '.[] | select(.languages | keys | contains(["Python","TypeScript"]))')

# Analyze repository dependencies
DEPS=$(echo "$REPOS" | jq -r '.name' | while read -r repo; do
  # Get pyproject.toml or package.json if they exist
  if gh api repos/ranonbezerra/$repo/contents/pyproject.toml --jq '.content' 2>/dev/null; then
    echo "Found Python project: $repo"
  fi
  if gh api repos/ranonbezerra/$repo/contents/package.json --jq '.content' 2>/dev/null; then
    gh api repos/ranonbezerra/$repo/contents/package.json \
      --jq '.content' | base64 -d | jq '{name, dependencies, devDependencies}'
  fi
done | jq -s '.')

# Discover and analyze
npx claude-flow@v3alpha github discover-repos \
  --repos "$REPOS" \
  --dependencies "$DEPS" \
  --analyze-dependencies \
  --suggest-swarm-topology
```

### 3. Synchronized Operations
```bash
# Execute synchronized changes across repos with gh CLI
# For monorepo packages, coordinate changes
PACKAGES=("packages/api" "packages/web" "packages/app")

for pkg in "${PACKAGES[@]}"; do
  echo "Processing $pkg..."

  # Run package-specific validation
  case "$pkg" in
    "packages/api")
      cd packages/api && uv run pytest --cov --cov-fail-under=90
      ;;
    "packages/web")
      cd packages/web && bun test --coverage
      ;;
    "packages/app")
      cd packages/app && flutter test --coverage
      ;;
  esac

  cd -
done

# Create PR if changes exist
if [[ -n $(git status --porcelain) ]]; then
  git checkout -b update-dependencies-$(date +%Y%m%d)
  git add -A
  git commit -m "chore: Update dependencies across packages"
  git push origin HEAD
  PR_URL=$(gh pr create \
    --title "Update dependencies" \
    --body "Automated dependency update across packages" \
    --label "dependencies,automated")
  echo "Created PR: $PR_URL"
fi
```

## Configuration

### Multi-Package Config
```yaml
# .swarm/multi-repo.yml
version: 1
organization: ranonbezerra
monorepo: dailyloadout-monorepo
packages:
  - name: api
    path: packages/api
    role: backend
    language: python
    agents: [architect, coder, tester]
    tools: [uv, alembic, taskiq]

  - name: web
    path: packages/web
    role: frontend
    language: typescript
    agents: [coder, designer, tester]
    tools: [bun, biome, mantine]

  - name: app
    path: packages/app
    role: mobile
    language: dart
    agents: [coder, tester]
    tools: [flutter]

coordination:
  topology: hierarchical
  communication: webhook
  memory: redis://shared-memory

dependencies:
  - from: web
    to: [api]
  - from: app
    to: [api]
```

### Package Roles
```javascript
// Define package roles and responsibilities
{
  "roles": {
    "backend": {
      "responsibilities": ["api-endpoints", "business-logic", "data-models", "llm-integration"],
      "default-agents": ["architect", "coder", "security"],
      "tools": ["uv", "alembic", "taskiq", "pytest"]
    },
    "frontend": {
      "responsibilities": ["user-interface", "ux", "accessibility", "state-management"],
      "default-agents": ["designer", "coder", "tester"],
      "tools": ["bun", "biome", "mantine", "vitest"]
    },
    "mobile": {
      "responsibilities": ["mobile-ui", "platform-integration", "offline-support"],
      "default-agents": ["coder", "tester"],
      "tools": ["flutter", "dart"]
    }
  }
}
```

## Orchestration Commands

### Dependency Management
```bash
# Update dependencies across all packages
# Create tracking issue first
TRACKING_ISSUE=$(gh issue create \
  --title "Dependency Update: Cross-package alignment" \
  --body "Tracking issue for updating dependencies across all packages" \
  --label "dependencies,tracking" \
  --json number -q .number)

# Update Python dependencies
cd packages/api && uv lock --upgrade
uv run pytest --cov --cov-fail-under=90

# Update TypeScript dependencies
cd packages/web && bun update
bun test --coverage

# Update Flutter dependencies
cd packages/app && flutter pub upgrade
flutter test --coverage

# Create PR
git checkout -b update-deps-$(date +%Y%m%d)
git add -A
git commit -m "chore: Update dependencies across all packages

Part of #$TRACKING_ISSUE"
git push origin HEAD
gh pr create \
  --title "Update dependencies across packages" \
  --body "Updates dependencies in api (uv), web (bun), and app (flutter)\n\nTracking: #$TRACKING_ISSUE" \
  --label "dependencies"
```

## Best Practices

### 1. Package Organization
- Clear package boundaries and responsibilities
- Consistent naming conventions across packages/api, packages/web, packages/app
- Documented cross-package dependencies
- Shared configuration standards

### 2. Communication
- Use appropriate sync strategies between packages
- Implement circuit breakers for cross-package calls
- Monitor API contract compliance
- Clear error propagation

### 3. Security
- Secure cross-package authentication (JWT shared secrets)
- Jinja2 SandboxedEnvironment for LLM templates
- Audit trail for all operations
- Coverage gate at 90%

## Use Cases

### 1. Full-Stack Feature Development
```bash
# Coordinate full-stack feature across packages
# API: Create Alembic migration + FastAPI endpoints
cd packages/api && uv run alembic revision --autogenerate -m "add missions table"
# Web: Create Mantine components + React hooks
cd packages/web && bun run build
# App: Create Flutter screens
cd packages/app && flutter build
```

### 2. Cross-Package Testing
```bash
# Run integration tests across packages
cd packages/api && uv run pytest tests/ --cov --cov-fail-under=90
cd packages/web && bun test --coverage
cd packages/app && flutter test --coverage
```

See also: [project-board-sync.md](./project-board-sync.md)
