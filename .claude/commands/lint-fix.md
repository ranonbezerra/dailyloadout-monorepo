# /lint-fix

Format and lint the entire codebase (API + Web).

## Usage
```
/lint-fix
```

## Execution

### API (packages/api)
```bash
cd packages/api && poetry run ruff format . && poetry run ruff check --fix . && poetry run mypy src/
```

### Web (packages/web)
```bash
cd packages/web && bun run lint --write
```

## Sequence

1. `ruff format .` — format all Python files
2. `ruff check --fix .` — auto-fix lint issues (unused imports, etc.)
3. `mypy src/` — type checking
4. `biome check --write` — format and lint all TypeScript/TSX files

## After execution

- If everything passes: report that the code is clean
- If mypy reports errors: analyze and fix the type errors
- If ruff reports non-auto-fixable errors: analyze and fix manually
- If biome reports errors: analyze and fix manually
