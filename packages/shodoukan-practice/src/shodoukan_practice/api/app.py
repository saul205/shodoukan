import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..domain.exceptions import (
    CollectionNameTakenError,
    DictionaryItemNotFoundError,
    EntityNotFoundError,
    ExercisePoolTooSmallError,
    InvalidAnswerError,
    LastMeaningError,
    LastReadingError,
    OriginalDataError,
    QuestionNotActiveError,
    SenseLanguageError,
    SessionAlreadyOpenError,
    SessionFinishedError,
)
from .routes import (
    dictionary_router,
    entry_collection_router,
    exercise_router,
    exercise_session_router,
    exercise_statistics_router,
    health_router,
    kanji_collection_router,
    library_router,
    practice_entry_router,
    practice_kanji_router,
    user_router,
)

PORT = 8001  # shodoukan-api uses 8000


def create_app() -> FastAPI:
    app = FastAPI(
        title="shodoukan-practice",
        # Swagger UI "Authorize": sign in with Keycloak (authorization code +
        # PKCE) through a public client whose redirect URIs include
        # http://localhost:8001/docs/oauth2-redirect.
        swagger_ui_init_oauth={
            "clientId": os.environ.get("AUTH_SWAGGER_CLIENT_ID", "shodoukan-web"),
            "usePkceWithAuthorizationCodeGrant": True,
            "scopes": "openid profile",
        },
    )
    # The practice frontend (port 3001) calls this API from the browser with
    # an Authorization header, so it needs CORS (same variable as
    # shodoukan-api).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3001").split(","),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health_router)
    app.include_router(dictionary_router)
    app.include_router(library_router)
    app.include_router(practice_entry_router)
    app.include_router(practice_kanji_router)
    app.include_router(user_router)
    app.include_router(entry_collection_router)
    app.include_router(kanji_collection_router)
    app.include_router(exercise_router)
    app.include_router(exercise_session_router)
    app.include_router(exercise_statistics_router)
    app.add_exception_handler(DictionaryItemNotFoundError, _not_found)
    # Repositories scope lookups to the user, so another user's collection
    # or item is "not found" too.
    app.add_exception_handler(EntityNotFoundError, _not_found)
    app.add_exception_handler(CollectionNameTakenError, _conflict)
    # Dictionary data in the library can only be disabled, not changed.
    app.add_exception_handler(OriginalDataError, _conflict)
    # A word always keeps one reading, and a sense one meaning.
    app.add_exception_handler(LastReadingError, _conflict)
    app.add_exception_handler(LastMeaningError, _conflict)
    app.add_exception_handler(QuestionNotActiveError, _conflict)
    app.add_exception_handler(SessionFinishedError, _conflict)
    app.add_exception_handler(SessionAlreadyOpenError, _conflict)
    # Requests that are well formed but can't be done: too few items to build
    # an exercise session, an option the question doesn't have.
    app.add_exception_handler(ExercisePoolTooSmallError, _unprocessable_detail)
    app.add_exception_handler(InvalidAnswerError, _unprocessable_detail)
    # A meaning in another language than its sense's.
    app.add_exception_handler(SenseLanguageError, _unprocessable_detail)
    # Rules entities check when built or changed in a use case (e.g. exercise
    # settings that use fields of the other item kind), shaped like FastAPI's
    # own request validation errors.
    app.add_exception_handler(ValidationError, _unprocessable)
    return app


async def _not_found(_: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)}
    )


async def _conflict(_: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)}
    )


async def _unprocessable_detail(_: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(error)},
    )


async def _unprocessable(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, ValidationError)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": error.errors(
                include_url=False, include_context=False, include_input=False
            )
        },
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("shodoukan_practice.api.app:app", port=PORT, reload=True)
