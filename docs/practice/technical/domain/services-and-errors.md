# Domain Services, Errors and Clock

[← Technical documentation](../README.md)

Pure business rules that don't belong to a single entity, the domain exceptions, and
the domain's notion of "now".

## Services (`domain/services/`)

### `collection_service.ensure_combinable(collections)`

Checks that collections can be merged into one pool (e.g. for an exercise):

- all have the same owner, else `CollectionOwnershipError`;
- all are the same subclass (all `EntryCollection` or all `KanjiCollection`), else
  `CollectionKindMismatchError`.

An empty list is combinable. The union of their members is computed by the
repository (`item_ids`), not here.

## Exceptions (`domain/exceptions.py`)

| Exception | Base | Raised when |
|---|---|---|
| `CollectionOwnershipError` | `ValueError` | Collections of different users are combined, or an item is added to another user's collection |
| `CollectionKindMismatchError` | `ValueError` | Entry and kanji collections are combined |
| `EntityNotFoundError` | `LookupError` | An update/delete targets something that doesn't exist or belongs to another user |
| `DictionaryItemNotFoundError` | `LookupError` | An import asks for an entry or kanji the dictionary doesn't have (HTTP `404`) |

## Clock (`domain/clock.py`)

`utc_now()` returns `datetime.now(UTC)`, an aware UTC datetime. It's the only source
of "now" for entities and repositories. See
[dates and time zones](../cross-cutting/dates-and-time-zones.md).
