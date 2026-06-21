from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional


class WarningSeverity(str, Enum):
    INFO = "INFO"
    CAUTION = "CAUTION"
    MATERIAL = "MATERIAL"
    CRITICAL = "CRITICAL"
    BLOCKING = "BLOCKING"


@dataclass(frozen=True)
class WarningItem:
    severity: WarningSeverity
    code: str
    message: str

    def as_string(self) -> str:
        return f"{self.severity.value}: {self.code}: {self.message}"


def make_warning(
    severity: WarningSeverity,
    code: str,
    message: str,
) -> str:
    return WarningItem(
        severity=severity,
        code=code,
        message=message,
    ).as_string()


def parse_warning(raw: str) -> WarningItem:
    """
    Expected format:
        SEVERITY: CODE: message
    If malformed, classify as INFO.
    """
    parts = raw.split(":", 2)
    if len(parts) < 3:
        return WarningItem(
            severity=WarningSeverity.INFO,
            code="UNSTRUCTURED_WARNING",
            message=raw,
        )
    severity_raw = parts[0].strip().upper()
    code = parts[1].strip()
    message = parts[2].strip()
    try:
        severity = WarningSeverity(severity_raw)
    except ValueError:
        severity = WarningSeverity.INFO
    return WarningItem(
        severity=severity,
        code=code,
        message=message,
    )


def warning_profile(warnings: Iterable[str]) -> Dict[str, int]:
    profile = {
        "info": 0,
        "caution": 0,
        "material": 0,
        "critical": 0,
        "blocking": 0,
    }
    for raw in warnings:
        parsed = parse_warning(raw)
        key = parsed.severity.value.lower()
        profile[key] = profile.get(key, 0) + 1
    return profile


def warning_summary(
    warnings: List[str],
    max_material: int = 3,
) -> Dict[str, object]:
    parsed = [parse_warning(warning) for warning in warnings]
    blocking = [
        item.as_string()
        for item in parsed
        if item.severity == WarningSeverity.BLOCKING
    ]
    critical = [
        item.as_string()
        for item in parsed
        if item.severity == WarningSeverity.CRITICAL
    ]
    material = [
        item.as_string()
        for item in parsed
        if item.severity == WarningSeverity.MATERIAL
    ]
    primary_blocking_reason: Optional[str] = blocking[0] if blocking else None
    primary_critical_reason: Optional[str] = critical[0] if critical else None
    return {
        "profile": warning_profile(warnings),
        "primary_blocking_reason": primary_blocking_reason,
        "primary_critical_reason": primary_critical_reason,
        "top_material_concerns": material[:max_material],
        "warning_count": len(warnings),
    }
