from fastapi import FastAPI

from shodoukan_api.routes import entries, kanji, search


def create_app() -> FastAPI:
    app = FastAPI(title="Shodoukan API", version="0.1.0")
    app.include_router(search.router, prefix="/search", tags=["search"])
    app.include_router(entries.router, prefix="/entries", tags=["entries"])
    app.include_router(kanji.router, prefix="/kanji", tags=["kanji"])
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("shodoukan_api.app:app", host="0.0.0.0", port=8000)
