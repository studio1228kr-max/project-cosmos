"""공통 Scanner Interface — scan → guardrail → dedupe → save → normalize → emit."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional

import db
import guardrail
from dedupe.signal_dedupe import is_duplicate, record_dedupe
from schemas.source_event_schema import NormalizedSignal, RawEvent  # re-export

__all__ = ["BaseScanner", "RawEvent", "NormalizedSignal"]


class BaseScanner(ABC):
    VERSION = "v0.1"

    @abstractmethod
    async def scan(self, **kwargs) -> List[RawEvent]:
        """원천 데이터 수집."""

    @abstractmethod
    async def normalize(self, raw_event: RawEvent) -> Optional[NormalizedSignal]:
        """표준 신호로 정규화."""

    async def emit(self, signal: NormalizedSignal) -> None:
        """Redis Stream publish."""
        from streams.redis_streams import publish_signal
        await publish_signal(signal)

    async def _is_duplicate(self, dedupe_key: str) -> bool:
        return await asyncio.to_thread(is_duplicate, dedupe_key)

    async def _save_raw_event(self, event: RawEvent) -> int:
        return await asyncio.to_thread(db.save_raw_event, event)

    async def _save_normalized(self, signal: NormalizedSignal) -> int:
        return await asyncio.to_thread(db.save_normalized, signal)

    async def run(self, **kwargs) -> dict:
        """scan → guardrail → dedupe → save → normalize → emit."""
        raw_events = await self.scan(**kwargs)
        hits, signals = [], []
        accepted = rejected = 0
        # Sprint #3: normalize 무관 — 스캔된 모든 corp_code 수집(재무 fetch 별도 루프 입력)
        corp_map = {e.entity_id: e.entity_name for e in raw_events if e.entity_id}

        for event in raw_events:
            verdict = guardrail.evaluate(event)
            hit = {
                "dedupe_key": event.dedupe_key,
                "entity_name": event.entity_name,
                "intake_status": verdict["intake_status"],
                "reason": verdict["reason"],
            }
            hits.append(hit)

            if verdict["intake_status"] == "REJECT":
                rejected += 1
                await asyncio.to_thread(
                    guardrail.record_rejection, event.dedupe_key, event.entity_name,
                    verdict["reason"] or "", self.__class__.__name__,
                )
                continue

            accepted += 1
            if await self._is_duplicate(event.dedupe_key):
                continue
            event_id = await self._save_raw_event(event)
            await asyncio.to_thread(record_dedupe, event.dedupe_key)

            signal = await self.normalize(event)
            if signal:
                signal.raw_event_id = event_id
                signal.normalized_id = await self._save_normalized(signal)
                await self.emit(signal)
                signals.append(signal)

        return {
            "scanned": len(raw_events),
            "emitted": len(signals),
            "hits": hits,
            "corp_map": corp_map,
            "intake_summary": {"accepted": accepted, "rejected": rejected},
            "scanner": self.__class__.__name__,
            "version": self.VERSION,
        }
