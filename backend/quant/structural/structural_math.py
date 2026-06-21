from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List
from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
)


@dataclass(frozen=True)
class StructuralPointResult:
    distance_to_default: float
    pd_structural_raw: float
    forced_pd_100: bool
    absolute_default_triggered: bool
    risk_state: str
    warnings: List[str]


class StructuralMath:
    """
    순수 구조모형 계산 레이어.
    담당:
    - Distance to Default
    - N(-DD) raw structural PD
    - Absolute default override
    담당하지 않는 것:
    - sigma floor
    - drift clamp
    - maturity lock
    - haircut policy
    - confidence
    - warning summary
    """
    MIN_DENOMINATOR = 1e-8

    def calculate_structural_point(
        self,
        *,
        asset_value: float,
        default_barrier: float,
        sigma: float,
        horizon_years: float,
        drift: float,
        label: str,
        absolute_default_override: bool = True,
    ) -> StructuralPointResult:
        warnings: List[str] = []
        self._validate_math_inputs(
            asset_value=asset_value,
            default_barrier=default_barrier,
            sigma=sigma,
            horizon_years=horizon_years,
            label=label,
        )
        if absolute_default_override and asset_value <= default_barrier:
            warnings.append(
                make_warning(
                    WarningSeverity.CRITICAL,
                    f"{label}_COLLATERAL_BELOW_DEFAULT_BARRIER_FORCED_PD_100",
                    (
                        f"{label} asset value is below or equal to default barrier. "
                        "Merton formula bypassed; raw structural PD forced to 100%."
                    ),
                )
            )
            return StructuralPointResult(
                distance_to_default=-float("inf"),
                pd_structural_raw=1.0,
                forced_pd_100=True,
                absolute_default_triggered=True,
                risk_state="EXTREME_RISK",
                warnings=warnings,
            )
        denominator = sigma * math.sqrt(horizon_years)
        if denominator <= self.MIN_DENOMINATOR:
            raise ValueError(
                f"{label}: denominator too small after policy layer. "
                f"sigma={sigma}, horizon_years={horizon_years}"
            )
        numerator = (
            math.log(asset_value / default_barrier)
            + (drift - 0.5 * sigma**2) * horizon_years
        )
        distance_to_default = numerator / denominator
        pd = self._normal_cdf(-distance_to_default)
        pd = max(0.0, min(1.0, pd))
        return StructuralPointResult(
            distance_to_default=distance_to_default,
            pd_structural_raw=pd,
            forced_pd_100=False,
            absolute_default_triggered=False,
            risk_state="NORMAL",
            warnings=warnings,
        )

    def _validate_math_inputs(
        self,
        *,
        asset_value: float,
        default_barrier: float,
        sigma: float,
        horizon_years: float,
        label: str,
    ) -> None:
        if asset_value < 0:
            raise ValueError(f"{label}: asset_value cannot be negative.")
        if default_barrier <= 0:
            raise ValueError(f"{label}: default_barrier must be greater than 0.")
        if sigma <= 0:
            raise ValueError(f"{label}: sigma must be greater than 0.")
        if horizon_years <= 0:
            raise ValueError(f"{label}: horizon_years must be greater than 0.")

    def _normal_cdf(self, x: float) -> float:
        return 0.5 * math.erfc(-x / math.sqrt(2.0))
