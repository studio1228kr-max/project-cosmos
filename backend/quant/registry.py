"""
COSMOS Quant Layer — Engine Registry

새 엔진(GPT가 만든 merton_kmv.py 등)을 추가할 때마다
이 파일 맨 아래에 import + register 한 줄만 추가하면 된다.
quant/api.py는 이 레지스트리만 보고 라우팅한다 — 엔진 늘어나도 api.py 안 건드림.
"""
from __future__ import annotations
from quant.base import QuantEngine

_ENGINE_REGISTRY: dict[str, QuantEngine] = {}


def register_engine(name: str, engine_instance: QuantEngine) -> None:
    if name in _ENGINE_REGISTRY:
        raise ValueError(f"엔진 '{name}'은 이미 등록되어 있음 — 이름 중복 확인")
    _ENGINE_REGISTRY[name] = engine_instance


def get_engine(name: str) -> QuantEngine:
    if name not in _ENGINE_REGISTRY:
        raise KeyError(
            f"엔진 '{name}' 없음. 등록된 엔진: {list(_ENGINE_REGISTRY.keys())}"
        )
    return _ENGINE_REGISTRY[name]


def list_engines() -> list[str]:
    return list(_ENGINE_REGISTRY.keys())


# ── 엔진 등록 구간 ──────────────────────────────────────────
# GPT가 quant/engines/merton_kmv.py 같은 파일을 완성하면
# 아래처럼 한 줄씩 추가만 하면 됨. (지금은 아직 엔진이 없어서 비워둠)
#
# from quant.engines.merton_kmv import MertonKMVEngine
# register_engine("merton_kmv", MertonKMVEngine())
#
# from quant.engines.cecl_engine import CECLEngine
# register_engine("cecl", CECLEngine())

from quant.engines.merton_kmv import MertonKMVEngine
register_engine("merton_kmv", MertonKMVEngine())

from quant.engines.cecl_engine import CECLEngine
register_engine("cecl_engine", CECLEngine())

from quant.engines.cox_hazard_engine import CoxHazardEngine
register_engine("cox_hazard_engine", CoxHazardEngine())
