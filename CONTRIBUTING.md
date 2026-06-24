# Contributing to DailyLoadout

## Commit Convention

This project follows [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

### Commit message structure

```text
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Purpose |
| ------ | --------- |
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration |
| `build` | Build system or dependencies |
| `chore` | Other changes that don't modify src or test files |

### Scopes

| Scope | Package |
| ------- | --------- |
| `api` | `packages/api/` |
| `app` | `packages/app/` |
| `web` | `packages/web/` |
| `infra` | `infra/`, `docker-compose.*` |

Omit scope for cross-cutting changes (e.g., `docs: update ROADMAP.md`).

### Breaking changes

Use `!` after the type/scope:

```text
feat(api)!: change auth token format
```

Or add a `BREAKING CHANGE:` footer:

```text
feat(api): change auth token format

BREAKING CHANGE: access tokens now use opaque format instead of JWT
```

### Examples

```text
feat(api): add user registration endpoint
feat(app): add login screen with AuthBloc
fix(api): handle duplicate email on signup
test(api): add auth endpoint integration tests
refactor(api): extract JWT config to settings
ci: add postgres service to ci-api workflow
docs: update ARCHITECTURE.md with auth strategy
chore(infra): add postgres init.sql extensions
```

## Branch Naming

```text
epic/<number>-<slug>       # epic/1-auth
```

## Pull Requests

- One PR per epic, targeting `main`
- PR title follows the commit convention: `feat(api): implement auth + users (Epic 1)`
- `main` must always be in a working state — never merge broken code

## Quality Gate

Before pushing, run:

```bash
make check   # lint + test across all packages
```
