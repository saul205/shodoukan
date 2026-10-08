"""Helpers for aggregates that change their nested items one at a time.

Internal to `domain/entities`: entries and kanji both find a nested item by
id, toggle it, and validate the text of the meanings users add.
"""

from collections.abc import Iterable
from typing import Protocol, TypeVar

from ..exceptions import EntityNotFoundError


class Identified(Protocol):
    id: int | None


class Toggleable(Identified, Protocol):
    enabled: bool


T = TypeVar("T", bound=Identified)


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
