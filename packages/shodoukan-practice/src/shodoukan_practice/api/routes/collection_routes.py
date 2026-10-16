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
    ImportEntryCollection,
    ImportKanjiCollection,
    PublishEntryCollection,
    PublishKanjiCollection,
    RemoveEntryFromCollection,
    RemoveKanjiFromCollection,
    UnpublishEntryCollection,
    UnpublishKanjiCollection,
    UpdateEntryCollection,
    UpdateEntryCollectionFromSource,
    UpdateKanjiCollection,
    UpdateKanjiCollectionFromSource,
)
from ...application.queries import (
    ExportEntryCollection,
    ExportKanjiCollection,
    GetEntryCollection,
    GetKanjiCollection,
    LatestEntrySourceVersions,
    LatestKanjiSourceVersions,
    ListEntryCollections,
    ListKanjiCollections,
    SearchEntries,
    SearchKanji,
)
from ...domain.clock import utc_now
from ...domain.entities import Collection
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_add_entry_to_collection,
    get_add_kanji_to_collection,
    get_create_entry_collection,
    get_create_kanji_collection,
    get_delete_entry_collection,
    get_delete_kanji_collection,
    get_export_entry_collection,
    get_export_kanji_collection,
    get_get_entry_collection,
    get_get_kanji_collection,
    get_import_entry_collection,
    get_import_kanji_collection,
    get_latest_entry_source_versions,
    get_latest_kanji_source_versions,
    get_list_entry_collections,
    get_list_kanji_collections,
    get_publish_entry_collection,
    get_publish_kanji_collection,
    get_remove_entry_from_collection,
    get_remove_kanji_from_collection,
    get_search_entries,
    get_search_kanji,
    get_unpublish_entry_collection,
    get_unpublish_kanji_collection,
    get_update_entry_collection,
    get_update_entry_collection_from_source,
    get_update_kanji_collection,
    get_update_kanji_collection_from_source,
)
from ..schemas import (
    CollectionRequest,
    CollectionResponse,
    EntryCollectionFile,
    EntryCollectionImportResponse,
    EntryCollectionUpdateResponse,
    KanjiCollectionFile,
    KanjiCollectionImportResponse,
    KanjiCollectionUpdateResponse,
    MeaningLang,
    PracticeEntryPageResponse,
    PracticeKanjiPageResponse,
    PublicationRequest,
    SearchText,
)

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {
        "description": "No such collection or item for this user."
    }
}
_TOO_BIG: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "description": "More items than an import takes (`MAX_SHARED_ITEMS`)."
    }
}
_NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {"description": "The user has a collection by that name."}
}

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
Active = Annotated[
    bool | None,
    Query(
        description="Only active (`true`) or inactive (`false`) items; all if omitted."
    ),
]

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
    latest: Annotated[
        LatestEntrySourceVersions, Depends(get_latest_entry_source_versions)
    ],
) -> list[CollectionResponse]:
    """The current user's entry collections, by name."""
    collections = use_case.execute(user.id)
    versions = latest.execute(user.id)
    session.commit()  # persists the user if this request created it
    return [_with_source(c, versions) for c in collections]


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
    latest: Annotated[
        LatestEntrySourceVersions, Depends(get_latest_entry_source_versions)
    ],
) -> CollectionResponse:
    """One of the current user's entry collections."""
    collection = use_case.execute(user.id, collection_id)
    versions = latest.execute(user.id)
    session.commit()
    return _with_source(collection, versions)


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
    response_model=PracticeEntryPageResponse,
    responses=_NOT_FOUND,
)
def list_entry_collection_items(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SearchEntries, Depends(get_search_entries)],
    q: SearchText = None,
    meaning_lang: MeaningLang = None,
    active: Active = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> PracticeEntryPageResponse:
    """A page of the collection's entries, in the order they were added.

    With `q`, only the matching ones, best match first.
    """
    page = use_case.execute(
        user.id,
        text=q,
        meaning_lang=meaning_lang,
        active=active,
        in_collection=collection_id,
        limit=limit,
        offset=offset,
    )
    session.commit()
    return PracticeEntryPageResponse.model_validate(page)


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


