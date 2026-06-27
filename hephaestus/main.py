"""
HEPHAESTUS — COSMOS 계산계
──────────────────────────
Railway 서비스: hephaestus
역할: 수치 계산 엔진 전용 서버

3계 구조:
  COSMOS      (project-cosmos)  ← 운용계
  HERMES      (data-pipeline)   ← 인프라계
  HEPHAESTUS  (hephaestus)      ← 계산계  ← 여기
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.exceptions import HephaestusError
from core.logging_config import get_logger, setup_logging
from middleware.logging_middleware import LoggingMiddleware
from routers.engines import router as engines_router
from routers.health import router as health_router

setup_logging()
logger = get_logger("hephaestus.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "hephaestus_startup",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        environment=settings.ENVIRONMENT,
    )

    from engines.registry import list_engines
    engines = list_engines()
    logger.info(
        "engine_registry_loaded",
        count=len(engines),
        engines=[e["name"] for e in engines],
    )

    yield

    logger.info("hephaestus_shutdown")


app = FastAPI(
    title="HEPHAESTUS",
    description="COSMOS 계산계 — 수치 엔진 전용 서버",
    version=settings.SERVICE_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"]
        if settings.ENVIRONMENT == "development"
        else [
            "https://cosmos.luskacapital.com",
            "http://project-cosmos.railway.internal",
        ]
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(engines_router)


@app.exception_handler(HephaestusError)
async def hephaestus_error_handler(request: Request, exc: HephaestusError):
    logger.warning(
        "hephaestus_error",
        error_code=exc.error_code,
        message=exc.message,
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "예상치 못한 오류"},
    )
