"""Public collections: `/public-collections/entries` and `/public-collections/kanji`.

Any signed-in user can search them, preview their published version and
import it. A private (or missing) collection is a 404, to its owner too:
they manage it under `/collections`.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from ...application.commands import (
    ImportPublicEntryCollection,
    ImportPublicKanjiCollection,
)
from ...application.queries import (
    GetPublicEntryCollection,
    GetPublicKanjiCollection,
    PreviewPublicEntryCollection,
    PreviewPublicKanjiCollection,
    SearchPublicEntryCollections,
    SearchPublicKanjiCollections,
)
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_get_public_entry_collection,
    get_get_public_kanji_collection,
    get_import_public_entry_collection,
    get_import_public_kanji_collection,
    get_preview_public_entry_collection,
    get_preview_public_kanji_collection,
    get_search_public_entry_collections,
    get_search_public_kanji_collections,
)
from ..schemas import (
    CollectionResponse,
    EntryCollectionImportResponse,
    EntryPreviewPageResponse,
    KanjiCollectionImportResponse,
    PracticeKanjiPageResponse,
    PublicCollectionPageResponse,
    PublicCollectionResponse,
    PublicOwnerQuery,
    PublicSortQuery,
    SearchText,
    preview_ids,
)

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No such public collection."}
}

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
Owner = Annotated[
    PublicOwnerQuery,
    Query(description="The current user's (`mine`), everybody else's, or `all`."),
]
Sort = Annotated[PublicSortQuery, Query()]
# Ids for a preview's unstored items: far apart, so no two items share one.
_PREVIEW_ID_SPAN = 1_000_000

entry_router = APIRouter(
    prefix="/public-collections/entries",
    tags=["public collections"],
    responses=_UNAUTHORIZED,
)
kanji_router = APIRouter(
    prefix="/public-collections/kanji",
    tags=["public collections"],
    responses=_UNAUTHORIZED,
)


@entry_router.get("", response_model=PublicCollectionPageResponse)
def search_public_entry_collections(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        SearchPublicEntryCollections, Depends(get_search_public_entry_collections)
    ],
    q: SearchText = None,
    owner: Owner = "all",
    sort: Sort = "popular",
    limit: Limit = 20,
    offset: Offset = 0,
) -> PublicCollectionPageResponse:
    """A page of public entries collections. `q` looks in the name, the
    description and the owner's username (case-insensitive)."""
    page = use_case.execute(user.id, q, owner, sort, limit, offset)
    session.commit()
    return PublicCollectionPageResponse(
        items=[PublicCollectionResponse.from_summary(s, user.id) for s in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@entry_router.get(
    "/{collection_id}", response_model=PublicCollectionResponse, responses=_NOT_FOUND
)
def get_public_entry_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        GetPublicEntryCollection, Depends(get_get_public_entry_collection)
    ],
) -> PublicCollectionResponse:
    """A public collection, with its owner and counts."""
    summary = use_case.execute(user.id, collection_id)
    session.commit()
    return PublicCollectionResponse.from_summary(summary, user.id)


@entry_router.get(
    "/{collection_id}/items",
    response_model=EntryPreviewPageResponse,
    responses=_NOT_FOUND,
)
def preview_public_entry_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        PreviewPublicEntryCollection, Depends(get_preview_public_entry_collection)
    ],
    limit: Limit = 20,
    offset: Offset = 0,
) -> EntryPreviewPageResponse:
    """A page of its published version, each item as importing it would give
    it to the current user, with the sentences it brings. They aren't
    stored: their ids only tell them apart on the page."""
    page = use_case.execute(user.id, collection_id, limit, offset)
    session.commit()
    items = [
        preview_ids(
            {
                **preview.entry.model_dump(),
                "sentences": [s.model_dump() for s in preview.sentences],
            },
            (offset + i) * _PREVIEW_ID_SPAN + 1,
        )
        for i, preview in enumerate(page.items)
    ]
    return EntryPreviewPageResponse.model_validate(
        {"items": items, "total": page.total, "limit": limit, "offset": offset}
    )


@entry_router.post(
    "/{collection_id}/import",
    response_model=EntryCollectionImportResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_NOT_FOUND,
)
def import_public_entry_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        ImportPublicEntryCollection, Depends(get_import_public_entry_collection)
    ],
) -> EntryCollectionImportResponse:
    """Import its published version as a new collection of the current user's,
    like an exported file (`POST /collections/entries/import`). The download
    is counted unless it's the user's own."""
    result = use_case.execute(user.id, collection_id)
    session.commit()
    return EntryCollectionImportResponse(
        collection=CollectionResponse.model_validate(result.collection),
        created=result.created,
        existing=result.existing,
        missing=result.missing,
    )


@kanji_router.get("", response_model=PublicCollectionPageResponse)
def search_public_kanji_collections(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        SearchPublicKanjiCollections, Depends(get_search_public_kanji_collections)
    ],
    q: SearchText = None,
    owner: Owner = "all",
    sort: Sort = "popular",
    limit: Limit = 20,
    offset: Offset = 0,
) -> PublicCollectionPageResponse:
    """A page of public kanji collections. `q` looks in the name, the
    description and the owner's username (case-insensitive)."""
    page = use_case.execute(user.id, q, owner, sort, limit, offset)
    session.commit()
    return PublicCollectionPageResponse(
        items=[PublicCollectionResponse.from_summary(s, user.id) for s in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@kanji_router.get(
    "/{collection_id}", response_model=PublicCollectionResponse, responses=_NOT_FOUND
)
def get_public_kanji_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        GetPublicKanjiCollection, Depends(get_get_public_kanji_collection)
    ],
) -> PublicCollectionResponse:
    """A public collection, with its owner and counts."""
    summary = use_case.execute(user.id, collection_id)
    session.commit()
    return PublicCollectionResponse.from_summary(summary, user.id)


@kanji_router.get(
    "/{collection_id}/items",
    response_model=PracticeKanjiPageResponse,
    responses=_NOT_FOUND,
)
def preview_public_kanji_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        PreviewPublicKanjiCollection, Depends(get_preview_public_kanji_collection)
    ],
    limit: Limit = 20,
    offset: Offset = 0,
) -> PracticeKanjiPageResponse:
    """A page of its published version, each item as importing it would give
    it to the current user. They aren't stored: their ids only tell them
    apart on the page."""
    page = use_case.execute(user.id, collection_id, limit, offset)
    session.commit()
    items = [
        preview_ids(item.model_dump(), (offset + i) * _PREVIEW_ID_SPAN + 1)
        for i, item in enumerate(page.items)
    ]
    return PracticeKanjiPageResponse.model_validate(
        {"items": items, "total": page.total, "limit": limit, "offset": offset}
    )


@kanji_router.post(
    "/{collection_id}/import",
    response_model=KanjiCollectionImportResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_NOT_FOUND,
)
def import_public_kanji_collection(
    collection_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[
        ImportPublicKanjiCollection, Depends(get_import_public_kanji_collection)
    ],
) -> KanjiCollectionImportResponse:
    """Import its published version as a new collection of the current user's,
    like an exported file (`POST /collections/kanji/import`). The download
    is counted unless it's the user's own."""
    result = use_case.execute(user.id, collection_id)
    session.commit()
    return KanjiCollectionImportResponse(
        collection=CollectionResponse.model_validate(result.collection),
        created=result.created,
        existing=result.existing,
        missing=result.missing,
    )
