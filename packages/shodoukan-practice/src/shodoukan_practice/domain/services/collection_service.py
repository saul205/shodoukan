"""Rules for using collections together (e.g. combining them into an
exercise), and for naming an imported one."""

from collections.abc import Collection as Names
from collections.abc import Sequence
from itertools import count

from ..entities import COLLECTION_NAME_MAX_LENGTH, Collection
from ..exceptions import CollectionKindMismatchError, CollectionOwnershipError


def ensure_combinable(collections: Sequence[Collection]) -> None:
    """Check that collections can be merged into one pool, e.g. for an exercise.

    They must belong to the same user and hold the same kind of item. The
    union of their members is resolved by the collection repository.
    """
    if len({c.user_id for c in collections}) > 1:
        raise CollectionOwnershipError(
            "cannot combine collections owned by different users"
        )
    if len({type(c) for c in collections}) > 1:
        raise CollectionKindMismatchError(
            "cannot combine entry collections with kanji collections"
        )


def free_collection_name(name: str, taken: Names[str]) -> str:
    """`name`, or with a suffix ("N5 (2)") if it's `taken`, within the length
    a name can have."""
    name = name.strip()[:COLLECTION_NAME_MAX_LENGTH].strip()
    if name not in taken:
        return name
    for n in count(2):
        suffix = f" ({n})"
        candidate = name[: COLLECTION_NAME_MAX_LENGTH - len(suffix)].rstrip() + suffix
        if candidate not in taken:
            return candidate
    raise AssertionError("unreachable")
