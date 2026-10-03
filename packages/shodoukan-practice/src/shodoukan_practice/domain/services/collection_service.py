"""Rules for using collections together (e.g. combining them into an exercise)."""

from collections.abc import Sequence

from ..entities import Collection
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
