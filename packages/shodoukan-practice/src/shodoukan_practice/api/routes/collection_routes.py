"""The user's collections: `/collections/entries` and `/collections/kanji`.

The two routers have the same shape; entry and kanji collections never mix.
Another user's collection or item is a 404, like a missing one.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from ...application.commands import (
    AddEntryToCollection,
    AddKanjiToCollection,
    CreateEntryCollection,
    CreateKanjiCollection,
    DeleteEntryCollection,
    DeleteKanjiCollection,
    RemoveEntryFromCollection,
    RemoveKanjiFromCollection,
    UpdateEntryCollection,
    UpdateKanjiCollection,
)
from ...application.queries import (
    GetEntryCollection,
    GetKanjiCollection,
    ListEntryCollectionItems,
    ListEntryCollections,
    ListKanjiCollectionItems,
    ListKanjiCollections,
)
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_add_entry_to_collection,
    get_add_kanji_to_collection,
    get_create_entry_collection,
    get_create_kanji_collection,
    get_delete_entry_collection,
    get_delete_kanji_collection,
    get_get_entry_collection,
    get_get_kanji_collection,
    get_list_entry_collection_items,
    get_list_entry_collections,
    get_list_kanji_collection_items,
    get_list_kanji_collections,
    get_remove_entry_from_collection,
    get_remove_kanji_from_collection,
    get_update_entry_collection,
    get_update_kanji_collection,
)
from ..schemas import (
    CollectionRequest,
    CollectionResponse,
    PracticeEntryResponse,
    PracticeKanjiResponse,
)

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {
        "description": "No such collection or item for this user."
    }
}
_NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {"description": "The user has a collection by that name."}
}

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]

entry_router = APIRouter(
    prefix="/collections/entries",
    tags=["collections"],
    responses=_UNAUTHORIZED,
)
kanji_router = APIRouter(
    prefix="/collections/kanji",
    tags=["collections"],
    responses=_UNAUTHORIZED,
)


# --- Entry collections ---


@entry_router.get("", response_model=list[CollectionResponse])
def list_entry_collections(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ListEntryCollections, Depends(get_list_entry_collections)],
) -> list[CollectionResponse]:
    """The current user's entry collections, by name."""
    collections = use_case.execute(user.id)
    session.commit()  # persists the user if this request created it
    return [CollectionResponse.model_validate(c) for c in collections]


@entry_router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_NAME_TAKEN,
)
def create_entry_collection(
    body: CollectionRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[CreateEntryCollection, Depends(get_create_entry_collection)],
) -> CollectionResponse:
    """Create an empty entry collection."""
    collection = use_case.execute(user.id, body.name, body.description)
    session.commit()
    return CollectionResponse.model_validate(collection)


@entry_router.get(
    "/{collection_id}", response_model=CollectionResponse, responses=_NOT_FOUND
)
def get_entry_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetEntryCollection, Depends(get_get_entry_collection)],
) -> CollectionResponse:
    """One of the current user's entry collections."""
    collection = use_case.execute(user.id, collection_id)
    session.commit()
    return CollectionResponse.model_validate(collection)


@entry_router.put(
    "/{collection_id}",
    response_model=CollectionResponse,
    responses={**_NOT_FOUND, **_NAME_TAKEN},
)
def update_entry_collection(
    collection_id: int,
    body: CollectionRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[UpdateEntryCollection, Depends(get_update_entry_collection)],
) -> CollectionResponse:
    """Replace the collection's name and description (send both)."""
    collection = use_case.execute(user.id, collection_id, body.name, body.description)
    session.commit()
    return CollectionResponse.model_validate(collection)


@entry_router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def delete_entry_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[DeleteEntryCollection, Depends(get_delete_entry_collection)],
) -> None:
    """Delete the collection. Its entries stay in the library."""
    use_case.execute(user.id, collection_id)
    session.commit()


@entry_router.get(
    "/{collection_id}/items",
    response_model=list[PracticeEntryResponse],
    responses=_NOT_FOUND,
)
def list_entry_collection_items(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        ListEntryCollectionItems, Depends(get_list_entry_collection_items)
    ],
    limit: Limit = 20,
    offset: Offset = 0,
) -> list[PracticeEntryResponse]:
    """A page of the collection's active entries, in the order they were added."""
    items = use_case.execute(user.id, collection_id, limit, offset)
    session.commit()
    return [PracticeEntryResponse.model_validate(item) for item in items]


