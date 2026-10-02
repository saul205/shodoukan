import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..domain.exceptions import (
    CollectionNameTakenError,
    DictionaryItemNotFoundError,
    EntityNotFoundError,
)
from .routes import (
    dictionary_router,
    entry_collection_router,
    kanji_collection_router,
    library_router,
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
    # The frontend calls this API from the browser with an Authorization
    # header, so it needs CORS (same variable as shodoukan-api).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(dictionary_router)
    app.include_router(library_router)
    app.include_router(user_router)
    app.include_router(entry_collection_router)
    app.include_router(kanji_collection_router)
    app.add_exception_handler(DictionaryItemNotFoundError, _not_found)
    # Repositories scope lookups to the user, so another user's collection
    # or item is "not found" too.
    app.add_exception_handler(EntityNotFoundError, _not_found)
    app.add_exception_handler(CollectionNameTakenError, _conflict)
    return app


async def _not_found(_: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)}
    )


async def _conflict(_: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)}
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("shodoukan_practice.api.app:app", port=PORT, reload=True)
