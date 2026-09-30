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
