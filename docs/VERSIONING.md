# Versioning & Releases

One repo, **independent versions per surface** — via prefixed git tags and
[release-please](https://github.com/googleapis/release-please) (per-component,
path-scoped changelogs from the Conventional Commits this repo already uses).

## Tags

```text
api/v1.2.0          web/v0.5.1
app/v1.3.0+45       backoffice/v0.2.0
```

The prefix replaces "one repo per surface" — each surface has its own version
line in the same repo. `+45` is the store build number (mirrors `pubspec.yaml`'s
`1.3.0+45`; in native it maps to iOS `CFBundleVersion` / Android `versionCode`).

| Surface | Version file (source of truth) | Tag | Managed by |
| --- | --- | --- | --- |
| API | `packages/api/pyproject.toml` (`[tool.poetry] version`) | `api/vX.Y.Z` | release-please |
| Web | `packages/web/package.json` (`version`) | `web/vX.Y.Z` | release-please |
| App | `packages/app/pubspec.yaml` (`version: X.Y.Z+BUILD`) | `app/vX.Y.Z+BUILD` | *its own store pipeline (add later)* |
| Backoffice | its `package.json` | `backoffice/vX.Y.Z` | *add when built* |

> Only **api** and **web** are wired into release-please today
> (`release-please-config.json`). The **app** is store-released and may move off
> Flutter to native Swift/Kotlin — its build-number semantics are store-specific,
> so it gets its own pipeline. The **backoffice** (Epic 21) is added when built.
> Add either as a new entry in `release-please-config.json` +
> `.release-please-manifest.json`.

## Why release-please (the path-scoped changelog)

GitHub's "Generate release notes" is **commit-range based and path-blind**: in a
monorepo, the notes for `api/v1.2.0` would list every web/app commit in the
range too. release-please tracks each **component by path**, so the API changelog
contains only commits that touched `packages/api/` — clean, per-surface notes.

## The release flow (and how it ties to staging/prod)

```text
PR → CI (lint/types/tests + migration check) → merge to main
        ├─ release-please updates the per-surface "release PR" (path-scoped changelog)
        └─ deploy-staging.yml → auto-deploys main to STAGING   ◄── validate here
   → merge the `api` release PR
        ├─ release-please cuts tag api/vX.Y.Z + GitHub release
        └─ release-please.yml chains → deploys that tag to PRODUCTION
```

- **Staging = "what's on main now"** (every merge redeploys it).
- **Production = the last released tag** (cutting a release = merging its release PR).
- The act of merging the release PR is your explicit go-to-prod control.

The prod deploy is **chained inside `release-please.yml`** (not a separate
tag-triggered workflow) because a tag created by the default `GITHUB_TOKEN` does
not itself trigger other workflows.

## Bumping a version (you don't hand-tag)

release-please derives the next version from your Conventional Commits and opens
a release PR — you review/merge it. So: write `feat:` / `fix:` / `feat!:`
commits scoped to a package, and the right surface's version bumps automatically.
No manual `git tag`.

## Enabling the pipeline

All deploy/release automation is **OFF** until you set the repository **variable**
`DEPLOY_ENABLED=true` (Settings → Secrets and variables → Actions → Variables).
Until then the jobs are *skipped* (never failed). Turn it on once the GitHub
setup is done — see [DEPLOYMENT.md §1.10](./DEPLOYMENT.md). The pre-merge CI
migration check runs regardless.
