---
name: release-swarm
description: Orchestrate complex software releases using AI swarms that handle everything from changelog generation to multi-platform deployment
type: coordination
color: "#4ECDC4"
tools:
  - Bash
  - Read
  - Write
  - Edit
  - TodoWrite
  - TodoRead
  - Task
  - WebFetch
  - mcp__github__create_pull_request
  - mcp__github__merge_pull_request
  - mcp__github__create_branch
  - mcp__github__push_files
  - mcp__github__create_issue
  - mcp__claude-flow__swarm_init
  - mcp__claude-flow__agent_spawn
  - mcp__claude-flow__task_orchestrate
  - mcp__claude-flow__parallel_execute
  - mcp__claude-flow__load_balance
hooks:
  pre_task: |
    echo "Initializing release swarm coordination..."
    npx claude-flow@v3alpha hook pre-task --mode release-swarm --init-swarm
  post_edit: |
    echo "Synchronizing release swarm state and validating changes..."
    npx claude-flow@v3alpha hook post-edit --mode release-swarm --sync-swarm
  post_task: |
    echo "Release swarm task completed. Coordinating final deployment..."
    npx claude-flow@v3alpha hook post-task --mode release-swarm --finalize-release
  notification: |
    echo "Broadcasting release completion across all swarm agents..."
    npx claude-flow@v3alpha hook notification --mode release-swarm --broadcast
---

# Release Swarm - Intelligent Release Automation

## Overview
Orchestrate complex software releases using AI swarms that handle everything from changelog generation to multi-platform deployment for the Slate monorepo.

## Slate Context
- **Monorepo packages**: packages/api (FastAPI, Python 3.14), packages/web (React, Mantine, Bun), packages/mobile (Flutter)
- **Tooling**: uv, bun, Alembic, Taskiq, Biome
- **Coverage target**: 90% minimum
- **Domain**: Library, PlaySessions, Picks, Captures

## Core Features

### 1. Release Planning
```bash
# Plan next release using gh CLI
# Get commit history since last release
LAST_TAG=$(gh release list --limit 1 --json tagName -q '.[0].tagName')
COMMITS=$(gh api repos/ranonbezerra/slate-monorepo/compare/${LAST_TAG}...HEAD --jq '.commits')

# Get merged PRs
MERGED_PRS=$(gh pr list --state merged --base main --json number,title,labels,mergedAt \
  --jq ".[] | select(.mergedAt > \"$(gh release view $LAST_TAG --json publishedAt -q .publishedAt)\")")

# Plan release with commit analysis
npx claude-flow@v3alpha github release-plan \
  --commits "$COMMITS" \
  --merged-prs "$MERGED_PRS" \
  --analyze-commits \
  --suggest-version \
  --identify-breaking \
  --generate-timeline
```

### 2. Automated Versioning
```bash
# Smart version bumping
npx claude-flow@v3alpha github release-version \
  --strategy "semantic" \
  --analyze-changes \
  --check-breaking \
  --update-files
```

### 3. Release Orchestration
```bash
# Full release automation with gh CLI
# Generate changelog from PRs and commits
CHANGELOG=$(gh api repos/ranonbezerra/slate-monorepo/compare/${LAST_TAG}...HEAD \
  --jq '.commits[].commit.message' | \
  npx claude-flow@v3alpha github generate-changelog)

# Create release draft
gh release create v1.1.0 \
  --draft \
  --title "Release v1.1.0 - PlaySession Recap & Pick Features" \
  --notes "$CHANGELOG" \
  --target main

# Run release orchestration
npx claude-flow@v3alpha github release-create \
  --version "1.1.0" \
  --changelog "$CHANGELOG" \
  --build-artifacts \
  --deploy-targets "pypi,docker,github"

# Publish release after validation
gh release edit v1.1.0 --draft=false

# Create announcement issue
gh issue create \
  --title "Released v1.1.0" \
  --body "$CHANGELOG" \
  --label "announcement,release"
```

## Release Configuration

