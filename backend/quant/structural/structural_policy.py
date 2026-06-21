from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from quant.schemas import SourceType
from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
)


class StructuralPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class StructuralPolicyConfig:
    min_volatility_floor: float = 0.10
    volatility_stress_multiplier: float = 1.30

    default_asset_drift: float = -0.02
    max_positive_drift: float = 0.0

    default_breach_ltv_floor: float = 0.80
    min_breach_ltv_floor: float = 0.20
    max_breach_ltv_floor: float = 1.50

    min_horizon_years: float = 7.0 / 365.25
    horizon_material_mismatch_ratio: float = 1.20
    horizon_blocking_mismatch_ratio: float = 2.00

    stale_haircut_grace_days: int = 30
    stale_haircut_per_day: float = 0.0005
    max_stale_haircut: float = 0.15
    as_of_date_material_gap_days: int = 60
    as_of_date_blocking_gap_days: int = 90

    extreme_haircut_threshold: float = 0.80

    allowed_sigma_methods: frozenset[str] = frozenset(
        {
            "market_comp_dispersion",
            "appraisal_band_proxy",
            "cap_rate_noi_stress",
            "house_assumption",
        }
    )


@dataclass(frozen=True)
class StructuralPolicyOutput:
    avm_value: float
    effective_asset_value: float

    avm_sigma_input: float
    avm_sigma_floored: float
    avm_sigma_effective: float

    current_debt_balance: float
    default_threshold: float
    breach_ltv_floor: float
    default_barrier: float

    days_to_maturity: float
    locked_horizon_years: float
    manual_horizon_years: Optional[float]

    asset_drift_input: float
    effective_asset_drift: float

    liquidity_haircut: float
    enforcement_cost_ratio: float
    jurisdictional_friction_haircut: float
    stale_haircut: float
    total_effective_haircut: float

    valuation_date: date
    debt_as_of_date: date
    valuation_staleness_days: int
    debt_staleness_days: int
    as_of_date_gap_days: int

    asset_class: str
    collateral_type: str
    sigma_method: str

    current_ltv_gross: float
    current_ltv_effective: float
    threshold_ltv_gross: float
    threshold_ltv_effective: float

    manual_override_detected: bool
    approval_required_flags: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StructuralPolicyLayer:
    """
    House policy / governance layer.

    담당:
    - volatility floor
    - volatility stress multiplier
    - positive drift clamp
    - maturity lock-in
    - stale valuation haircut
    - liquidity / enforcement / jurisdiction haircut
    - default barrier construction

    담당하지 않는 것:
    - DD 수식 계산
    - confidence aggregation
    - EngineResult 포장
    """

    def __init__(self, config: Optional[StructuralPolicyConfig] = None) -> None:
        self.config = config or StructuralPolicyConfig()

    def apply(
        self,
        inputs: Dict[str, Any],
        vectors: Optional[Dict[str, Any]] = None,
    ) -> StructuralPolicyOutput:
        vectors = vectors or {}
        warnings: List[str] = []
        approval_flags: List[str] = []

        avm_value = self._to_positive_float(inputs["avm_value"], "avm_value")
        avm_sigma_input = self._to_positive_float(inputs["avm_sigma"], "avm_sigma")
        current_debt_balance = self._to_positive_float(
            inputs["current_debt_balance"],
            "current_debt_balance",
        )
        default_threshold = self._to_positive_float(
            inputs["default_threshold"],
            "default_threshold",
        )

        days_to_maturity = self._to_float(
            inputs["days_to_maturity"],
            "days_to_maturity",
        )

        if days_to_maturity <= 0:
            warnings.append(
                make_warning(
                    WarningSeverity.CRITICAL,
                    "MATURITY_PASSED_OR_DUE",
                    (
                        "days_to_maturity is zero or negative. "
                        "Locked horizon is floored, but maturity state is critical."
                    ),
                )
            )
            approval_flags.append("MATURITY_PASSED_OR_DUE")

        locked_horizon_years = max(
            days_to_maturity / 365.25,
            self.config.min_horizon_years,
        )

        manual_horizon_years = None

        if "horizon_years" in inputs and inputs.get("horizon_years") is not None:
            manual_horizon_years = self._to_positive_float(
                inputs["horizon_years"],
                "horizon_years",
            )

            ratio = self._ratio_gap(manual_horizon_years, locked_horizon_years)

            if ratio >= self.config.horizon_blocking_mismatch_ratio:
                raise StructuralPolicyError(
                    "BLOCKING: HORIZON_MATURITY_MISMATCH: "
                    f"manual horizon {manual_horizon_years:.4f}y differs from "
                    f"locked maturity horizon {locked_horizon_years:.4f}y by "
                    f"{ratio:.2f}x."
                )

            if ratio >= self.config.horizon_material_mismatch_ratio:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "HORIZON_OVERRIDDEN_BY_MATURITY_LOCK",
                        (
                            f"Manual horizon {manual_horizon_years:.4f}y differs from "
                            f"locked maturity horizon {locked_horizon_years:.4f}y. "
                            "Maturity-locked horizon is used."
                        ),
                    )
                )
                approval_flags.append("MANUAL_HORIZON_OVERRIDE_SUPPRESSED")

        asset_class = str(inputs["asset_class"]).upper()
        collateral_type = str(inputs["collateral_type"]).upper()
        sigma_method = str(inputs["sigma_method"]).lower()

        if sigma_method not in self.config.allowed_sigma_methods:
            raise StructuralPolicyError(
                "BLOCKING: INVALID_SIGMA_METHOD: "
                f"sigma_method must be one of {sorted(self.config.allowed_sigma_methods)}."
            )

        liquidity_haircut = self._to_ratio(
            inputs["liquidity_haircut"],
            "liquidity_haircut",
        )
        enforcement_cost_ratio = self._to_ratio(
            inputs["enforcement_cost_ratio"],
            "enforcement_cost_ratio",
        )
        jurisdictional_friction_haircut = self._to_ratio(
            inputs.get("jurisdictional_friction_haircut", 0.0),
            "jurisdictional_friction_haircut",
        )

        valuation_date = self._parse_date(inputs["valuation_date"], "valuation_date")
        debt_as_of_date = self._parse_date(inputs["debt_as_of_date"], "debt_as_of_date")

        now_date = datetime.now(timezone.utc).date()
        valuation_staleness_days = max(0, (now_date - valuation_date).days)
        debt_staleness_days = max(0, (now_date - debt_as_of_date).days)
        as_of_date_gap_days = abs((valuation_date - debt_as_of_date).days)

        if as_of_date_gap_days >= self.config.as_of_date_blocking_gap_days:
            raise StructuralPolicyError(
                "BLOCKING: AS_OF_DATE_MISMATCH_EXCEEDS_LIMIT: "
                f"valuation_date and debt_as_of_date differ by "
                f"{as_of_date_gap_days} days."
            )

        if as_of_date_gap_days >= self.config.as_of_date_material_gap_days:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "AS_OF_DATE_MISMATCH_MATERIAL",
                    (
                        f"valuation_date and debt_as_of_date differ by "
                        f"{as_of_date_gap_days} days."
                    ),
                )
            )
            approval_flags.append("AS_OF_DATE_MISMATCH_MATERIAL")

        stale_haircut = self._stale_haircut(valuation_staleness_days)

        if stale_haircut > 0:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "STALE_VALUATION_HAIRCUT_APPLIED",
                    (
                        f"valuation_date is {valuation_staleness_days} days old. "
                        f"Stale valuation haircut {stale_haircut:.2%} applied."
                    ),
                )
            )

        if avm_sigma_input < self.config.min_volatility_floor:
            avm_sigma_floored = self.config.min_volatility_floor
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "VOLATILITY_FLOORED_TO_MINIMUM",
                    (
                        f"Input sigma {avm_sigma_input:.2%} is below minimum floor "
                        f"{self.config.min_volatility_floor:.2%}. "
                        f"Floored sigma {avm_sigma_floored:.2%} is used."
                    ),
                )
            )
            approval_flags.append("VOLATILITY_FLOORED_TO_MINIMUM")
        else:
            avm_sigma_floored = avm_sigma_input

        avm_sigma_effective = (
            avm_sigma_floored * self.config.volatility_stress_multiplier
        )

        warnings.append(
            make_warning(
                WarningSeverity.CAUTION,
                "VOLATILITY_STRESS_MULTIPLIER_APPLIED",
                (
                    f"Floored sigma {avm_sigma_floored:.2%} multiplied by "
                    f"{self.config.volatility_stress_multiplier:.2f}. "
                    f"Effective sigma {avm_sigma_effective:.2%}."
                ),
            )
        )

        sigma_source_type = self._vector_source_type(vectors, "avm_sigma")

        if sigma_source_type == SourceType.MANUAL:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "MANUAL_SIGMA_INPUT",
                    (
                        "avm_sigma came from MANUAL source. Sigma should normally be "
                        "generated by sigma engine or house rule table."
                    ),
                )
            )
            approval_flags.append("MANUAL_SIGMA_INPUT")

        if sigma_method == "house_assumption":
            warnings.append(
                make_warning(
                    WarningSeverity.CAUTION,
                    "HOUSE_SIGMA_ASSUMPTION",
                    (
                        "sigma_method is house_assumption. Acceptable for early screen, "
                        "but should be replaced by observed dispersion or appraisal band "
                        "proxy before final IC."
                    ),
                )
            )

        asset_drift_input = self._to_float(
            inputs.get("asset_drift", self.config.default_asset_drift),
            "asset_drift",
        )

        if asset_drift_input > self.config.max_positive_drift:
            effective_asset_drift = self.config.max_positive_drift
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "ASSET_DRIFT_FORCED_TO_ZERO",
                    (
                        f"Positive asset_drift {asset_drift_input:.2%} supplied. "
                        "Operating path forbids positive drift. "
                        f"Effective drift {effective_asset_drift:.2%} used."
                    ),
                )
            )
            approval_flags.append("POSITIVE_ASSET_DRIFT_SUPPLIED")
        else:
            effective_asset_drift = asset_drift_input

        breach_ltv_floor = self._to_ratio(
            inputs.get("breach_ltv_floor", self.config.default_breach_ltv_floor),
            "breach_ltv_floor",
        )

        if breach_ltv_floor < self.config.min_breach_ltv_floor:
            raise StructuralPolicyError(
                "BLOCKING: BREACH_LTV_FLOOR_TOO_LOW: "
                f"breach_ltv_floor must be >= "
                f"{self.config.min_breach_ltv_floor:.2%}."
            )

        if breach_ltv_floor > self.config.max_breach_ltv_floor:
            raise StructuralPolicyError(
                "BLOCKING: BREACH_LTV_FLOOR_TOO_HIGH: "
                f"breach_ltv_floor must be <= "
                f"{self.config.max_breach_ltv_floor:.2%}."
            )

        if breach_ltv_floor > 1.0:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "BREACH_LTV_FLOOR_ABOVE_100PCT",
                    (
                        f"breach_ltv_floor is {breach_ltv_floor:.2%}. "
                        "This may be valid for special situations but requires approval."
                    ),
                )
            )
            approval_flags.append("BREACH_LTV_FLOOR_ABOVE_100PCT")

        if breach_ltv_floor > self.config.default_breach_ltv_floor:
            warnings.append(
                make_warning(
                    WarningSeverity.CAUTION,
                    "BREACH_LTV_FLOOR_ABOVE_HOUSE_DEFAULT",
                    (
                        f"breach_ltv_floor {breach_ltv_floor:.2%} is more permissive "
                        f"than house default {self.config.default_breach_ltv_floor:.2%}."
                    ),
                )
            )

        default_barrier = default_threshold / breach_ltv_floor

        total_effective_haircut = (
            liquidity_haircut
            + enforcement_cost_ratio
            + jurisdictional_friction_haircut
            + stale_haircut
        )

        if total_effective_haircut >= self.config.extreme_haircut_threshold:
            warnings.append(
                make_warning(
                    WarningSeverity.CRITICAL,
                    "TOTAL_EFFECTIVE_HAIRCUT_EXTREME",
                    (
                        f"Total effective haircut is {total_effective_haircut:.2%}. "
                        "Calculation will continue, but result should be treated as "
                        "extreme risk, not model failure."
                    ),
                )
            )
            approval_flags.append("TOTAL_EFFECTIVE_HAIRCUT_EXTREME")

        if total_effective_haircut >= 1.0:
            effective_asset_value = 0.0
            warnings.append(
                make_warning(
                    WarningSeverity.CRITICAL,
                    "EFFECTIVE_ASSET_VALUE_ZERO_AFTER_HAIRCUTS",
                    (
                        f"Total haircut {total_effective_haircut:.2%} eliminates "
                        "effective collateral value."
                    ),
                )
            )
        else:
            effective_asset_value = avm_value * (1.0 - total_effective_haircut)

        current_ltv_gross = self._safe_ratio(current_debt_balance, avm_value)
        current_ltv_effective = self._safe_ratio(
            current_debt_balance,
            effective_asset_value,
        )
        threshold_ltv_gross = self._safe_ratio(default_threshold, avm_value)
        threshold_ltv_effective = self._safe_ratio(
            default_threshold,
            effective_asset_value,
        )

        if current_ltv_effective >= self.config.default_breach_ltv_floor:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "CURRENT_EFFECTIVE_LTV_ABOVE_HOUSE_BREACH_FLOOR",
                    (
                        f"Current effective LTV is {current_ltv_effective:.2%}, "
                        f"above house floor {self.config.default_breach_ltv_floor:.2%}."
                    ),
                )
            )

        manual_override_detected = (
            self._bool_like(inputs.get("manual_override_flag", False))
            or sigma_source_type == SourceType.MANUAL
            or bool(approval_flags)
        )

        return StructuralPolicyOutput(
            avm_value=avm_value,
            effective_asset_value=effective_asset_value,
            avm_sigma_input=avm_sigma_input,
            avm_sigma_floored=avm_sigma_floored,
            avm_sigma_effective=avm_sigma_effective,
            current_debt_balance=current_debt_balance,
            default_threshold=default_threshold,
            breach_ltv_floor=breach_ltv_floor,
            default_barrier=default_barrier,
            days_to_maturity=days_to_maturity,
            locked_horizon_years=locked_horizon_years,
            manual_horizon_years=manual_horizon_years,
            asset_drift_input=asset_drift_input,
            effective_asset_drift=effective_asset_drift,
            liquidity_haircut=liquidity_haircut,
            enforcement_cost_ratio=enforcement_cost_ratio,
            jurisdictional_friction_haircut=jurisdictional_friction_haircut,
            stale_haircut=stale_haircut,
            total_effective_haircut=total_effective_haircut,
            valuation_date=valuation_date,
            debt_as_of_date=debt_as_of_date,
            valuation_staleness_days=valuation_staleness_days,
            debt_staleness_days=debt_staleness_days,
            as_of_date_gap_days=as_of_date_gap_days,
            asset_class=asset_class,
            collateral_type=collateral_type,
            sigma_method=sigma_method,
            current_ltv_gross=current_ltv_gross,
            current_ltv_effective=current_ltv_effective,
            threshold_ltv_gross=threshold_ltv_gross,
            threshold_ltv_effective=threshold_ltv_effective,
            manual_override_detected=manual_override_detected,
            approval_required_flags=approval_flags,
            warnings=warnings,
        )

    def _to_float(self, value: Any, field_name: str) -> float:
        if value is None:
            raise ValueError(f"{field_name} cannot be None.")

        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} cannot be converted to float: {value}") from exc

    def _to_positive_float(self, value: Any, field_name: str) -> float:
        result = self._to_float(value, field_name)

        if result <= 0:
            raise ValueError(f"{field_name} must be greater than 0.")

        return result

    def _to_ratio(self, value: Any, field_name: str) -> float:
        result = self._to_float(value, field_name)

        if result < 0.0 or result > 1.5:
            raise ValueError(
                f"{field_name} must be a ratio between 0.0 and 1.5."
            )

        return result

    def _parse_date(self, value: Any, field_name: str) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            raw = value.strip()

            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"

            try:
                return datetime.fromisoformat(raw).date()
            except ValueError:
                try:
                    return date.fromisoformat(raw)
                except ValueError as exc:
                    raise ValueError(
                        f"{field_name} must be ISO date or datetime string: {value}"
                    ) from exc

        raise ValueError(f"{field_name} must be date, datetime, or ISO string.")

    def _stale_haircut(self, valuation_staleness_days: int) -> float:
        excess_days = max(
            0,
            valuation_staleness_days - self.config.stale_haircut_grace_days,
        )

        haircut = excess_days * self.config.stale_haircut_per_day

        return min(self.config.max_stale_haircut, haircut)

    def _ratio_gap(self, a: float, b: float) -> float:
        epsilon = 1e-9
        return max(a, b) / max(min(a, b), epsilon)

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return float("inf")

        return numerator / denominator

    def _vector_source_type(
        self,
        vectors: Dict[str, Any],
        name: str,
    ) -> Optional[SourceType]:
        vector = vectors.get(name)

        if vector is None:
            return None

        return getattr(vector, "source_type", None)

    def _bool_like(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}

        return bool(value)
