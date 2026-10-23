"""SQL for library search, shared by the entry and kanji repositories.

Each place a query can match (spellings, readings, meanings, ...) is a SELECT
of `(item_id, tier)`; `best_matches` keeps each item's best tier. Repositories
join that to the items, so filtering, ordering and paging stay in SQL.
"""

from sqlalchemy import (
    ColumnElement,
    Select,
    SQLColumnExpression,
    Subquery,
    case,
    func,
    or_,
    select,
    union_all,
)

from ...domain.searches import MatchTier


def text_match(
    column: SQLColumnExpression[str], needles: tuple[str, ...]
) -> tuple[ColumnElement[bool], ColumnElement[int]]:
    """Condition and tier for a spelling or reading against any of `needles`.

    `needles` are lower-case (the query and its kana forms): equal → EXACT,
    starts with → PREFIX, contains → CONTAINS. `%` and `_` are literal.
    """
    value = func.lower(column)
    exact = or_(*(value == needle for needle in needles))
    prefix = or_(*(value.startswith(needle, autoescape=True) for needle in needles))
    contains = or_(*(value.contains(needle, autoescape=True) for needle in needles))
    tier = case(
        (exact, MatchTier.EXACT.value),
        (prefix, MatchTier.PREFIX.value),
        else_=MatchTier.CONTAINS.value,
    )
    return contains, tier


def meaning_match(
    column: SQLColumnExpression[str], text: str
) -> tuple[ColumnElement[bool], ColumnElement[int]]:
    """Condition and tier for a meaning against the lower-case query.

    Equal → EXACT; a word of the meaning starts with it ("to eat" for "eat")
    → PREFIX; anywhere → CONTAINS.
    """
    value = func.lower(column)
    word_start = or_(
        value.startswith(text, autoescape=True),
        value.contains(" " + text, autoescape=True),
    )
    tier = case(
        (value == text, MatchTier.EXACT.value),
        (word_start, MatchTier.PREFIX.value),
        else_=MatchTier.CONTAINS.value,
    )
    return value.contains(text, autoescape=True), tier


def best_matches(sources: list[Select[int, int]]) -> Subquery:
    """`(item_id, tier)`: each matching item once, with its best tier."""
    hits = union_all(*sources).subquery("hits")
    return (
        select(hits.c.item_id, func.max(hits.c.tier).label("tier"))
        .group_by(hits.c.item_id)
        .subquery("matches")
    )
