"""What a search of public collections asks for, and what it finds.

Plain values: the collection repositories run the search (`find_public`,
`count_public`), and the public collection queries build it.
"""

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from ..entities import Collection

C = TypeVar("C", bound=Collection)

# Whose public collections: the viewer's own, everybody else's, or all.
PublicOwner = Literal["mine", "others", "all"]
# Most downloaded first, or most recently published first.
PublicSort = Literal["popular", "recent"]


@dataclass(frozen=True)
class PublicCollectionSearch:
    """Filters for a search of public collections.

    - `text`: what the user typed, trimmed and lower-cased; it's looked for
      in the name, the description and the owner's username. `None` for all.
    - `owner`: relative to the viewer.
    """

    text: str | None = None
    owner: PublicOwner = "all"
    sort: PublicSort = "popular"


@dataclass(frozen=True)
class PublicCollectionSummary(Generic[C]):
    """A public collection as listed: its owner and its counts.

    - `item_count`: items in the published version.
    - `downloads`: distinct users who imported it (its owner isn't counted).
    - `viewer_version`: the version the viewer last imported, if they did.
    """

    collection: C
    owner_username: str
    item_count: int
    downloads: int
    viewer_version: int | None
