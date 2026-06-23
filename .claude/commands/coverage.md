# /coverage

Run tests with coverage and analyze critical gaps.

## Usage
```
/coverage [module]
```

Examples:
- `/coverage` -> full coverage
- `/coverage core/mission` -> coverage of a specific module

## Execution

```bash
cd packages/api && poetry run pytest --cov=src/dailyloadout --cov-report=term-missing --cov-report=html -v
```

For specific module:
```bash
cd packages/api && poetry run pytest tests/test_$ARGUMENTS.py --cov=src/dailyloadout/$ARGUMENTS --cov-report=term-missing -v
```

## Gap analysis

After the report, analyze and report:

1. **Current overall coverage** (target: >= 90%)
2. **Coverage by domain** (core/mission, core/library, core/capture, core/loadout, core/stats)
3. **Infrastructure coverage** (LLM client, repositories, tasks)
4. **Top 5 uncovered lines** most important (error branches, LLM validation, edge cases)
5. **Suggestion for next tests** to write to reach targets

## Coverage targets

| Module | Minimum |
|--------|---------|
| Overall (core + infrastructure) | 90% |
| Core services | 90% |
| Repositories | 85% |
| API routes | 80% |
| LLM integration | 75% |
