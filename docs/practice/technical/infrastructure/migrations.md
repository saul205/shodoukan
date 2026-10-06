# Migrations (Alembic)

[← Technical documentation](../README.md)

How the [schema](database-schema.md) is versioned and changed.

## Setup

| Item | Location |
|---|---|
| Config | `packages/shodoukan-practice/alembic.ini` |
| Environment | `src/shodoukan_practice/infrastructure/db/migrations/env.py` |
| Revision template | `.../migrations/script.py.mako` |
| Revisions | `.../migrations/versions/` (named `YYYYMMDD_<rev>_<slug>.py`) |

`env.py`:

- reads the URL from `PRACTICE_DATABASE_URL`, or from `sqlalchemy.url` when a caller
  sets it (the tests do);
- targets `Base.metadata` with `compare_type=True`;
- uses `render_as_batch` on SQLite, which can't `ALTER` most things in place;
- has a `render_item` hook that writes custom column types (`UtcDateTime`) as their
  plain SQLAlchemy type, so migrations never import application code.

New revision files are formatted and linted by Ruff through `post_write_hooks`.

## Workflow

Every model change ships with a migration in the same commit.

```bash
set -a; . ./.env.dev; set +a                                   # export PRACTICE_DATABASE_URL
alembic -c packages/shodoukan-practice/alembic.ini revision --autogenerate -m "Describe the change"
# review the generated file by hand
alembic -c packages/shodoukan-practice/alembic.ini upgrade head
alembic -c packages/shodoukan-practice/alembic.ini check      # no pending changes
```

Generate against the local PostgreSQL (see
[configuration](../cross-cutting/configuration.md)), not SQLite, so the result matches
the real engine.

Don't edit a migration that has been pushed or applied anywhere shared. Add a new one
instead. A migration that exists only locally can be regenerated. The one exception
was before the first deployment: the history was squashed into a single initial
migration (see [decisions](../decisions.md#migrations-squashed-before-the-first-deploy)).
Once any environment is deployed, migrations are append-only.

## History

| Revision | Change |
|---|---|
| `4ea69ccc76fd` | Initial schema (squashed before the first deploy) |
| `cc326135e923` | `notes` on `practice_entries`, `practice_senses`, `practice_kanji` |
| `8ef13443cd30` | `exercises` and their collection link tables |
| `08d07b56c263` | `exercise_sessions` and `exercise_questions` |
| `f59399cff4a5` | One question per position in a session |
| `bfad9df5a138` | One open session per user (closes the extra ones first) |
| `33f2afbdd7cf` | Questions by `type`: a choice card's `options` and `correct_option` move into `details` (JSON); downgrading moves them back and deletes other types' questions |

## Safety nets

- `tests/shodoukan-practice/infrastructure/test_migrations.py` upgrades an empty SQLite
  database to `head` and asserts there's no difference with the models. It fails if
  someone changes a model without a migration. It also checks `downgrade base`.
- CI runs `upgrade head`, `check`, `downgrade base` and `upgrade head` against a
  throwaway PostgreSQL. See [testing](../testing.md#ci).
