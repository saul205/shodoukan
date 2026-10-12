"""Helpers for aggregates that change their nested items one at a time.

Internal to `domain/entities`: entries and kanji both find a nested item by
id, toggle it, and validate the text of the meanings users add.
"""

from collections.abc import Callable, Iterable
from typing import Protocol, TypeVar

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


class Versioned(Copyable, Toggleable, Protocol):
    """A part with content, whose `edited_id` is the version of it."""

    edited_id: int | None

    @property
    def origin(self) -> str: ...


class CopySource(Protocol):
    """A part with content of a shared item (`SharedContent`)."""

    @property
    def origin(self) -> str: ...

    @property
    def enabled(self) -> bool: ...

    @property
    def version(self) -> int | None: ...


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


def version(part: Versioned) -> int | None:
    """The version of the part's content: the row where it was last written."""
    return part.edited_id if part.edited_id is not None else part.id


def merge_parts(
    targets: list[C],
    parts: Iterable[S],
    *,
    created: bool,
    same: Callable[[C, S], bool],
    copy: Callable[[S], C],
) -> bool:
    """Merge a shared list of parts into the item's own list.

    An imported part is located by its place among the imported targets and
    checked with `same`; its flag is taken only when the item was `created`
    by this import. An added part is appended as a `copy` unless a target
    has its version already (another version of the same part is added too:
    better to duplicate than to lose it). Returns whether anything changed.
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
        elif part.version is None or all(version(t) != part.version for t in targets):
            targets.append(copy(part))
            changed = True
    return changed
