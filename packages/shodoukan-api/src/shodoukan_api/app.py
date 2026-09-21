import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shodoukan_api.routes import entries, kanji, search


def create_app() -> FastAPI:
    app = FastAPI(title="Shodoukan API", version="0.2.0")

    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(search.router, prefix="/search", tags=["search"])
    app.include_router(entries.router, prefix="/entries", tags=["entries"])
    app.include_router(kanji.router, prefix="/kanji", tags=["kanji"])
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("shodoukan_api.app:app", host="0.0.0.0", port=8000)