@entry_router.put(
    "/{collection_id}/items/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def add_entry_to_collection(
    collection_id: int,
    entry_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddEntryToCollection, Depends(get_add_entry_to_collection)],
) -> None:
    """Put a library entry (its practice `id`) in the collection. Idempotent."""
    use_case.execute(user.id, collection_id, entry_id)
    session.commit()


@entry_router.delete(
    "/{collection_id}/items/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def remove_entry_from_collection(
    collection_id: int,
    entry_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        RemoveEntryFromCollection, Depends(get_remove_entry_from_collection)
    ],
) -> None:
    """Take the entry out of the collection; it stays in the library. Idempotent."""
    use_case.execute(user.id, collection_id, entry_id)
    session.commit()


# --- Kanji collections ---


@kanji_router.get("", response_model=list[CollectionResponse])
def list_kanji_collections(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ListKanjiCollections, Depends(get_list_kanji_collections)],
) -> list[CollectionResponse]:
    """The current user's kanji collections, by name."""
    collections = use_case.execute(user.id)
    session.commit()  # persists the user if this request created it
    return [CollectionResponse.model_validate(c) for c in collections]


@kanji_router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_NAME_TAKEN,
)
def create_kanji_collection(
    body: CollectionRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[CreateKanjiCollection, Depends(get_create_kanji_collection)],
) -> CollectionResponse:
    """Create an empty kanji collection."""
    collection = use_case.execute(user.id, body.name, body.description)
    session.commit()
    return CollectionResponse.model_validate(collection)


@kanji_router.get(
    "/{collection_id}", response_model=CollectionResponse, responses=_NOT_FOUND
)
def get_kanji_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetKanjiCollection, Depends(get_get_kanji_collection)],
) -> CollectionResponse:
    """One of the current user's kanji collections."""
    collection = use_case.execute(user.id, collection_id)
    session.commit()
    return CollectionResponse.model_validate(collection)


@kanji_router.put(
    "/{collection_id}",
    response_model=CollectionResponse,
    responses={**_NOT_FOUND, **_NAME_TAKEN},
)
def update_kanji_collection(
    collection_id: int,
    body: CollectionRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[UpdateKanjiCollection, Depends(get_update_kanji_collection)],
) -> CollectionResponse:
    """Replace the collection's name and description (send both)."""
    collection = use_case.execute(user.id, collection_id, body.name, body.description)
    session.commit()
    return CollectionResponse.model_validate(collection)


@kanji_router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def delete_kanji_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[DeleteKanjiCollection, Depends(get_delete_kanji_collection)],
) -> None:
    """Delete the collection. Its kanji stay in the library."""
    use_case.execute(user.id, collection_id)
    session.commit()


@kanji_router.get(
    "/{collection_id}/items",
    response_model=list[PracticeKanjiResponse],
    responses=_NOT_FOUND,
)
def list_kanji_collection_items(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        ListKanjiCollectionItems, Depends(get_list_kanji_collection_items)
    ],
    limit: Limit = 20,
    offset: Offset = 0,
) -> list[PracticeKanjiResponse]:
    """A page of the collection's active kanji, in the order they were added."""
    items = use_case.execute(user.id, collection_id, limit, offset)
    session.commit()
    return [PracticeKanjiResponse.model_validate(item) for item in items]


@kanji_router.put(
    "/{collection_id}/items/{kanji_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def add_kanji_to_collection(
    collection_id: int,
    kanji_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddKanjiToCollection, Depends(get_add_kanji_to_collection)],
) -> None:
    """Put a library kanji (its practice `id`) in the collection. Idempotent."""
    use_case.execute(user.id, collection_id, kanji_id)
    session.commit()


@kanji_router.delete(
    "/{collection_id}/items/{kanji_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def remove_kanji_from_collection(
    collection_id: int,
    kanji_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        RemoveKanjiFromCollection, Depends(get_remove_kanji_from_collection)
    ],
) -> None:
    """Take the kanji out of the collection; it stays in the library. Idempotent."""
    use_case.execute(user.id, collection_id, kanji_id)
    session.commit()
