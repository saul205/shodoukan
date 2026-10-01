# Design Decisions

[← Technical documentation](README.md)

A short log of the non-obvious choices in the practice app, newest last. Each entry
says what was decided and why, so it isn't re-litigated or accidentally undone. If a
decision is reversed, add a new entry instead of editing the old one.

## Collections double as tags

A tag and a collection are the same data: a named group plus an m:n link to items.
There is one concept, `Collection`. Tagging an item is adding it to a collection.

## Collections don't hold their members

`Collection` is metadata only. Membership lives in link tables and goes through the
repository (`add_item`, `list_by_collection`, `item_ids`), so listing cards paginates
and sorts in SQL, tagging is a single INSERT, and nothing loads a whole collection.

## Entry and kanji collections are subclasses

Entries and kanji are never studied together. A `kind` field was replaced by
`EntryCollection` / `KanjiCollection`: the type says what a collection holds, each
has its own tables with real foreign keys, and code that only needs the grouping uses
the `Collection` base.

## Ports take typed entities, not ids

Entry and kanji collection ids come from different tables and can collide. Ports take
`KanjiCollection` rather than an `int`, and mypy (nominal typing) rejects mixing them.
The application loads the collection anyway, to answer "not found" or "not yours".

## Protocols for repository ports

`typing.Protocol` by default: implementations needn't import the domain, and mypy
checks conformance. Implementations still inherit their Protocol explicitly to be
checked at the definition. An `ABC` is fine where runtime enforcement, shared helpers
or `isinstance` checks are needed.

## PostgreSQL, normalized snapshot

PostgreSQL in every real environment, SQLite in unit tests. The nested snapshot is
normalized (one table per level) so enabling, disabling or adding one gloss or reading
is a single-row write with a stable id.

## Repositories never commit

The caller (use case / request) owns the transaction. Repositories flush only, so
several of them share one unit of work.

## Naive UTC in the database, aware UTC in the backend

The database stores naive UTC, the backend works with aware UTC (`UtcDateTime`), and
the API will send ISO 8601 with offset, so clients convert to local time.

## The domain decides "now"; no database defaults for timestamps

Timestamps come from `utc_now()` in the domain; aggregates bump `updated_at` with
`touch()` from their mutation methods. Database defaults only pay off when something
writes to the database without going through the app. Here they would hide dates from
the entity until after the insert, fight the domain's `updated_at`, make time hard to
control in tests, and need dialect-specific SQL (`timezone('utc', now())` on
PostgreSQL, which SQLite lacks). Performance and scale are the same either way.
Revisit if a non-app writer appears, and then add a `server_default` only as a safety
net.

## The dictionary is used in-process behind a port

`shodoukan` already is the shared library: `shodoukan-api` is a thin FastAPI layer over
`shodoukan.Dictionary`. The practice app uses it the same way, in-process, behind a
`DictionaryGateway` port, and wires its own cached instance (nothing is shared with
the API beyond the library). The practice app only needs the dictionary at import
time, since imported items are snapshots. Considered and rejected for now:

- **HTTP calls to `shodoukan-api`:** one owner of the data, but it adds latency,
  failure handling and an API contract to keep stable.
- **Merging both apps:** one deployable, but read-only search and per-user writes
  would share their scaling and deploy cycle.
- **A new common package:** `shodoukan` already is that package.

The port makes an HTTP adapter a drop-in replacement if the services need to be split.
The gateway returns domain entities, and an anti-corruption mapper keeps the
dictionary's models out of the domain.

## Keycloak, with the API as a resource server

Users sign in with Keycloak (OIDC). The API only verifies access tokens (RS256 against
the realm's JWKS, plus `exp`, `iss` and optionally `aud`) and identifies the user by
`sub`, stored as `users.subject`. No passwords or login code live in this repo.

## Unregistered users are rejected

A valid token whose `sub` has no practice user gets `403`. Users aren't created on
first sight; a registration use case will create them. This keeps account creation
an explicit step.

## Imports are idempotent and keep every language

Importing an item the user already has returns that copy (`200`) instead of failing,
so double clicks and retries are harmless. A concurrent duplicate is handled with a
savepoint (`add_if_absent`). The snapshot keeps every language the dictionary has: the
UI filters by language, and switching language never needs a re-import.

## One session per request; routes commit

The request's `Session` is shared by every repository it uses. Use cases don't commit;
the route commits after the use case succeeds and before responding, so the client
never gets a success response for a transaction that then fails to commit.
