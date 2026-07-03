"""Factory de la aplicación FastAPI."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.backend.api.router import register_routers
from app.backend.core.mcp_integration import combined_app_lifespan, mount_workspace_mcp
from app.backend.core.config import apply_settings_to_process_env, backend_env_path, resolve_cors_origins, settings
from app.backend.core.cors_utils import cors_headers_for_origin, is_origin_allowed


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        origin = request.headers.get("origin")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": exc.status_code,
                "message": exc.detail,
                "data": None,
            },
            headers=cors_headers_for_origin(origin),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        origin = request.headers.get("origin")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Internal server error: {str(exc)}",
                "data": None,
            },
            headers=cors_headers_for_origin(origin),
        )


def register_middleware(app: FastAPI) -> None:
    cors_origins, allow_credentials = resolve_cors_origins(settings.cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.middleware("http")
    async def ensure_cors_on_all_responses(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "OPTIONS" and is_origin_allowed(origin):
            return Response(
                status_code=204,
                headers={
                    **cors_headers_for_origin(origin),
                    "Access-Control-Allow-Methods": "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT",
                    "Access-Control-Allow-Headers": request.headers.get(
                        "access-control-request-headers", "*"
                    ),
                    "Access-Control-Max-Age": "600",
                },
            )
        response = await call_next(request)
        for key, value in cors_headers_for_origin(origin).items():
            response.headers[key] = value
        return response

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
    key = settings.openai_api_key
    if key:
        logging.getLogger(__name__).info(
            "OpenAI configurada (modelo=%s, key=…%s)",
            settings.agent_v2_model,
            key[-4:],
        )
    else:
        logging.getLogger(__name__).warning(
            "OPENAI_API_KEY no configurada en %s",
            backend_env_path(),
        )

    app = FastAPI(
        root_path=settings.api_root_path,
        title="PIE 360 API",
        description="API del proyecto PIE 360",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=combined_app_lifespan,
    )

    register_exception_handlers(app)
    register_middleware(app)

    files_dir = Path(settings.files_dir)
    files_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=str(files_dir)), name="files")

    register_routers(app)
    mount_workspace_mcp(app)
    return app
