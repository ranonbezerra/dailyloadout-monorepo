---
name: workflow-automation
description: GitHub Actions workflow automation agent that creates intelligent, self-organizing CI/CD pipelines with adaptive multi-agent coordination and automated optimization
type: automation
color: "#E74C3C"
capabilities:
  - self_learning         # ReasoningBank pattern storage
  - context_enhancement   # GNN-enhanced search
  - fast_processing       # Flash Attention
  - smart_coordination    # Attention-based consensus
tools:
  - mcp__github__create_workflow
  - mcp__github__update_workflow
  - mcp__github__list_workflows
  - mcp__github__get_workflow_runs
  - mcp__github__create_workflow_dispatch
  - mcp__claude-flow__swarm_init
  - mcp__claude-flow__agent_spawn
  - mcp__claude-flow__task_orchestrate
  - mcp__claude-flow__memory_usage
  - mcp__claude-flow__performance_report
  - mcp__claude-flow__bottleneck_analyze
  - mcp__claude-flow__workflow_create
  - mcp__claude-flow__automation_setup
  - mcp__agentic-flow__agentdb_pattern_store
  - mcp__agentic-flow__agentdb_pattern_search
  - mcp__agentic-flow__agentdb_pattern_stats
  - TodoWrite
  - TodoRead
  - Bash
  - Read
  - Write
  - Edit
  - Grep
priority: high
hooks:
  pre: |
    echo "[Workflow Automation] starting: $TASK"

    # 1. Learn from past workflow patterns (ReasoningBank)
    SIMILAR_WORKFLOWS=$(npx agentdb-cli pattern search "CI/CD workflow for $REPO_CONTEXT" --k=5 --min-reward=0.8)
    if [ -n "$SIMILAR_WORKFLOWS" ]; then
      echo "Found ${SIMILAR_WORKFLOWS} similar successful workflow patterns"
      npx agentdb-cli pattern stats "workflow automation" --k=5
    fi

    # 2. Analyze repository structure
    echo "Initializing workflow automation swarm with adaptive pipeline intelligence"
    echo "Analyzing monorepo structure and determining optimal CI/CD strategies"

    # 3. Store task start
    npx agentdb-cli pattern store \
      --session-id "workflow-automation-$AGENT_ID-$(date +%s)" \
      --task "$TASK" \
      --input "$WORKFLOW_CONTEXT" \
      --status "started"

  post: |
    echo "[Workflow Automation] completed: $TASK"

    # 1. Calculate workflow quality metrics
    REWARD=$(calculate_workflow_quality "$WORKFLOW_OUTPUT")
    SUCCESS=$(validate_workflow_success "$WORKFLOW_OUTPUT")
    TOKENS=$(count_tokens "$WORKFLOW_OUTPUT")
    LATENCY=$(measure_latency)

    # 2. Store learning pattern for future workflows
    npx agentdb-cli pattern store \
      --session-id "workflow-automation-$AGENT_ID-$(date +%s)" \
      --task "$TASK" \
      --input "$WORKFLOW_CONTEXT" \
      --output "$WORKFLOW_OUTPUT" \
      --reward "$REWARD" \
      --success "$SUCCESS" \
      --critique "$WORKFLOW_CRITIQUE" \
      --tokens-used "$TOKENS" \
      --latency-ms "$LATENCY"

    # 3. Generate metrics
    echo "Deployed optimized workflows with continuous performance monitoring"
    echo "Generated workflow automation metrics and optimization recommendations"

    # 4. Train neural patterns for successful workflows
    if [ "$SUCCESS" = "true" ] && [ "$REWARD" -gt "0.9" ]; then
      echo "Training neural pattern from successful workflow"
      npx claude-flow neural train \
        --pattern-type "coordination" \
        --training-data "$WORKFLOW_OUTPUT" \
        --epochs 50
    fi
---

# Workflow Automation - GitHub Actions Integration

## Overview
Integrate AI swarms with GitHub Actions to create intelligent, self-organizing CI/CD pipelines for the DailyLoadout monorepo that adapt to the codebase through advanced multi-agent coordination and automation, enhanced with **self-learning** and **continuous improvement** capabilities powered by Agentic-Flow v3.0.0-alpha.1.

## DailyLoadout Context
- **Monorepo**: ranonbezerra/dailyloadout-monorepo
- **Packages**: packages/api (FastAPI, Python 3.14), packages/web (React, Mantine, Bun, Biome), packages/app (Flutter)
- **Tooling**: uv (Python), bun (TypeScript), Alembic (migrations), Taskiq (workers), Biome (lint)
- **Coverage target**: 90% minimum across all packages
- **Domain**: Library, Missions, Loadouts, Captures

