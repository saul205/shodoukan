"""FTS5 virtual tables — not ORM-mappable, kept as Core Table objects."""

from sqlalchemy import Column, Integer, Table, Text

from shodoukan.db.orm import Base

glosses_fts = Table(
    "glosses_fts",
    Base.metadata,
    Column("rowid", Integer),
    Column("text", Text),
)

kanji_meanings_fts = Table(
    "kanji_meanings_fts",
    Base.metadata,
    Column("rowid", Integer),
    Column("text", Text),
)