@entry_router.get(
    "/{collection_id}/export",
    response_model=EntryCollectionFile,
    responses={**_NOT_FOUND, **_TOO_BIG},
)
def export_entry_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ExportEntryCollection, Depends(get_export_entry_collection)],
) -> EntryCollectionFile:
    """The collection as a file to download and import back: every entries,
    active or not, with the user's own data (see `POST /import`)."""
    shared = use_case.execute(user.id, collection_id)
    session.commit()
    return EntryCollectionFile(
        format="shodoukan.collection",
        version=1,
        kind="entries",
        exported_at=utc_now(),
        collection=shared,
    )


@entry_router.post(
    "/import",
    response_model=EntryCollectionImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_entry_collection(
    body: EntryCollectionFile,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ImportEntryCollection, Depends(get_import_entry_collection)],
) -> EntryCollectionImportResponse:
    """Import an exported collection as a new collection (renamed "name (2)"
    if the name is taken).

    Entries already in the library are reused, keeping the user's
    data, and get the parts of their own the file adds; missing ones are
    imported from the dictionary with the file's flags and notes. What the
    dictionary no longer has is left out and listed in `missing`. All or
    nothing: an invalid file (422) imports nothing.
    """
    result = use_case.execute(user.id, body.collection)
    session.commit()
    return EntryCollectionImportResponse(
        collection=CollectionResponse.model_validate(result.collection),
        created=result.created,
        existing=result.existing,
        missing=result.missing,
    )


@entry_router.put(
    "/{collection_id}/publication",
    response_model=CollectionResponse,
    responses={**_NOT_FOUND, **_TOO_BIG},
)
def publish_entry_collection(
    collection_id: int,
    body: PublicationRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[PublishEntryCollection, Depends(get_publish_entry_collection)],
) -> CollectionResponse:
    """Publish a new version: a snapshot of its active items (notes only if
    `include_notes`) that any signed-in user can see and import."""
    collection = use_case.execute(user.id, collection_id, body.include_notes)
    session.commit()
    return CollectionResponse.model_validate(collection)


@entry_router.delete(
    "/{collection_id}/publication",
    response_model=CollectionResponse,
    responses=_NOT_FOUND,
)
def unpublish_entry_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        UnpublishEntryCollection, Depends(get_unpublish_entry_collection)
    ],
) -> CollectionResponse:
    """Make it private again; its last version is kept. Idempotent."""
    collection = use_case.execute(user.id, collection_id)
    session.commit()
    return CollectionResponse.model_validate(collection)


@entry_router.post(
    "/{collection_id}/update",
    response_model=EntryCollectionUpdateResponse,
    responses=_NOT_FOUND,
)
def update_entry_collection_from_source(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        UpdateEntryCollectionFromSource,
        Depends(get_update_entry_collection_from_source),
    ],
) -> EntryCollectionUpdateResponse:
    """Bring a copy of a public collection up to its source's latest version:
    what came from the source and is untouched follows it, what the user
    touched or added stays; dropped items leave the collection, not the
    library. A no-op when it's up to date; 404 if the source isn't public."""
    result = use_case.execute(user.id, collection_id)
    session.commit()
    return EntryCollectionUpdateResponse(
        collection=CollectionResponse.model_validate(result.collection),
        created=result.created,
        existing=result.existing,
        missing=result.missing,
        removed=result.removed,
    )


# --- Kanji collections ---


@kanji_router.get("", response_model=list[CollectionResponse])
def list_kanji_collections(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ListKanjiCollections, Depends(get_list_kanji_collections)],
    latest: Annotated[
        LatestKanjiSourceVersions, Depends(get_latest_kanji_source_versions)
    ],
) -> list[CollectionResponse]:
    """The current user's kanji collections, by name."""
    collections = use_case.execute(user.id)
    versions = latest.execute(user.id)
    session.commit()  # persists the user if this request created it
    return [_with_source(c, versions) for c in collections]


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
    latest: Annotated[
        LatestKanjiSourceVersions, Depends(get_latest_kanji_source_versions)
    ],
) -> CollectionResponse:
    """One of the current user's kanji collections."""
    collection = use_case.execute(user.id, collection_id)
    versions = latest.execute(user.id)
    session.commit()
    return _with_source(collection, versions)


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
    response_model=PracticeKanjiPageResponse,
    responses=_NOT_FOUND,
)
def list_kanji_collection_items(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SearchKanji, Depends(get_search_kanji)],
    q: SearchText = None,
    meaning_lang: MeaningLang = None,
    active: Active = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> PracticeKanjiPageResponse:
    """A page of the collection's kanji, in the order they were added.

    With `q`, only the matching ones, best match first.
    """
    page = use_case.execute(
        user.id,
        text=q,
        meaning_lang=meaning_lang,
        active=active,
        in_collection=collection_id,
        limit=limit,
        offset=offset,
    )
    session.commit()
    return PracticeKanjiPageResponse.model_validate(page)


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


