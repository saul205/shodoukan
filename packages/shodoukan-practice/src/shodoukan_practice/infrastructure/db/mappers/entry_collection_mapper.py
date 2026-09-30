from ....domain.entities import EntryCollection
from ..orm import EntryCollectionORM


def entry_collection_to_domain(row: EntryCollectionORM) -> EntryCollection:
    return EntryCollection(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def entry_collection_to_db(entity: EntryCollection) -> EntryCollectionORM:
    return EntryCollectionORM(
        id=entity.id,
        user_id=entity.user_id,
        name=entity.name,
        description=entity.description,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
