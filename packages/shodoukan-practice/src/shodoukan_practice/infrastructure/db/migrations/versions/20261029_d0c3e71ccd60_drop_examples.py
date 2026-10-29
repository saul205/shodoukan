"""Drop examples: a word's sentences are the library's sentences now

`37c04a6faa6f` converted every example into a sentence (keeping its id); the
code reads and writes sentences only, so the example tables go.

Downgrading brings them back from the sentences: one example per word linked
to an entry, under its sense (the entry's first when it has none), the first
one with the sentence's id, so the older code finds its examples again.
Sentences linked to no word don't come back.

Revision ID: d0c3e71ccd60
Revises: 37c04a6faa6f
Create Date: 2026-10-29 00:09:14.639108+00:00
"""

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "d0c3e71ccd60"
down_revision: str | Sequence[str] | None = "37c04a6faa6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(
        op.f("ix_practice_example_sentences_example_id"),
        table_name="practice_example_sentences",
    )
    op.drop_table("practice_example_sentences")
    op.drop_index(op.f("ix_practice_examples_sense_id"), table_name="practice_examples")
    op.drop_table("practice_examples")


def downgrade() -> None:
    op.create_table(
        "practice_examples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sense_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "origin", sa.String(length=16), server_default="imported", nullable=False
        ),
        sa.Column("original_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("edited_id", sa.Integer(), nullable=True),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "source_collection_ids", sa.JSON(), server_default="[]", nullable=False
        ),
        sa.CheckConstraint(
            "origin IN ('imported', 'added')", name=op.f("ck_practice_examples_origin")
        ),
        sa.ForeignKeyConstraint(
            ["sense_id"],
            ["practice_senses.id"],
            name=op.f("fk_practice_examples_sense_id_practice_senses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_examples")),
    )
    op.create_index(
        op.f("ix_practice_examples_sense_id"),
        "practice_examples",
        ["sense_id"],
        unique=False,
    )
    op.create_table(
        "practice_example_sentences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("example_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["example_id"],
            ["practice_examples.id"],
            name=op.f("fk_practice_example_sentences_example_id_practice_examples"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_example_sentences")),
    )
    op.create_index(
        op.f("ix_practice_example_sentences_example_id"),
        "practice_example_sentences",
        ["example_id"],
        unique=False,
    )
    _examples_from_sentences()


# The tables as they are at this revision, so the migration never depends on
# the ORM models (which keep changing).
_senses = sa.table(
    "practice_senses",
    sa.column("id", sa.Integer()),
    sa.column("entry_id", sa.Integer()),
    sa.column("position", sa.Integer()),
)
_sentences = sa.table(
    "practice_sentences",
    sa.column("id", sa.Integer()),
    sa.column("text", sa.Text()),
    sa.column("is_active", sa.Boolean()),
    sa.column("origin", sa.String()),
    sa.column("original_id", sa.Integer()),
    sa.column("source_id", sa.Integer()),
    sa.column("edited_id", sa.Integer()),
    sa.column("revision", sa.Integer()),
    sa.column("source_collection_ids", sa.JSON()),
)
_translations = sa.table(
    "practice_sentence_translations",
    sa.column("sentence_id", sa.Integer()),
    sa.column("position", sa.Integer()),
    sa.column("lang", sa.String()),
    sa.column("text", sa.Text()),
)
_words = sa.table(
    "practice_sentence_words",
    sa.column("sentence_id", sa.Integer()),
    sa.column("position", sa.Integer()),
    sa.column("span_start", sa.Integer()),
    sa.column("span_end", sa.Integer()),
    sa.column("entry_id", sa.Integer()),
    sa.column("sense_id", sa.Integer()),
)
_examples = sa.table(
    "practice_examples",
    sa.column("id", sa.Integer()),
    sa.column("sense_id", sa.Integer()),
    sa.column("position", sa.Integer()),
    sa.column("text", sa.String()),
    sa.column("enabled", sa.Boolean()),
    sa.column("origin", sa.String()),
    sa.column("original_id", sa.Integer()),
    sa.column("source_id", sa.Integer()),
    sa.column("edited_id", sa.Integer()),
    sa.column("revision", sa.Integer()),
    sa.column("source_collection_ids", sa.JSON()),
)
_example_sentences = sa.table(
    "practice_example_sentences",
    sa.column("example_id", sa.Integer()),
    sa.column("position", sa.Integer()),
    sa.column("lang", sa.String()),
    sa.column("text", sa.String()),
)


def _examples_from_sentences() -> None:
    bind = op.get_bind()
    first_sense: dict[int, int] = {}
    for sense_id, entry_id in bind.execute(
        sa.select(_senses.c.id, _senses.c.entry_id).order_by(
            _senses.c.entry_id, _senses.c.position
        )
    ):
        first_sense.setdefault(entry_id, sense_id)
    translations: defaultdict[int, list[tuple[str, str]]] = defaultdict(list)
    for sentence_id, lang, text in bind.execute(
        sa.select(
            _translations.c.sentence_id, _translations.c.lang, _translations.c.text
        ).order_by(_translations.c.sentence_id, _translations.c.position)
    ):
        translations[sentence_id].append((lang, text))
    sentences = {row.id: row for row in bind.execute(sa.select(_sentences))}
    next_id = max(sentences, default=0) + 1
    used: set[int] = set()
    positions: defaultdict[int, int] = defaultdict(int)
    examples: list[dict[str, Any]] = []
    texts: list[dict[str, Any]] = []
    for word in bind.execute(
        sa.select(_words)
        .where(_words.c.entry_id.is_not(None))
        .order_by(_words.c.sentence_id, _words.c.position)
    ):
        sense_id = word.sense_id or first_sense.get(word.entry_id)
        if sense_id is None:
            continue
        sentence = sentences[word.sentence_id]
        if sentence.id in used:
            example_id, next_id = next_id, next_id + 1
        else:
            example_id = sentence.id
            used.add(sentence.id)
        form = (
            sentence.text[word.span_start : word.span_end]
            if sentence.origin == "imported" and word.span_start is not None
            else ""
        )
        examples.append(
            {
                "id": example_id,
                "sense_id": sense_id,
                "position": positions[sense_id],
                "text": form,
                "enabled": sentence.is_active,
                "origin": sentence.origin,
                "original_id": sentence.original_id,
                "source_id": sentence.source_id,
                "edited_id": sentence.edited_id,
                "revision": sentence.revision,
                "source_collection_ids": sentence.source_collection_ids,
            }
        )
        positions[sense_id] += 1
        texts += [
            {"example_id": example_id, "position": i, "lang": lang, "text": text}
            for i, (lang, text) in enumerate(
                [("jpn", sentence.text), *translations[sentence.id]]
            )
        ]
    if examples:
        op.bulk_insert(_examples, examples)
        op.bulk_insert(_example_sentences, texts)
    if bind.dialect.name == "postgresql":
        op.execute(
            "SELECT setval(pg_get_serial_sequence('practice_examples', 'id'), "
            "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM practice_examples"
        )
