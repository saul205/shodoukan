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
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from shodoukan import Dictionary

from ..application.commands import ImportEntry, ImportKanji
from ..application.queries import GetRegisteredUser
from ..domain.entities import User
from ..domain.exceptions import UserNotRegisteredError
from ..domain.gateways import DictionaryGateway
from ..infrastructure.db.connection import create_db_engine, create_session_factory
from ..infrastructure.dictionary import ShodoukanDictionaryGateway
from ..infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
    SqlAlchemyUserRepository,
)
from .auth import TokenVerifier

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

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    session: SessionDep,
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """The registered practice user behind the request's bearer token.

    401 for a missing or invalid token, 403 for a valid token whose user
    isn't registered.
    """
    if credentials is None:
        raise _unauthorized("missing bearer token")
    try:
        subject = verifier.subject(credentials.credentials)
    except jwt.PyJWTError as error:
        raise _unauthorized("invalid token") from error
    try:
        return GetRegisteredUser(SqlAlchemyUserRepository(session)).execute(subject)
    except UserNotRegisteredError as error:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="user not registered"
        ) from error


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_import_entry(
    session: SessionDep,
    dictionary: Annotated[DictionaryGateway, Depends(get_dictionary_gateway)],
) -> ImportEntry:
    return ImportEntry(dictionary, SqlAlchemyPracticeEntryRepository(session))


def get_import_kanji(
    session: SessionDep,
    dictionary: Annotated[DictionaryGateway, Depends(get_dictionary_gateway)],
) -> ImportKanji:
    return ImportKanji(dictionary, SqlAlchemyPracticeKanjiRepository(session))


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
