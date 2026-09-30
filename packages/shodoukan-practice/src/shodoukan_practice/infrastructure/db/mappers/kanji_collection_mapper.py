from ....domain.entities import KanjiCollection
from ..orm import KanjiCollectionORM


def kanji_collection_to_domain(row: KanjiCollectionORM) -> KanjiCollection:
    return KanjiCollection(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def kanji_collection_to_db(entity: KanjiCollection) -> KanjiCollectionORM:
    return KanjiCollectionORM(
        id=entity.id,
        user_id=entity.user_id,
        name=entity.name,
        description=entity.description,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
