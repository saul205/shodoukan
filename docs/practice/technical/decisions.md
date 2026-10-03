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

## External identity provider instead of our own user management

Sign-up, sign-in, password storage and reset, sessions, brute-force protection, MFA and
social login stay with an OpenID Connect provider (Keycloak locally). Building them in
the practice API would put the most security-sensitive code of the system in our hands
for little gain. The API is written against the standard (signature, `iss`, `aud`,
`exp`), so the provider can be self-hosted Keycloak or a managed service in
production, changing configuration only.

## Users are created on their first request

This **replaces** "Unregistered users are rejected". The identity provider already
decides who may sign up, so any identity it vouches for gets a practice user on its
first request (`EnsureUser`, `GET /users/me`). There's no 403 any more. `username` is
the provider's display name, so it isn't unique and isn't updated after creation.

## Keycloak has its own database container

Keycloak stores its realm, users and sessions in a dedicated `keycloak-db` Postgres,
not in `practice-db`. It starts from an empty image and Keycloak creates its own
tables, so there are no init scripts or extra users to manage. Its environment lives in
its own `.env.keycloak`, and the identity provider can run, be upgraded or move
independently of the practice API, as it would in production.

## Users are keyed by the identity provider's UUID

`users.id` **is** the provider's user id (the token's `sub`, a UUID), and every
`user_id` foreign key is a UUID. This replaces the integer id plus `subject` column: a
strict 1:1 with provider users, with no second id to keep in sync, and the same id in
the API, the database and Keycloak. The cost is that the provider must issue UUID
`sub`s (Keycloak, Cognito and Supabase do; Auth0, Google and Okta don't), and tokens
with any other `sub` get `401`. Switching to such a provider would need an id-mapping
column again.

## Migrations squashed before the first deploy

The integer-to-UUID change was folded into a single regenerated initial migration
instead of a conversion migration, although the original initial migration had
already been pushed to the feature branch. No environment had ever applied it (the
practice database has never been deployed and the branch wasn't merged), so there was
no data to convert. This is the only exception to "never edit a pushed migration", and
it ends with the first deployment.

## Import status is a separate request from dictionary search

The dictionary page searches with `shodoukan-api`'s public `GET /search` and, in
parallel, asks the practice API `GET /library/imported` with the ids of the results.
Search is the same for everyone: public, cacheable, and no sign-in needed to browse.
Import status is per user: it needs a token and the practice database. Merging them
would make every search require sign-in, defeat shared caching, make search depend on
PostgreSQL, and duplicate `shodoukan-api`'s search in the practice API. The cost is a
second, short request. Searching the user's own imported data (the collection page)
is a separate, future use case.

## The practice app has its own dictionary search

The dictionary and the practice app are **standalone applications** that may evolve
separately. So the practice API exposes `GET /dictionary/search` itself instead of
relying on `shodoukan-api` being up, and the dictionary page searches there. This
partly supersedes "Import status is a separate request from dictionary search": status
is still a separate per-user request, but the search now comes from the practice API.
Nothing is reimplemented: both apps call the `shodoukan` library's `Dictionary.search`,
so query detection and ranking stay identical, and search changes belong in the
library. The response has `shodoukan-api`'s shape (so UI components can serve both)
but is the practice API's own read model (`Dictionary*`), translated in the
anti-corruption mapper so the two APIs' contracts can diverge.

## Collection name clashes come from the unique constraint

A user can't have two entry (or two kanji) collections with the same name. The
repository doesn't look the name up before writing: it writes in a savepoint and turns
the `UNIQUE(user_id, name)` violation into `CollectionNameTakenError`. A pre-check
alone would let two concurrent requests both pass it, and the loser would get a `500`
instead of a `409`.

## Collection updates replace name and description

`PUT /collections/{kind}/{id}` takes the whole `CollectionRequest` and replaces both
fields, instead of a `PATCH` with optional fields. With only two editable fields the
client always has both, and the use case stays typed (`name: str`,
`description: str | None`) without a sentinel to tell "not sent" from "cleared". The
cost: an omitted `description` clears it. If collections gain more fields, revisit
with a `PATCH`.

## Dictionary data in the library is only ever disabled

The library copy is the user's, but its dictionary data (readings, spellings, examples
and imported meanings) is never edited or deleted: the user disables what they don't
want. Only meanings they added themselves can be edited and removed. This keeps the
original always recoverable (re-enable it), keeps an "imported" item meaning the same
thing as the dictionary, and lets a future re-sync with the dictionary tell the
user's additions apart. Readings can't be added for now: it's rarely needed and would
need an `origin` column on the reading tables.

## One endpoint per customisation

Each edit of a library item is its own small request (`PUT .../notes`,
`PUT .../{part}/{id}/enabled`, `POST .../glosses`, ...) instead of a `PATCH` of the whole
document. Each maps to one domain method, so the rules (only own meanings change) are
enforced where they live, the UI saves each toggle or note as the user makes it, and two
tabs editing different parts don't overwrite each other. Every edit returns the whole
item so the client doesn't have to merge.

## The practice frontend is a Nuxt 4 SPA with Nuxt UI

`shodoukan-practice-web` is built with Nuxt UI 4, which needs Nuxt 4, while the
dictionary web stays on Nuxt 3. Nuxt UI gives the dashboard layout (collapsible
sidebar, panels), forms, overlays and toasts ready-made and accessible, with an official
Claude Code skill for its conventions. The dictionary cards come from `shodoukan-ui`
(built with Tailwind 3 into its own CSS), so the two Tailwind versions don't meet.

It renders only in the browser (`ssr: false`): every screen needs the signed-in user's
token, which lives in the browser, so the server would render nothing useful and would
complicate the sign-in flow. Sign-in uses `oidc-client-ts`, written against the OpenID
Connect standard like the API, so the identity provider can change by configuration.

The item detail is a page shared by the library and collections, not a modal, so it has
its own URL and the back button works.

## Importing into collections is one request

The dictionary lets the user pick a collection for an item that isn't imported yet.
`POST /library/entries` and `/library/kanji` take optional `collection_ids` instead of
the frontend chaining the import and `PUT /collections/.../items/...`: two requests can
fail halfway and leave the item imported but outside the collection the user chose.
One request runs in one transaction, checks the collections before importing (an
unknown one imports nothing), and stays idempotent, so a retry is safe. Every client
gets that guarantee without repeating the logic. Adding an already-imported item to a
collection keeps using the collection endpoints.