@kanji_router.get(
    "/{collection_id}/export",
    response_model=KanjiCollectionFile,
    responses={**_NOT_FOUND, **_TOO_BIG},
)
def export_kanji_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ExportKanjiCollection, Depends(get_export_kanji_collection)],
) -> KanjiCollectionFile:
    """The collection as a file to download and import back: every kanji,
    active or not, with the user's own data (see `POST /import`)."""
    shared = use_case.execute(user.id, collection_id)
    session.commit()
    return KanjiCollectionFile(
        format="shodoukan.collection",
        version=1,
        kind="kanji",
        exported_at=utc_now(),
        collection=shared,
    )


@kanji_router.post(
    "/import",
    response_model=KanjiCollectionImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_kanji_collection(
    body: KanjiCollectionFile,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ImportKanjiCollection, Depends(get_import_kanji_collection)],
) -> KanjiCollectionImportResponse:
    """Import an exported collection as a new collection (renamed "name (2)"
    if the name is taken).

    Kanji already in the library are reused, keeping the user's
    data, and get the parts of their own the file adds; missing ones are
    imported from the dictionary with the file's flags and notes. What the
    dictionary no longer has is left out and listed in `missing`. All or
    nothing: an invalid file (422) imports nothing.
    """
    result = use_case.execute(user.id, body.collection)
    session.commit()
    return KanjiCollectionImportResponse(
        collection=CollectionResponse.model_validate(result.collection),
        created=result.created,
        existing=result.existing,
        missing=result.missing,
    )


@kanji_router.put(
    "/{collection_id}/publication",
    response_model=CollectionResponse,
    responses={**_NOT_FOUND, **_TOO_BIG},
)
def publish_kanji_collection(
    collection_id: int,
    body: PublicationRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[PublishKanjiCollection, Depends(get_publish_kanji_collection)],
) -> CollectionResponse:
    """Publish a new version: a snapshot of its active items (notes only if
    `include_notes`) that any signed-in user can see and import."""
    collection = use_case.execute(user.id, collection_id, body.include_notes)
    session.commit()
    return CollectionResponse.model_validate(collection)


@kanji_router.delete(
    "/{collection_id}/publication",
    response_model=CollectionResponse,
    responses=_NOT_FOUND,
)
def unpublish_kanji_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        UnpublishKanjiCollection, Depends(get_unpublish_kanji_collection)
    ],
) -> CollectionResponse:
    """Make it private again; its last version is kept. Idempotent."""
    collection = use_case.execute(user.id, collection_id)
    session.commit()
    return CollectionResponse.model_validate(collection)


@kanji_router.post(
    "/{collection_id}/update",
    response_model=KanjiCollectionUpdateResponse,
    responses=_NOT_FOUND,
)
def update_kanji_collection_from_source(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        UpdateKanjiCollectionFromSource,
        Depends(get_update_kanji_collection_from_source),
    ],
) -> KanjiCollectionUpdateResponse:
    """Bring a copy of a public collection up to its source's latest version:
    what came from the source and is untouched follows it, what the user
    touched or added stays; dropped items leave the collection, not the
    library. A no-op when it's up to date; 404 if the source isn't public."""
    result = use_case.execute(user.id, collection_id)
    session.commit()
    return KanjiCollectionUpdateResponse(
        collection=CollectionResponse.model_validate(result.collection),
        created=result.created,
        existing=result.existing,
        missing=result.missing,
        removed=result.removed,
    )


def _with_source(
    collection: Collection, versions: dict[int, int]
) -> CollectionResponse:
    """The collection's response, with its source's latest version if any."""
    response = CollectionResponse.model_validate(collection)
    response.latest_source_version = versions.get(response.id)
    return response
