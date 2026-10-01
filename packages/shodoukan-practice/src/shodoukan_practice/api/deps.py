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

from ..application.commands import EnsureUser, ImportEntry, ImportKanji
from ..application.queries import GetImportStatus, SearchDictionary
from ..domain.entities import User
from ..domain.gateways import DictionaryGateway
from ..infrastructure.db.connection import create_db_engine, create_session_factory
from ..infrastructure.dictionary import ShodoukanDictionaryGateway
from ..infrastructure.repositories import (
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


def get_search_dictionary(
    dictionary: Annotated[DictionaryGateway, Depends(get_dictionary_gateway)],
) -> SearchDictionary:
    return SearchDictionary(dictionary)


def get_import_status(session: SessionDep) -> GetImportStatus:
    return GetImportStatus(
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
