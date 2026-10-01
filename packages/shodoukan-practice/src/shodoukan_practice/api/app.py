from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..domain.exceptions import DictionaryItemNotFoundError
from .routes import library_router


def create_app() -> FastAPI:
    app = FastAPI(title="shodoukan-practice")
    app.include_router(library_router)
    app.add_exception_handler(DictionaryItemNotFoundError, _not_found)
    return app


async def _not_found(_: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)}
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("shodoukan_practice.api.app:app", reload=True)
