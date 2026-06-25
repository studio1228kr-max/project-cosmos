"""Signal Contract — RawEvent / NormalizedSignal 표준 dataclass."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RawEvent:
    source: str
    source_ref_id: str
    source_url: Optional[str]
    observed_at: Optional[datetime]
    entity_name: str
    entity_id: Optional[str]
    entity_type: str          # CORP / ASSET / CASE / COLLATERAL
    raw_content: str
    dedupe_key: str
    scanner_version: str
    raw_json: Optional[dict] = None   # Raw Data Lake 원문 (v2.9)


@dataclass
class NormalizedSignal:
    source: str
    entity_name: str
    entity_id: Optional[str]
    signal_type: str
    signal_subtype: Optional[str]
    normalized_summary: str
    severity: str             # INFO / WATCH / REVIEW / CRITICAL / FATAL
    confidence: float         # 0.0 ~ 1.0
    evidence_quality: str     # PUBLIC / OFFICIAL / VENDOR / MANUAL / UNVERIFIED
    observed_at: Optional[datetime]
    raw_event_id: Optional[int] = None
    normalized_id: Optional[int] = None
