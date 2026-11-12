"""Aplicación FastAPI: API + interfaz estática, todo en el mismo servidor local."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.errors import UserError
from app.jobs.runner import runner
from app.web.api import router

STATIC = Path(__file__).with_name("static")
ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(_: FastAPI):
    runner.recover()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AudioLibro Libre", version=__version__, lifespan=lifespan, docs_url="/api/docs",
                  openapi_url="/api/openapi.json")

    @app.exception_handler(UserError)
    async def user_error(_: Request, exc: UserError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={
            "error": {"code": exc.code, "detail": exc.detail, "params": exc.params}})

    @app.get("/licencias", include_in_schema=False)
    async def licenses() -> PlainTextResponse:
        """Muestra LICENSES.md dentro de la app (dependencias y voces con su licencia)."""
        f = ROOT / "LICENSES.md"
        if not f.is_file():
            return PlainTextResponse("LICENSES.md no está disponible en esta instalación.", status_code=404)
        return PlainTextResponse(f.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")

    app.include_router(router)
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app


app = create_app()
