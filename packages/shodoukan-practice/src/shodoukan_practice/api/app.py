import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..domain.exceptions import DictionaryItemNotFoundError
from .routes import library_router, user_router

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
    app.include_router(library_router)
    app.include_router(user_router)
    app.add_exception_handler(DictionaryItemNotFoundError, _not_found)
    return app


async def _not_found(_: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)}
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("shodoukan_practice.api.app:app", port=PORT, reload=True)
