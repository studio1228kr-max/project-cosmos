from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
)


class EADBasis(str, Enum):
    DRAWN_ONLY = "DRAWN_ONLY"
    DRAWN_PLUS_ACCRUED = "DRAWN_PLUS_ACCRUED"
    DEFAULT_THRESHOLD = "DEFAULT_THRESHOLD"
    COMMITTED_INCLUDING_UNDRAWN = "COMMITTED_INCLUDING_UNDRAWN"
    REVERSE_DEBT_ENGINE_DEFAULT_THRESHOLD = "REVERSE_DEBT_ENGINE_DEFAULT_THRESHOLD"
    ADJUSTED_EAD_ENGINE = "ADJUSTED_EAD_ENGINE"


@dataclass(frozen=True)
class IFRS9EADPolicyConfig:
    default_ccf: float = 0.75
    high_ead_spread_threshold: float = 0.10
    material_undrawn_threshold: float = 0.05


@dataclass(frozen=True)
class IFRS9EADPolicyOutput:
    ead: float
    ead_primary: float
    ead_alternative: Optional[float]
    ead_delta: Optional[float]
    ead_delta_ratio: Optional[float]

    current_balance: float
    undrawn_commitment: float
    ccf: float
    ccf_applied: bool

    ead_basis: EADBasis
    ead_source_engine: str

    warnings: List[str] = field(default_factory=list)
    approval_required_flags: List[str] = field(default_factory=list)


class IFRS9EADPolicy:
    """
    EAD pre-policy layer.

    원칙:
    - IFRS9 ECL engine은 EAD를 소비한다.
    - 다만 EAD basis, CCF, reverse_debt 교차검증은 여기서 한다.
    - 나중에 EAD 산정이 커지면 독립 ead_adjustment_engine으로 승격 가능.
    """

    def __init__(self, config: Optional[IFRS9EADPolicyConfig] = None) -> None:
        self.config = config or IFRS9EADPolicyConfig()

    def apply(self, inputs: Dict[str, Any]) -> IFRS9EADPolicyOutput:
        warnings: List[str] = []
        approval_flags: List[str] = []

        current_balance = self._to_non_negative_float(
            inputs.get("current_balance", inputs.get("ead", 0.0)),
            "current_balance",
        )

        undrawn_commitment = self._to_non_negative_float(
            inputs.get("undrawn_commitment", 0.0),
            "undrawn_commitment",
        )

        ccf = self._to_ratio(inputs.get("ccf", self.config.default_ccf), "ccf")

        raw_basis = str(inputs.get("ead_basis", "DRAWN_ONLY")).upper()

        try:
            ead_basis = EADBasis(raw_basis)
        except ValueError as exc:
            raise ValueError(
                f"ead_basis must be one of {[item.value for item in EADBasis]}"
            ) from exc

        ead_source_engine = str(inputs.get("ead_source_engine", "unknown"))

        ead_primary = self._resolve_primary_ead(
            inputs=inputs,
            current_balance=current_balance,
            undrawn_commitment=undrawn_commitment,
            ccf=ccf,
            ead_basis=ead_basis,
        )

        ccf_applied = ead_basis == EADBasis.COMMITTED_INCLUDING_UNDRAWN

        if ead_basis == EADBasis.DRAWN_ONLY and undrawn_commitment > 0:
            undrawn_ratio = undrawn_commitment / max(current_balance, 1.0)

            if undrawn_ratio >= self.config.material_undrawn_threshold:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "DRAWN_ONLY_EAD_MAY_UNDERSTATE_EXPOSURE",
                        (
                            f"EAD basis is DRAWN_ONLY but undrawn_commitment is "
                            f"{undrawn_commitment:,.0f}. Consider CCF-adjusted EAD."
                        ),
                    )
                )
                approval_flags.append("DRAWN_ONLY_WITH_MATERIAL_UNDRAWN")

        ead_alternative = self._optional_float(inputs.get("ead_alternative"))

        if ead_alternative is None:
            reverse_default_threshold = self._optional_float(
                inputs.get("reverse_debt_default_threshold")
            )

            adjusted_ead = current_balance + undrawn_commitment * ccf

            candidates = [
                value
                for value in [reverse_default_threshold, adjusted_ead]
                if value is not None
            ]

            ead_alternative = max(candidates) if candidates else None

        ead_delta = None
        ead_delta_ratio = None

        if ead_alternative is not None:
            ead_delta = abs(ead_primary - ead_alternative)
            ead_delta_ratio = ead_delta / max(ead_primary, ead_alternative, 1.0)

            if ead_delta_ratio >= self.config.high_ead_spread_threshold:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "EAD_ESTIMATION_SPREAD_HIGH",
                        (
                            f"ead_primary and ead_alternative differ by "
                            f"{ead_delta_ratio:.2%}. This indicates exposure estimation "
                            "methodology spread."
                        ),
                    )
                )
                approval_flags.append("EAD_ESTIMATION_SPREAD_HIGH")

        return IFRS9EADPolicyOutput(
            ead=ead_primary,
            ead_primary=ead_primary,
            ead_alternative=ead_alternative,
            ead_delta=ead_delta,
            ead_delta_ratio=ead_delta_ratio,
            current_balance=current_balance,
            undrawn_commitment=undrawn_commitment,
            ccf=ccf,
            ccf_applied=ccf_applied,
            ead_basis=ead_basis,
            ead_source_engine=ead_source_engine,
            warnings=warnings,
            approval_required_flags=approval_flags,
        )

    def _resolve_primary_ead(
        self,
        *,
        inputs: Dict[str, Any],
        current_balance: float,
        undrawn_commitment: float,
        ccf: float,
        ead_basis: EADBasis,
    ) -> float:
        if "ead_primary" in inputs and inputs.get("ead_primary") is not None:
            return self._to_non_negative_float(inputs["ead_primary"], "ead_primary")

        if "ead" in inputs and inputs.get("ead") is not None:
            return self._to_non_negative_float(inputs["ead"], "ead")

        if ead_basis == EADBasis.COMMITTED_INCLUDING_UNDRAWN:
            return current_balance + undrawn_commitment * ccf

        if ead_basis in {
            EADBasis.DEFAULT_THRESHOLD,
            EADBasis.REVERSE_DEBT_ENGINE_DEFAULT_THRESHOLD,
        }:
            if "reverse_debt_default_threshold" not in inputs:
                raise ValueError(
                    "reverse_debt_default_threshold is required for DEFAULT_THRESHOLD basis."
                )

            return self._to_non_negative_float(
                inputs["reverse_debt_default_threshold"],
                "reverse_debt_default_threshold",
            )

        return current_balance

    def _to_non_negative_float(self, value: Any, field_name: str) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} cannot be converted to float: {value}") from exc

        if result < 0:
            raise ValueError(f"{field_name} must be greater than or equal to 0.")

        return result

    def _to_ratio(self, value: Any, field_name: str) -> float:
        result = self._to_non_negative_float(value, field_name)

        if result > 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

        return result

    def _optional_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
