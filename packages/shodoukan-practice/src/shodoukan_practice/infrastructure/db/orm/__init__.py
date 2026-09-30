"""SQLAlchemy ORM models, one module per aggregate (planned):

- user_orm.py — UserORM
- practice_entry_orm.py — PracticeEntryORM, PracticeFieldOverrideORM
- practice_kanji_orm.py — PracticeKanjiORM
- entry_collection_orm.py — EntryCollectionORM + entry_collection_items link table
- kanji_collection_orm.py — KanjiCollectionORM + kanji_collection_items link table

Link tables use a real FK with ON DELETE CASCADE; collection tables enforce
UNIQUE(user_id, name).
"""
