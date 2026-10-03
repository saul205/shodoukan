from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Junction table — no extra columns, no ORM class needed
reading_restrictions = Table(
    "reading_restrictions",
    Base.metadata,
    Column("reading_id", Integer, ForeignKey("readings.id"), primary_key=True),
    Column(
        "kanji_reading_id",
        Integer,
        ForeignKey("kanji_readings.id"),
        primary_key=True,
    ),
)


class EntryORM(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)

    kanji_readings: Mapped[list[KanjiReadingORM]] = relationship(
        back_populates="entry"
    )
    readings: Mapped[list[ReadingORM]] = relationship(back_populates="entry")
    senses: Mapped[list[SenseORM]] = relationship(back_populates="entry")
    entry_kanji: Mapped[list[EntryKanjiORM]] = relationship(back_populates="entry")


class KanjiReadingORM(Base):
    __tablename__ = "kanji_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"))
    kanji: Mapped[str]
    priority: Mapped[str]
    info: Mapped[str]

    entry: Mapped[EntryORM] = relationship(back_populates="kanji_readings")


class ReadingORM(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"))
    text: Mapped[str]
    no_kanji: Mapped[int]
    priority: Mapped[str]
    info: Mapped[str]

    entry: Mapped[EntryORM] = relationship(back_populates="readings")
    restrictions: Mapped[list[KanjiReadingORM]] = relationship(
        secondary=reading_restrictions,
        viewonly=True,
    )


class SenseORM(Base):
    __tablename__ = "senses"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"))
    pos: Mapped[str]
    misc: Mapped[str]
    dialects: Mapped[str]
    info: Mapped[str]

    entry: Mapped[EntryORM] = relationship(back_populates="senses")
    glosses: Mapped[list[GlossORM]] = relationship(back_populates="sense")
    cross_references: Mapped[list[CrossReferenceORM]] = relationship(
        back_populates="sense"
    )
    examples: Mapped[list[ExampleORM]] = relationship(back_populates="sense")


class GlossORM(Base):
    __tablename__ = "glosses"

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(ForeignKey("senses.id"))
    text: Mapped[str]
    type: Mapped[str | None]
    lang: Mapped[str | None]

    sense: Mapped[SenseORM] = relationship(back_populates="glosses")


class CrossReferenceORM(Base):
    __tablename__ = "cross_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(ForeignKey("senses.id"))
    reference: Mapped[str]
    reading: Mapped[str | None]
    sense_idx: Mapped[int | None]

    sense: Mapped[SenseORM] = relationship(back_populates="cross_references")


class ExampleORM(Base):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(ForeignKey("senses.id"))
    source_name: Mapped[str]
    source_id: Mapped[str | None]
    text: Mapped[str]

    sense: Mapped[SenseORM] = relationship(back_populates="examples")
    sentences: Mapped[list[ExampleSentenceORM]] = relationship(
        back_populates="example"
    )


class ExampleSentenceORM(Base):
    __tablename__ = "example_sentences"

    id: Mapped[int] = mapped_column(primary_key=True)
    example_id: Mapped[int] = mapped_column(ForeignKey("examples.id"))
    lang: Mapped[str]
    text: Mapped[str]

    example: Mapped[ExampleORM] = relationship(back_populates="sentences")


class EntryKanjiORM(Base):
    __tablename__ = "entry_kanji"

    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id"), primary_key=True
    )
    literal: Mapped[str] = mapped_column(primary_key=True)
    priority_score: Mapped[int]

    entry: Mapped[EntryORM] = relationship(back_populates="entry_kanji")


class KanjiORM(Base):
    __tablename__ = "kanji"

    literal: Mapped[str] = mapped_column(primary_key=True)
    grade: Mapped[int | None]
    stroke_count: Mapped[int]
    freq: Mapped[int | None]
    jlpt: Mapped[int | None]
    on_readings: Mapped[str]
    kun_readings: Mapped[str]
    nanori: Mapped[str]

    meanings: Mapped[list[KanjiMeaningORM]] = relationship(back_populates="kanji_obj")


class KanjiMeaningORM(Base):
    __tablename__ = "kanji_meanings"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(ForeignKey("kanji.literal"))
    text: Mapped[str]
    lang: Mapped[str]

    kanji_obj: Mapped[KanjiORM] = relationship(back_populates="meanings")
