from fastapi import FastAPI


def create_app() -> FastAPI:
    return FastAPI(title="shodoukan-practice")


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("shodoukan_practice.api.app:app", reload=True)
