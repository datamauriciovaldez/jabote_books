"""Aplicación FastAPI: API + interfaz estática, todo en el mismo servidor local."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.errors import UserError
from app.jobs.runner import runner
from app.web.api import router

STATIC = Path(__file__).with_name("static")


@asynccontextmanager
async def lifespan(_: FastAPI):
    runner.recover()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AudioLibro Libre", version="0.1.0", lifespan=lifespan, docs_url="/api/docs",
                  openapi_url="/api/openapi.json")

    @app.exception_handler(UserError)
    async def user_error(_: Request, exc: UserError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={
            "error": {"code": exc.code, "detail": exc.detail, "params": exc.params}})

    app.include_router(router)
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app


app = create_app()
