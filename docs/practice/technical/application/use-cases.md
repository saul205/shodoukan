# Use Cases

[← Technical documentation](../README.md)

The application layer: what each use case does, with which ports. Code:
`src/shodoukan_practice/application/` (`commands/` write, `queries/` read).

Use cases receive their ports in `__init__` and expose `execute(...)`. They never
commit: the caller (the API route) owns the transaction. See
[endpoints](../api/endpoints.md#transactions).

## Commands (`commands/library_commands.py`)

### `ImportEntry(dictionary, entries).execute(user_id, source_entry_id)`

Copies dictionary entry `source_entry_id` into the user's library.

1. If the user already has it (`entries.get_by_source_entry_id`), return it with
   `created=False`. Nothing is written, and the dictionary isn't read.
2. Otherwise ask the [dictionary gateway](../infrastructure/dictionary-gateway.md) for
   a fresh snapshot. If there's none, raise `DictionaryItemNotFoundError`.
3. Store it with `entries.add_if_absent`. If a concurrent request stored the same item
   in between, that copy is returned with `created=False`. See
   [repositories](../infrastructure/repositories.md#add_if_absent).

Returns `ImportResult[PracticeEntry]` (`item`, `created`).

### `ImportKanji(dictionary, kanji).execute(user_id, literal)`

Same flow for kanji, keyed by `literal` (`kanji.get_by_literal`,
`dictionary.new_practice_kanji`).

## Commands (`commands/user_commands.py`)

### `EnsureUser(users).execute(user_id, username)`

Returns the practice user whose `id` is `user_id`, the identity provider's user id
(the token's `sub`, a UUID), **creating it** with that same id if this is the
identity's first request. `username`
(the token's `preferred_username`) is only used on creation. Creation goes through
`users.add_if_absent`, so two concurrent first requests create a single user. See
[decisions](../decisions.md#users-are-created-on-their-first-request).

## Queries

None yet. `queries/` is added with the first read use case.
