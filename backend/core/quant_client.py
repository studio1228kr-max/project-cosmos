"""
COSMOS Core — Quant Client

운용계가 계산계(Quant)를 호출할 때 이 모듈만 거친다.
지금은 같은 프로세스 안(모놀리식)이라 내부 함수 호출도 가능하지만,
나중에 Quant가 별도 Railway 서비스로 분리될 걸 대비해서
처음부터 HTTP 클라이언트로 짠다 (URL만 환경변수로 바꾸면 분리 끝).
"""
from __future__ import annotations
import os
import httpx

QUANT_BASE_URL = os.getenv("QUANT_SERVICE_URL", "http://localhost:8000")
# 분리 후에는 예: QUANT_SERVICE_URL=https://cosmos-quant.up.railway.app
# 같은 프로세스인 지금은 http://localhost:PORT 로 self-call 하거나,
# main.py에서 quant_router를 직접 mount했다면 내부 함수 호출로 대체 가능.

DEFAULT_TIMEOUT = 30.0  # 초 — Monte Carlo가 무거워지면 늘릴 것


class QuantClientError(Exception):
    pass


def evaluate_deal(engine_name: str, deal_master_id: int, inputs: dict) -> dict:
    """
    계산계의 /quant/evaluate_deal/{engine_name} 호출.
    반환값은 quant/schemas.py의 EngineResult를 그대로 dict로 받음.
    """
    url = f"{QUANT_BASE_URL}/quant/evaluate_deal/{engine_name}"
    payload = {"deal_master_id": deal_master_id, "inputs": inputs}

    try:
        resp = httpx.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise QuantClientError(
            f"엔진 '{engine_name}' 호출 실패 ({e.response.status_code}): {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise QuantClientError(f"계산계 연결 실패: {e}") from e

    return resp.json()


def list_available_engines() -> list[str]:
    url = f"{QUANT_BASE_URL}/quant/engines"
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    return resp.json().get("engines", [])
