# Releases

How a version of shodoukan is cut, numbered and tagged, and the release scheme we plan
to move to. Deploying is in [deployment](deployment.md); the commit and changelog
conventions are in `.claude/rules/git-and-docs.md`.

## Today

The flow is git-flow's:

1. Cut `release/X.Y.Z` from `develop` (no username prefix: a release isn't one
   person's work).
2. On it, bump the versions and move `[Unreleased]` in `CHANGELOG.md` into the new
   version's section. Nothing else goes in but release fixes.
3. Open a PR into `main`. After the merge, merge `main` back into `develop` and tag the
   merge commit on `main`.
4. Close the issues that were waiting in "Review".

A release branch carries the whole repo as `develop` had it: every package goes to
`main`, released or not. What is published or deployed depends on how CI and the
deploy script react to `main`:

| What | Triggered by |
|---|---|
| Dictionary API and web (Render) | every push to `main` ([ci.yml](../../.github/workflows/ci.yml), job `deploy`) |
| Practice stack (pre) | by hand: `deploy/deploy.sh` builds `origin/main` by default, or any ref given |
| Python library (`shodoukan`) | not published; consumers install it from the repo |

So, today, any release redeploys the dictionary on Render. `develop` can be deployed
to pre without a release: `deploy/deploy.sh origin/develop`.

## Planned (not implemented yet)

Agreed on 2026-10-16, to be done later. The goal is to release the library or the
apps on their own, from the same monorepo and the same git-flow.

### Two version lines

| Line | Packages | Tag | Changelog |
|---|---|---|---|
| Library | `shodoukan` | `shodoukan-vX.Y.Z` | `packages/shodoukan/CHANGELOG.md` |
| Platform | `shodoukan-api`, `shodoukan-web`, `shodoukan-ui`, `shodoukan-practice`, `shodoukan-practice-web` | `vX.Y.Z` | `CHANGELOG.md` (root) |

- The library is what others depend on, so its version follows its public API
  (SemVer) and moves only when it changes. The apps are deployed together and share
  almost everything, so they share one version.
- Apps state the library they need with `shodoukan>=X.Y.Z` and keep installing it in
  editable mode inside the repo.

### Tags decide what goes out

A release branch still carries everything, so what a release publishes is decided by
the versions it bumps and the tags it pushes, not by the code reaching `main`:

| Release | Bumped on `release/…` | Tag | Published |
|---|---|---|---|
| Library only | `packages/shodoukan` and its changelog | `shodoukan-vX.Y.Z` | the library |
| Apps only | the apps and the root changelog | `vX.Y.Z` | Render, then pre with `deploy/deploy.sh vX.Y.Z` |
| Both | both | both tags | everything |

Changes this needs:

1. **Render deploy on the `v*` tag**, not on every push to `main`: otherwise a
   library-only release redeploys the dictionary API and web.
2. **`deploy.sh` defaults to the latest `v*` tag** instead of `origin/main`, so pre
   only runs released versions by default. Any ref (`origin/develop`) still works for
   trying something.
3. **A library publishing workflow** on `shodoukan-v*` tags: build only
   `packages/shodoukan` (`python -m build packages/shodoukan`) and publish it, to PyPI
   with trusted publishing (no token in the repo) or as a GitHub Release asset. Still
   to decide.
4. **`develop` stays releasable.** Unfinished work stays on its feature branch: a
   release takes whatever `develop` has to `main`, even if it isn't tagged.

### Why not a separate repo for the library

Features usually cross the library and the apps (stroke order touched the library,
the API and the practice app in one PR). In separate repos that's a library release,
a dependency bump and then the app change, plus duplicated CI and editable installs
across repos. The monorepo with a version line per product keeps that in one PR.
Splitting the library out pays off once it has outside users or contributors with
their own pace; `shodoukan-db` is already split that way, as a published artifact.
