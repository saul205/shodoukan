"""Helpers for aggregates that change their nested items one at a time.

Internal to `domain/entities`: entries and kanji both find a nested item by
id, toggle it, and validate the text of the meanings users add.
"""

from collections.abc import Callable, Iterable, Set
from typing import Literal, Protocol, TypeVar

from ..exceptions import EntityNotFoundError


class Identified(Protocol):
    id: int | None


class Toggleable(Identified, Protocol):
    enabled: bool


class Copyable(Identified, Protocol):
    """A part (or word) that can be a copy of someone else's.

    `None` in an id means "this row itself": a part the user created is its
    own original and version, and was copied from nowhere.
    """

    original_id: int | None
    source_id: int | None


# A version of a part's content: the row that wrote it, and how many times
# that row rewrote it.
Version = tuple[int, int]


class Versioned(Copyable, Toggleable, Protocol):
    """A part with content: `edited_id` is the row that wrote this version
    (`None`: this row), `revision` how many edits that row made, and
    `source_collection_ids` the collections that bring it (a part can come
    with several the user follows)."""

    edited_id: int | None
    revision: int
    source_collection_ids: list[int]

    @property
    def origin(self) -> str: ...


class CopySource(Protocol):
    """A part with content of a shared item (`SharedContent`)."""

    @property
    def origin(self) -> str: ...

    @property
    def enabled(self) -> bool: ...

    @property
    def identity(self) -> int | None: ...

    @property
    def version(self) -> Version | None: ...


T = TypeVar("T", bound=Identified)
C = TypeVar("C", bound=Versioned)
S = TypeVar("S", bound=CopySource)


def find_item(items: Iterable[T], item_id: int, kind: str) -> T:
    """The item with `item_id`; `EntityNotFoundError` if there's none."""
    for item in items:
        if item.id == item_id:
            return item
    raise EntityNotFoundError(f"{kind} {item_id} not found")


def clean_meaning(text: str) -> str:
    """A meaning's text without surrounding whitespace; it can't be empty."""
    text = text.strip()
    if not text:
        raise ValueError("a meaning can't be empty")
    return text


def clean_sentence(text: str) -> str:
    """An example sentence without surrounding whitespace; it can't be empty."""
    text = text.strip()
    if not text:
        raise ValueError("a sentence can't be empty")
    return text


def clean_kana(text: str) -> str:
    """A reading without surrounding whitespace: hiragana or katakana only."""
    text = text.strip()
    if not text or not all("\u3041" <= char <= "\u30ff" for char in text):
        raise ValueError("a reading is written in kana")
    return text


def clean_spelling(text: str) -> str:
    """A written form without surrounding whitespace; it can't be empty."""
    text = text.strip()
    if not text:
        raise ValueError("a spelling can't be empty")
    return text


def identity(part: Copyable) -> int | None:
    """The part all copies of this one share."""
    return part.original_id if part.original_id is not None else part.id


def version_row(part: Versioned) -> int | None:
    """The row that wrote the part's current content."""
    return part.edited_id if part.edited_id is not None else part.id


def version(part: Versioned) -> Version | None:
    """The version of the part's content: the row that wrote it, and its
    revision there (an edit by the same row is another version)."""
    row = version_row(part)
    return None if row is None else (row, part.revision)


def merge_parts(
    targets: list[C],
    parts: Iterable[S],
    *,
    created: bool,
    same: Callable[[C, S], bool],
    copy: Callable[[S], C],
    dismissed: Set[int] = frozenset(),
    source: int | None = None,
) -> bool:
    """Merge a shared list of parts into the item's own list.

    An imported part is located by its place among the imported targets and
    checked with `same`; its flag is taken only when the item was `created`
    by this import. An added part is appended as a `copy` unless a target
    has its version already (another version of the same part is added too:
    better to duplicate than to lose it), or the user deleted that part
    before (its identity is `dismissed`). A copy already there in that
    version gains `source` as one more collection that brings it. Returns
    whether anything changed.
    """
    imported = [t for t in targets if t.origin == "imported"]
    position = 0
    changed = False
    for part in parts:
        if part.origin == "imported":
            target = imported[position] if position < len(imported) else None
            position += 1
            if (
                created
                and target is not None
                and same(target, part)
                and target.enabled != part.enabled
            ):
                target.enabled = part.enabled
                changed = True
        elif part.identity in dismissed:
            continue
        else:
            match = next(
                (
                    t
                    for t in targets
                    if part.version is not None and version(t) == part.version
                ),
                None,
            )
            if match is None:
                targets.append(copy(part))
                changed = True
            elif (
                source is not None
                and match.edited_id is not None  # a copy, not the user's own
                and source not in match.source_collection_ids
            ):
                match.source_collection_ids.append(source)
                changed = True
    return changed


def untouched_from(part: Versioned, source_collection_id: int) -> bool:
    """Whether that collection brings `part` and the user hasn't edited it."""
    return (
        part.origin == "added"
        and source_collection_id in part.source_collection_ids
        and part.edited_id is not None
    )


def brought_by(source_collection_id: int | None) -> list[int]:
    """The collections a new copy is brought by: the one it came with, if any."""
    return [] if source_collection_id is None else [source_collection_id]


def unclaimed(part: Versioned) -> bool:
    """Whether `part` is an unedited copy no followed collection brings."""
    return part.edited_id is not None and not part.source_collection_ids


def prune_parts(
    targets: list[C],
    parts: Iterable[S],
    source_collection_id: int,
    keep: int = 0,
) -> bool:
    """Let go of the parts the collection brought, untouched, that its new
    shared list no longer has (in that version): the collection stops
    bringing them, and a part no collection brings any more is removed, as
    long as `keep` targets stay. Returns whether anything changed."""
    current = {p.version for p in parts if p.origin == "added"}
    changed = False
    for target in list(targets):
        if not untouched_from(target, source_collection_id) or (
            version(target) in current
        ):
            continue
        target.source_collection_ids.remove(source_collection_id)
        changed = True
        if not target.source_collection_ids and len(targets) > keep:
            targets.remove(target)
    return changed


# The kinds of part a user can delete from a copy. Ids are per table, so a
# dismissed part is keyed by its kind and identity (`"gloss:12"`).
PartKind = Literal["spelling", "reading", "sense", "gloss", "example", "meaning"]


def dismissal_key(kind: PartKind, part: Copyable) -> str | None:
    """The key that remembers a deleted copy, or `None` if it isn't one."""
    key = identity(part)
    if part.source_id is None or key is None:
        return None
    return f"{kind}:{key}"


def dismissed_of(keys: Iterable[str], kind: PartKind) -> set[int]:
    """The identities of the dismissed parts of one kind."""
    prefix = f"{kind}:"
    return {int(key[len(prefix) :]) for key in keys if key.startswith(prefix)}
