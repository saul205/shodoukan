from ....domain.entities import KanjiCollection
from ..orm import KanjiCollectionORM


def kanji_collection_to_domain(row: KanjiCollectionORM) -> KanjiCollection:
    return KanjiCollection(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        description=row.description,
        is_public=row.is_public,
        published_version=row.published_version,
        published_at=row.published_at,
        source_collection_id=row.source_collection_id,
        source_version=row.source_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def kanji_collection_to_db(entity: KanjiCollection) -> KanjiCollectionORM:
    return KanjiCollectionORM(
        id=entity.id,
        user_id=entity.user_id,
        name=entity.name,
        description=entity.description,
        is_public=entity.is_public,
        published_version=entity.published_version,
        published_at=entity.published_at,
        source_collection_id=entity.source_collection_id,
        source_version=entity.source_version,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
