# /test-api

Run the backend tests (packages/api) with pytest.

## Usage
```
/test-api [pattern]
```

Examples:
- `/test-api` -> run all tests
- `/test-api play session` -> run tests matching "play session" in path or name
- `/test-api test_create_pick` -> run specific test

## Execution

If $ARGUMENTS contains only a name pattern (no `/`):
```bash
cd packages/api && poetry run pytest -k "$ARGUMENTS" -v
```

If $ARGUMENTS contains a path:
```bash
cd packages/api && poetry run pytest "$ARGUMENTS" -v
```

No arguments:
```bash
cd packages/api && poetry run pytest -v
```

## After execution

- If all pass: report how many passed
- If any fail: read the traceback and suggest the fix
- If coverage is relevant: run with `--cov=src/slate --cov-report=term-missing` to see gaps
