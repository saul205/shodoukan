# Git, documentation & changelog

These apply to any project in this repo, not just Python.

## Git

- Branches: `<username>/<issue>_<short-description>` (e.g.
  `saul205/16_create-the-shodoukan-practice-app`).
- PR-based workflow — no direct pushes to `main`.
- One logical change per commit: tooling, domain code and docs changes go in separate
  commits when they can stand alone. Each commit should leave `ruff`, `mypy` and the
  tests passing.
- Commit messages follow the convention below.

### Commit messages

```
<scope>: <Summary in imperative mood>

<Body: why the change was made, then what changed at a high level.
Wrap at 72 columns. Bullets are fine for listing several changes.>

Refs #<issue>
```

- **Scope**: the package the commit affects, same names as the changelog tags —
  `shodoukan`, `shodoukan-api`, `shodoukan-practice`, `shodoukan-ui`,
  `shodoukan-web`. Use `repo` for root-level tooling and config (CI, linters,
  `.gitignore`, editor settings) and `docs` for documentation and conventions
  (`README.md`, `CLAUDE.md`, `docs/`, `.claude/rules`, `.claude/skills`). If a commit
  really spans several packages, split it; if it can't be split, use the main one.
- **Summary**: imperative ("Add", "Rename", "Fix" — not "Added"/"Adds"), capitalized
  after the colon, no trailing period, whole line ≤ 72 characters. It completes the
  sentence "If applied, this commit will …".
- **Body**: required unless the summary says it all (e.g. a typo fix). Explain the
  *why* and any decision a reviewer would otherwise ask about; the diff already shows
  the *how*.
- **Footer**: reference the issue from the branch name — `Refs #16` for work in
  progress, `Fixes #16` only on the commit that closes it.
- English only. No empty, duplicated or "wip"/"fixes" messages on branches that will
  be merged; squash those before opening the PR.

Example:

```
shodoukan-practice: Add users and collections to the domain

Users own the imported entries and kanji; collections group them
without copying data and double as tags. Entry and kanji collections
are separate subclasses so repositories can't mix their ids.

Refs #16
```
- Never commit secrets or credentials. Keep `.env.example` up to date with any new
  variable (documented, no real values). Before adding a new `.env*` file or anything
  that looks like a credential, confirm it's covered by `.gitignore` — the root
  `.gitignore` covers most cases; add a package-level `.gitignore` only when that
  package's tooling genuinely differs (e.g. `packages/shodoukan-web/.gitignore` for
  Nuxt build artifacts).

## Documentation

- `README.md` — high-level overview, setup, deployment.
- `CLAUDE.md` — project instructions: stack, repo structure, key architectural
  decisions, and the documentation index table.
- `docs/index.md` + `docs/functional/*.md` + `docs/technical/*.md` — functional and
  technical detail per area (search, web, api, ...).

Update these as part of the change that makes them stale, not as a follow-up task.
When you add a package or make a significant architectural decision, add/extend the
relevant doc file and add a row to the table in `CLAUDE.md`.

## Changelog

Single `CHANGELOG.md` at the repo root, [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
format:

```markdown
## [x.y.z] — YYYY-MM-DD

### Added
- ...

### Changed
- ...
```

This repo is one product made of several packages, so the changelog stays a single
file rather than one per package. Tag each entry with the package it affects, e.g.:

```markdown
- **shodoukan-practice:** ...
```