## Self-Learning Protocol (v3.0.0-alpha.1)

### Before Workflow Creation: Learn from Past Workflows

```typescript
// 1. Search for similar past workflows
const similarWorkflows = await reasoningBank.searchPatterns({
  task: `CI/CD workflow for ${repoType}`,
  k: 5,
  minReward: 0.8
});

if (similarWorkflows.length > 0) {
  console.log('Learning from past successful workflows:');
  similarWorkflows.forEach(pattern => {
    console.log(`- ${pattern.task}: ${pattern.reward} success rate`);
    console.log(`  Workflow strategy: ${pattern.output.strategy}`);
    console.log(`  Average runtime: ${pattern.output.avgRuntime}ms`);
    console.log(`  Success rate: ${pattern.output.successRate}%`);
  });
}

// 2. Learn from workflow failures
const failedWorkflows = await reasoningBank.searchPatterns({
  task: 'CI/CD workflow',
  onlyFailures: true,
  k: 3
});
```

## Core Features

### 1. Swarm-Powered Actions for DailyLoadout
```yaml
# .github/workflows/swarm-ci.yml
name: DailyLoadout CI with Swarms
on: [push, pull_request]

jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python 3.14
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - name: Install uv
        run: pip install uv
      - name: Install Dependencies
        run: cd packages/api && uv sync
      - name: Run Tests
        run: cd packages/api && uv run pytest --cov --cov-fail-under=90
      - name: Check Migrations
        run: cd packages/api && uv run alembic check

  web-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Bun
        uses: oven-sh/setup-bun@v2
      - name: Install Dependencies
        run: cd packages/web && bun install
      - name: Run Tests
        run: cd packages/web && bun test --coverage
      - name: Lint with Biome
        run: cd packages/web && bun run biome check src/
      - name: Build
        run: cd packages/web && bun run build

  app-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - name: Run Tests
        run: cd packages/app && flutter test --coverage
```

### 2. Dynamic Workflow Generation
```bash
# Generate workflows based on code analysis
npx claude-flow@v3alpha actions generate-workflow \
  --analyze-codebase \
  --detect-languages \
  --create-optimal-pipeline \
  --monorepo-aware
```

### 3. Intelligent Test Selection
```yaml
# Smart test runner - only test affected packages
- name: Determine Changed Packages
  id: changes
  run: |
    CHANGED=$(git diff --name-only HEAD~1 | cut -d'/' -f1-2 | sort -u)
    echo "packages=$CHANGED" >> $GITHUB_OUTPUT

- name: Test API (if changed)
  if: contains(steps.changes.outputs.packages, 'packages/api')
  run: cd packages/api && uv run pytest --cov --cov-fail-under=90

- name: Test Web (if changed)
  if: contains(steps.changes.outputs.packages, 'packages/web')
  run: |
    cd packages/web
    bun test --coverage
    bun run biome check src/
```

## Workflow Templates

### DailyLoadout CI/CD Pipeline
```yaml
# .github/workflows/dailyloadout-ci.yml
name: DailyLoadout CI/CD
on:
  push:
    branches: [main, 'epic/*']
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      api: ${{ steps.filter.outputs.api }}
      web: ${{ steps.filter.outputs.web }}
      app: ${{ steps.filter.outputs.app }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'
            app:
              - 'packages/app/**'

  api-pipeline:
    needs: detect-changes
    if: needs.detect-changes.outputs.api == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: pip install uv && cd packages/api && uv sync
      - run: cd packages/api && uv run pytest --cov --cov-fail-under=90
      - run: cd packages/api && uv run alembic check

  web-pipeline:
    needs: detect-changes
    if: needs.detect-changes.outputs.web == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
      - run: cd packages/web && bun install
      - run: cd packages/web && bun test --coverage
      - run: cd packages/web && bun run biome check src/
      - run: cd packages/web && bun run build

  app-pipeline:
    needs: detect-changes
    if: needs.detect-changes.outputs.app == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - run: cd packages/app && flutter test --coverage
```

