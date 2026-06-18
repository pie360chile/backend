"""Factory de la aplicación FastAPI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.backend.api.router import register_routers
from app.backend.core.config import apply_settings_to_process_env, settings


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": exc.status_code,
                "message": exc.detail,
                "data": None,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Internal server error: {str(exc)}",
                "data": None,
            },
        )


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def period_year_middleware(request: Request, call_next):
        raw = request.query_params.get("period_year")
        if raw is not None and str(raw).strip() != "":
            try:
                request.state.period_year = int(raw)
            except ValueError:
                request.state.period_year = None
        else:
            request.state.period_year = None
        return await call_next(request)


def create_app() -> FastAPI:
    apply_settings_to_process_env()

    app = FastAPI(
        root_path=settings.api_root_path,
        title="PIE 360 API",
        description="API del proyecto PIE 360",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    register_exception_handlers(app)
    register_middleware(app)

    files_dir = Path(settings.files_dir)
    files_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=str(files_dir)), name="files")

    register_routers(app)
    return app