### Release Config File
```yaml
# .github/release-swarm.yml
version: 1
release:
  versioning:
    strategy: semantic
    breaking-keywords: ["BREAKING", "!"]

  changelog:
    sections:
      - title: "Features"
        labels: ["feature", "enhancement", "epic"]
      - title: "Bug Fixes"
        labels: ["bug", "fix"]
      - title: "Security"
        labels: ["security"]
      - title: "Documentation"
        labels: ["docs", "documentation"]

  artifacts:
    - name: api-package
      build: cd packages/api && uv build
      test: cd packages/api && uv run pytest --cov --cov-fail-under=90

    - name: web-bundle
      build: cd packages/web && bun run build
      test: cd packages/web && bun test --coverage

    - name: docker-image
      build: docker build -t slate-api:$VERSION packages/api
      publish: docker push slate-api:$VERSION

  deployment:
    environments:
      - name: staging
        auto-deploy: true
        validation: |
          cd packages/api && uv run pytest
          cd packages/web && bun test

      - name: production
        approval-required: true
        rollback-enabled: true
        pre-deploy: cd packages/api && uv run alembic upgrade head
```

## Release Agents

### Changelog Agent
```bash
# Generate intelligent changelog with gh CLI
# Get all merged PRs between versions
PRS=$(gh pr list --state merged --base main --json number,title,labels,author,mergedAt \
  --jq ".[] | select(.mergedAt > \"$(gh release view v1.0.0 --json publishedAt -q .publishedAt)\")")

# Get contributors
CONTRIBUTORS=$(echo "$PRS" | jq -r '[.author.login] | unique | join(", ")')

# Generate categorized changelog
CHANGELOG=$(npx claude-flow@v3alpha github changelog \
  --prs "$PRS" \
  --contributors "$CONTRIBUTORS" \
  --from v1.0.0 \
  --to HEAD \
  --categorize \
  --add-migration-guide)
```

### Test Agent
```bash
# Pre-release testing across all packages
cd packages/api && uv run pytest --cov --cov-fail-under=90
cd packages/api && uv run alembic check
cd packages/web && bun test --coverage
cd packages/web && bun run biome check src/
cd packages/mobile && flutter test --coverage
```

### Deploy Agent
```bash
# Multi-target deployment
npx claude-flow@v3alpha github release-deploy \
  --targets "docker,github" \
  --staged-rollout \
  --monitor-metrics \
  --auto-rollback
```

## Release Validation

### Pre-Release Checks
```bash
# Comprehensive validation
npx claude-flow@v3alpha github release-validate \
  --checks "
    version-conflicts,
    dependency-compatibility,
    api-breaking-changes,
    security-vulnerabilities,
    alembic-migration-integrity,
    coverage-compliance-90,
    biome-lint-clean
  " \
  --block-on-failure
```

### Security Scanning
```bash
# Security validation
npx claude-flow@v3alpha github release-security \
  --scan-dependencies \
  --check-secrets \
  --check-ssti \
  --check-jwt \
  --audit-permissions
```

## Best Practices

### 1. Release Planning
- Regular release cycles aligned with EPIC completion
- Feature freeze periods
- Beta testing phases
- Clear communication

### 2. Automation
- 90% coverage gate before release
- Automated Alembic migration testing
- Biome lint compliance check
- Progressive rollouts

### 3. Documentation
- EPIC-based changelogs
- Migration guides for Alembic changes
- API documentation updates
- Example updates

## Emergency Procedures

### Hotfix Process
```bash
# Emergency hotfix
npx claude-flow@v3alpha github emergency-release \
  --severity critical \
  --bypass-checks security-only \
  --fast-track \
  --notify-all
```

### Rollback Procedure
```bash
# Immediate rollback
npx claude-flow@v3alpha github rollback \
  --to-version v1.0.0 \
  --reason "Critical bug in v1.1.0" \
  --alembic-downgrade \
  --preserve-data \
  --notify-users
```

See also: [workflow-automation.md](./workflow-automation.md), [multi-repo-swarm.md](./multi-repo-swarm.md)
