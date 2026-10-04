"""ORM <-> domain entity mapping, one module per aggregate.

`<entity>_to_domain(row)` builds the domain entity from an ORM row;
`<entity>_to_db(entity)` builds a detached ORM row from the entity (ids kept,
so `Session.merge` can update existing rows).
"""

from .entry_collection_mapper import entry_collection_to_db, entry_collection_to_domain
from .exercise_mapper import exercise_to_db, exercise_to_domain
from .kanji_collection_mapper import kanji_collection_to_db, kanji_collection_to_domain
from .practice_entry_mapper import practice_entry_to_db, practice_entry_to_domain
from .practice_kanji_mapper import practice_kanji_to_db, practice_kanji_to_domain
from .user_mapper import user_to_db, user_to_domain

__all__ = [
    "entry_collection_to_db",
    "entry_collection_to_domain",
    "exercise_to_db",
    "exercise_to_domain",
    "kanji_collection_to_db",
    "kanji_collection_to_domain",
    "practice_entry_to_db",
    "practice_entry_to_domain",
    "practice_kanji_to_db",
    "practice_kanji_to_domain",
    "user_to_db",
    "user_to_domain",
]
