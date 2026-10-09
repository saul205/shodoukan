"""Dependency wiring: concrete infrastructure behind the domain ports.

One SQLAlchemy `Session` per request, shared by every repository the request
uses. Routes commit explicitly after their use case succeeds; anything not
committed is rolled back when the session closes.
"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy.orm import Session, sessionmaker

from shodoukan import Dictionary

from ..application.commands import (
    AddEntryExample,
    AddEntryGloss,
    AddEntryReading,
    AddEntrySense,
    AddEntrySpelling,
    AddEntryToCollection,
    AddKanjiMeaning,
    AddKanjiToCollection,
    AnswerExerciseQuestion,
    CreateEntryCollection,
    CreateExercise,
    CreateKanjiCollection,
    CreateOwnEntry,
    DeleteEntryCollection,
    DeleteExercise,
    DeleteKanjiCollection,
    EditEntryExample,
    EditEntryGloss,
    EditKanjiMeaning,
    EnsureUser,
    FinishExerciseSession,
    ImportEntry,
    ImportKanji,
    RemoveEntryExample,
    RemoveEntryFromCollection,
    RemoveEntryFromLibrary,
    RemoveEntryGloss,
    RemoveEntryReading,
    RemoveEntrySense,
    RemoveEntrySpelling,
    RemoveKanjiFromCollection,
    RemoveKanjiFromLibrary,
    RemoveKanjiMeaning,
    SetEntryActive,
    SetEntryNotes,
    SetEntryPartEnabled,
    SetKanjiActive,
    SetKanjiNotes,
    SetKanjiPartEnabled,
    SetSenseNotes,
    StartExerciseSession,
    UpdateEntryCollection,
    UpdateExercise,
    UpdateKanjiCollection,
)
from ..application.queries import (
    GetDictionaryEntry,
    GetDictionaryKanji,
    GetDictionaryKanjiStrokes,
    GetEntryCollection,
    GetExercise,
    GetExerciseSession,
    GetExerciseStatistics,
    GetImportStatus,
    GetKanjiCollection,
    GetLibraryEntry,
    GetLibraryKanji,
    GetPracticeStatistics,
    ListCollectionsOfEntry,
    ListCollectionsOfKanji,
    ListEntriesForKanji,
    ListEntryCollections,
    ListExercises,
    ListExerciseSessions,
    ListKanjiCollections,
    ListKanjiForEntry,
    SearchDictionary,
    SearchEntries,
    SearchKanji,
)
from ..domain.entities import User
from ..domain.gateways import DictionaryGateway, KanaGateway
from ..infrastructure.db.connection import create_db_engine, create_session_factory
from ..infrastructure.dictionary import (
    ShodoukanDictionaryGateway,
    ShodoukanKanaGateway,
)
from ..infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyExerciseStatisticsRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
    SqlAlchemyUserRepository,
)
from .auth import (
    DEFAULT_ISSUER,
    TokenVerifier,
    authorization_url,
    issuer_from_env,
    token_url,
)

# --- Infrastructure singletons (one per process) ---


@lru_cache(maxsize=1)
def _get_dictionary() -> Dictionary:
    # Read-only and safe to share: one instance per process. The database
    # path comes from SHODOUKAN_DB_PATH (or the library's default); it's
    # downloaded on first use if missing, as in shodoukan-api.
    return Dictionary()


@lru_cache(maxsize=1)
def _get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(create_db_engine())


@lru_cache(maxsize=1)
def get_token_verifier() -> TokenVerifier:
    return TokenVerifier.from_env()


# --- Per-request dependencies ---


def get_session() -> Iterator[Session]:
    with _get_session_factory()() as session:
        yield session


def get_dictionary_gateway() -> DictionaryGateway:
    return ShodoukanDictionaryGateway(_get_dictionary())


SessionDep = Annotated[Session, Depends(get_session)]

# Declares the OAuth2 flow (authorization code + PKCE) in the OpenAPI schema, so
# the Swagger UI can sign in with Keycloak. It only extracts the bearer token;
# TokenVerifier does the checking. The URLs are for the docs only, so they fall
# back to the local realm when AUTH_ISSUER isn't set (e.g. in tests).
_issuer_for_docs = issuer_from_env() or DEFAULT_ISSUER
_oauth2 = OAuth2AuthorizationCodeBearer(
    authorizationUrl=authorization_url(_issuer_for_docs),
    tokenUrl=token_url(_issuer_for_docs),
    scopes={"openid": "OpenID Connect", "profile": "Username"},
    auto_error=False,
)


def get_current_user(
    session: SessionDep,
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    token: Annotated[str | None, Depends(_oauth2)],
) -> User:
    """The practice user behind the request's bearer token.

    401 for a missing or invalid token. A valid token from an identity
    without a practice user creates it (see EnsureUser); the route's commit
    persists it.
    """
    if token is None:
        raise _unauthorized("missing bearer token")
    try:
        identity = verifier.identity(token)
    except jwt.PyJWTError as error:
        raise _unauthorized("invalid token") from error
    users = SqlAlchemyUserRepository(session)
    return EnsureUser(users).execute(identity.user_id, identity.username)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_create_own_entry(session: SessionDep) -> CreateOwnEntry:
    return CreateOwnEntry(
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
    )


def get_import_entry(
    session: SessionDep,
    dictionary: Annotated[DictionaryGateway, Depends(get_dictionary_gateway)],
) -> ImportEntry:
    return ImportEntry(
        dictionary,
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
    )


def get_import_kanji(
    session: SessionDep,
    dictionary: Annotated[DictionaryGateway, Depends(get_dictionary_gateway)],
) -> ImportKanji:
    return ImportKanji(
        dictionary,
        SqlAlchemyPracticeKanjiRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


def get_search_dictionary(
    dictionary: Annotated[DictionaryGateway, Depends(get_dictionary_gateway)],
) -> SearchDictionary:
    return SearchDictionary(dictionary)


DictionaryGatewayDep = Annotated[DictionaryGateway, Depends(get_dictionary_gateway)]


def get_get_dictionary_entry(dictionary: DictionaryGatewayDep) -> GetDictionaryEntry:
    return GetDictionaryEntry(dictionary)


def get_get_dictionary_kanji(dictionary: DictionaryGatewayDep) -> GetDictionaryKanji:
    return GetDictionaryKanji(dictionary)


def get_get_dictionary_kanji_strokes(
    dictionary: DictionaryGatewayDep,
) -> GetDictionaryKanjiStrokes:
    return GetDictionaryKanjiStrokes(dictionary)


def get_list_entries_for_kanji(dictionary: DictionaryGatewayDep) -> ListEntriesForKanji:
    return ListEntriesForKanji(dictionary)


def get_list_kanji_for_entry(dictionary: DictionaryGatewayDep) -> ListKanjiForEntry:
    return ListKanjiForEntry(dictionary)


def get_import_status(session: SessionDep) -> GetImportStatus:
    return GetImportStatus(
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def get_kana_gateway() -> KanaGateway:
    return ShodoukanKanaGateway()


KanaGatewayDep = Annotated[KanaGateway, Depends(get_kana_gateway)]


def get_search_entries(session: SessionDep, kana: KanaGatewayDep) -> SearchEntries:
    return SearchEntries(
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        kana,
    )


def get_search_kanji(session: SessionDep, kana: KanaGatewayDep) -> SearchKanji:
    return SearchKanji(
        SqlAlchemyPracticeKanjiRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
        kana,
    )


# --- Library items ---


def get_add_entry_example(session: SessionDep) -> AddEntryExample:
    return AddEntryExample(SqlAlchemyPracticeEntryRepository(session))


def get_edit_entry_example(session: SessionDep) -> EditEntryExample:
    return EditEntryExample(SqlAlchemyPracticeEntryRepository(session))


def get_remove_entry_example(session: SessionDep) -> RemoveEntryExample:
    return RemoveEntryExample(SqlAlchemyPracticeEntryRepository(session))


def get_add_entry_gloss(session: SessionDep) -> AddEntryGloss:
    return AddEntryGloss(SqlAlchemyPracticeEntryRepository(session))


def get_add_entry_spelling(session: SessionDep) -> AddEntrySpelling:
    return AddEntrySpelling(SqlAlchemyPracticeEntryRepository(session))


def get_remove_entry_spelling(session: SessionDep) -> RemoveEntrySpelling:
    return RemoveEntrySpelling(SqlAlchemyPracticeEntryRepository(session))


def get_add_entry_reading(session: SessionDep) -> AddEntryReading:
    return AddEntryReading(SqlAlchemyPracticeEntryRepository(session))


def get_remove_entry_reading(session: SessionDep) -> RemoveEntryReading:
    return RemoveEntryReading(SqlAlchemyPracticeEntryRepository(session))


def get_add_entry_sense(session: SessionDep) -> AddEntrySense:
    return AddEntrySense(SqlAlchemyPracticeEntryRepository(session))


def get_edit_entry_gloss(session: SessionDep) -> EditEntryGloss:
    return EditEntryGloss(SqlAlchemyPracticeEntryRepository(session))


def get_remove_entry_from_library(session: SessionDep) -> RemoveEntryFromLibrary:
    return RemoveEntryFromLibrary(SqlAlchemyPracticeEntryRepository(session))


def get_remove_entry_gloss(session: SessionDep) -> RemoveEntryGloss:
    return RemoveEntryGloss(SqlAlchemyPracticeEntryRepository(session))


def get_remove_entry_sense(session: SessionDep) -> RemoveEntrySense:
    return RemoveEntrySense(SqlAlchemyPracticeEntryRepository(session))


def get_set_entry_active(session: SessionDep) -> SetEntryActive:
    return SetEntryActive(SqlAlchemyPracticeEntryRepository(session))


def get_set_entry_notes(session: SessionDep) -> SetEntryNotes:
    return SetEntryNotes(SqlAlchemyPracticeEntryRepository(session))


def get_set_entry_part_enabled(session: SessionDep) -> SetEntryPartEnabled:
    return SetEntryPartEnabled(SqlAlchemyPracticeEntryRepository(session))


def get_set_sense_notes(session: SessionDep) -> SetSenseNotes:
    return SetSenseNotes(SqlAlchemyPracticeEntryRepository(session))


def get_add_kanji_meaning(session: SessionDep) -> AddKanjiMeaning:
    return AddKanjiMeaning(SqlAlchemyPracticeKanjiRepository(session))


def get_edit_kanji_meaning(session: SessionDep) -> EditKanjiMeaning:
    return EditKanjiMeaning(SqlAlchemyPracticeKanjiRepository(session))


def get_remove_kanji_from_library(session: SessionDep) -> RemoveKanjiFromLibrary:
    return RemoveKanjiFromLibrary(SqlAlchemyPracticeKanjiRepository(session))


def get_remove_kanji_meaning(session: SessionDep) -> RemoveKanjiMeaning:
    return RemoveKanjiMeaning(SqlAlchemyPracticeKanjiRepository(session))


def get_set_kanji_active(session: SessionDep) -> SetKanjiActive:
    return SetKanjiActive(SqlAlchemyPracticeKanjiRepository(session))


def get_set_kanji_notes(session: SessionDep) -> SetKanjiNotes:
    return SetKanjiNotes(SqlAlchemyPracticeKanjiRepository(session))


def get_set_kanji_part_enabled(session: SessionDep) -> SetKanjiPartEnabled:
    return SetKanjiPartEnabled(SqlAlchemyPracticeKanjiRepository(session))


def get_get_library_entry(session: SessionDep) -> GetLibraryEntry:
    return GetLibraryEntry(SqlAlchemyPracticeEntryRepository(session))


def get_get_library_kanji(session: SessionDep) -> GetLibraryKanji:
    return GetLibraryKanji(SqlAlchemyPracticeKanjiRepository(session))


def get_list_collections_of_entry(session: SessionDep) -> ListCollectionsOfEntry:
    return ListCollectionsOfEntry(
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
    )


def get_list_collections_of_kanji(session: SessionDep) -> ListCollectionsOfKanji:
    return ListCollectionsOfKanji(
        SqlAlchemyPracticeKanjiRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


# --- Collections ---


def get_list_entry_collections(session: SessionDep) -> ListEntryCollections:
    return ListEntryCollections(SqlAlchemyEntryCollectionRepository(session))


def get_get_entry_collection(session: SessionDep) -> GetEntryCollection:
    return GetEntryCollection(SqlAlchemyEntryCollectionRepository(session))


def get_create_entry_collection(session: SessionDep) -> CreateEntryCollection:
    return CreateEntryCollection(SqlAlchemyEntryCollectionRepository(session))


def get_update_entry_collection(session: SessionDep) -> UpdateEntryCollection:
    return UpdateEntryCollection(SqlAlchemyEntryCollectionRepository(session))


def get_delete_entry_collection(session: SessionDep) -> DeleteEntryCollection:
    return DeleteEntryCollection(SqlAlchemyEntryCollectionRepository(session))


def get_add_entry_to_collection(session: SessionDep) -> AddEntryToCollection:
    return AddEntryToCollection(
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
    )


def get_remove_entry_from_collection(session: SessionDep) -> RemoveEntryFromCollection:
    return RemoveEntryFromCollection(
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
    )


def get_list_kanji_collections(session: SessionDep) -> ListKanjiCollections:
    return ListKanjiCollections(SqlAlchemyKanjiCollectionRepository(session))


def get_get_kanji_collection(session: SessionDep) -> GetKanjiCollection:
    return GetKanjiCollection(SqlAlchemyKanjiCollectionRepository(session))


def get_create_kanji_collection(session: SessionDep) -> CreateKanjiCollection:
    return CreateKanjiCollection(SqlAlchemyKanjiCollectionRepository(session))


def get_update_kanji_collection(session: SessionDep) -> UpdateKanjiCollection:
    return UpdateKanjiCollection(SqlAlchemyKanjiCollectionRepository(session))


def get_delete_kanji_collection(session: SessionDep) -> DeleteKanjiCollection:
    return DeleteKanjiCollection(SqlAlchemyKanjiCollectionRepository(session))


def get_add_kanji_to_collection(session: SessionDep) -> AddKanjiToCollection:
    return AddKanjiToCollection(
        SqlAlchemyKanjiCollectionRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def get_remove_kanji_from_collection(session: SessionDep) -> RemoveKanjiFromCollection:
    return RemoveKanjiFromCollection(
        SqlAlchemyKanjiCollectionRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


# --- Exercises ---


def get_list_exercises(session: SessionDep) -> ListExercises:
    return ListExercises(SqlAlchemyExerciseRepository(session))


def get_get_exercise(session: SessionDep) -> GetExercise:
    return GetExercise(SqlAlchemyExerciseRepository(session))


def get_create_exercise(session: SessionDep) -> CreateExercise:
    return CreateExercise(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


def get_update_exercise(session: SessionDep) -> UpdateExercise:
    return UpdateExercise(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


def get_delete_exercise(session: SessionDep) -> DeleteExercise:
    return DeleteExercise(SqlAlchemyExerciseRepository(session))


# --- Exercise sessions ---


def get_start_exercise_session(
    session: SessionDep, dictionary: DictionaryGatewayDep
) -> StartExerciseSession:
    return StartExerciseSession(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyExerciseSessionRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
        dictionary,
        SqlAlchemyUserRepository(session),
    )


def get_answer_exercise_question(
    session: SessionDep, dictionary: DictionaryGatewayDep
) -> AnswerExerciseQuestion:
    return AnswerExerciseQuestion(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyExerciseSessionRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
        dictionary,
    )


def get_finish_exercise_session(session: SessionDep) -> FinishExerciseSession:
    return FinishExerciseSession(SqlAlchemyExerciseSessionRepository(session))


def get_get_exercise_session(session: SessionDep) -> GetExerciseSession:
    return GetExerciseSession(SqlAlchemyExerciseSessionRepository(session))


def get_list_exercise_sessions(session: SessionDep) -> ListExerciseSessions:
    return ListExerciseSessions(SqlAlchemyExerciseSessionRepository(session))


# --- Statistics ---


def get_get_exercise_statistics(session: SessionDep) -> GetExerciseStatistics:
    return GetExerciseStatistics(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyExerciseStatisticsRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def get_get_practice_statistics(session: SessionDep) -> GetPracticeStatistics:
    return GetPracticeStatistics(
        SqlAlchemyExerciseStatisticsRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
