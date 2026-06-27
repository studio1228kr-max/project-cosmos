"""
engines/registry.py
────────────────────
엔진 등록 단일 진입점.
엔진 추가 방법:
  1. engines/ 에 새 파일 생성, BaseEngine 구현
  2. _build_registry() 에 import 후 등록
  3. 끝 — 라우터 자동 인식
"""

from __future__ import annotations

from core.exceptions import EngineNotFoundError, EngineRegistryError
from core.logging_config import get_logger
from engines.base import BaseEngine

logger = get_logger("engine.registry")


def _build_registry() -> dict[str, BaseEngine]:
    registry: dict[str, BaseEngine] = {}

    try:
        from engines.ping_engine import PingEngine
        e = PingEngine()
        registry[e.name] = e
        logger.info("engine_registered", name=e.name, version=e.version)
    except Exception as exc:
        logger.error("engine_register_failed", engine="ping", error=str(exc))

    try:
        from engines.irr_engine import IRREngine
        e = IRREngine()
        registry[e.name] = e
        logger.info("engine_registered", name=e.name, version=e.version)
    except Exception as exc:
        logger.error("engine_register_failed", engine="irr_engine", error=str(exc))

    # 엔진 추가시 여기에만:
    # from engines.merton_kmv import MertonKMVEngine
    # from engines.behavioral_risk_engine import BehavioralRiskEngine

    return registry


_ENGINES: dict[str, BaseEngine] = _build_registry()


def get_engine(name: str) -> BaseEngine:
    if name not in _ENGINES:
        raise EngineNotFoundError(
            f"엔진 '{name}' 미등록",
            detail=f"사용 가능: {list(_ENGINES.keys())}",
        )
    return _ENGINES[name]


def list_engines() -> list[dict]:
    return [
        {
            "name": e.name,
            "version": e.version,
            "class": type(e).__name__,
        }
        for e in _ENGINES.values()
    ]


def register_engine(engine: BaseEngine) -> None:
    """런타임 동적 등록. 테스트·플러그인 용도."""
    if not isinstance(engine, BaseEngine):
        raise EngineRegistryError(
            "BaseEngine 하위 클래스만 등록 가능",
            detail=type(engine).__name__,
        )
    _ENGINES[engine.name] = engine
    logger.info("engine_registered_dynamic", name=engine.name, version=engine.version)