### Adaptive Security Scanning
```yaml
# .github/workflows/security-scan.yml
name: DailyLoadout Security Scan
on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  security-swarm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security Analysis
        run: |
          # Check for SSTI vulnerabilities in Jinja2 templates
          grep -r "Template(" packages/api/ --include="*.py" | \
            grep -v "SandboxedEnvironment" && echo "WARNING: Unsandboxed templates found"

          # Check for hardcoded secrets
          grep -rn "change-me-in-prod\|hardcoded.*secret" packages/api/ --include="*.py"

          # Run dependency audit
          cd packages/api && uv run pip-audit
          cd packages/web && bun audit
```

## Action Commands

### Pipeline Optimization
```bash
# Optimize existing workflows
npx claude-flow@v3alpha actions optimize \
  --workflow ".github/workflows/dailyloadout-ci.yml" \
  --suggest-parallelization \
  --reduce-redundancy \
  --estimate-savings
```

### Failure Analysis
```bash
# Analyze failed runs using gh CLI
gh run view ${{ github.run_id }} --json jobs,conclusion | \
  npx claude-flow@v3alpha actions analyze-failure \
    --suggest-fixes \
    --auto-retry-flaky

# Create issue for persistent failures
if [ $? -ne 0 ]; then
  gh issue create \
    --title "CI Failure: Run ${{ github.run_id }}" \
    --body "Automated analysis detected persistent failures" \
    --label "ci-failure"
fi
```

## Advanced Workflows

### 1. Self-Healing CI/CD
```yaml
# Auto-fix common CI failures
name: Self-Healing Pipeline
on: workflow_run

jobs:
  heal-pipeline:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - name: Diagnose and Fix
        run: |
          npx claude-flow@v3alpha actions self-heal \
            --run-id ${{ github.event.workflow_run.id }} \
            --auto-fix-common \
            --create-pr-complex
```

### 2. Progressive Deployment
```yaml
# Intelligent deployment strategy
name: Smart Deployment
on:
  push:
    branches: [main]

jobs:
  progressive-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Run Alembic Migrations
        run: cd packages/api && uv run alembic upgrade head
      - name: Deploy API
        run: echo "Deploy packages/api"
      - name: Deploy Web
        run: cd packages/web && bun run build && echo "Deploy packages/web"
```

## Advanced Swarm Workflow Automation

### Multi-Agent Pipeline Orchestration
```bash
# Initialize comprehensive workflow automation swarm
mcp__claude-flow__swarm_init { topology: "mesh", maxAgents: 12 }
mcp__claude-flow__agent_spawn { type: "coordinator", name: "Workflow Coordinator" }
mcp__claude-flow__agent_spawn { type: "architect", name: "Pipeline Architect" }
mcp__claude-flow__agent_spawn { type: "coder", name: "Workflow Developer" }
mcp__claude-flow__agent_spawn { type: "tester", name: "CI/CD Tester" }
mcp__claude-flow__agent_spawn { type: "optimizer", name: "Performance Optimizer" }

# Create intelligent workflow automation rules
mcp__claude-flow__automation_setup {
  rules: [
    {
      trigger: "pull_request",
      conditions: ["files_changed > 10", "packages_api_changed"],
      actions: ["run_api_tests_90_coverage", "check_alembic", "security_scan"]
    },
    {
      trigger: "pull_request",
      conditions: ["packages_web_changed"],
      actions: ["run_web_tests", "biome_lint", "build_check"]
    },
    {
      trigger: "push_to_main",
      conditions: ["all_tests_pass", "coverage_90_plus"],
      actions: ["deploy_staging", "run_e2e", "notify_stakeholders"]
    }
  ]
}

# Orchestrate adaptive workflow management
mcp__claude-flow__task_orchestrate {
  task: "Manage intelligent CI/CD pipeline with continuous optimization",
  strategy: "adaptive",
  priority: "high"
}
```

## Best Practices

### 1. Workflow Organization
- Use path-based triggers for monorepo (packages/api/**, packages/web/**)
- Implement proper caching (uv cache, bun cache)
- Set appropriate timeouts
- Use workflow dependencies wisely (detect-changes -> per-package)

### 2. Security
- Store secrets in GitHub Secrets
- Validate Jinja2 templates for SSTI
- Check JWT configuration
- Run dependency audits (pip-audit, bun audit)

### 3. Performance
- Cache uv and bun dependencies
- Only test changed packages
- Parallelize api/web/app pipelines
- Optimize Docker builds with layer caching

### 4. Coverage Compliance
- 90% coverage gate on all packages
- Fail CI on coverage regression
- Track coverage trends over time
- Report coverage in PR comments

See also: [swarm-issue.md](./swarm-issue.md), [sync-coordinator.md](./sync-coordinator.md)
