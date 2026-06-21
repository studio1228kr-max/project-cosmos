from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from quant.schemas import SourceType
from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
)


class IFRS9PolicyError(ValueError):
    pass


class DDStage(str, Enum):
    PRE = "PRE"
    SOFT = "SOFT"
    FULL = "FULL"


class IFRS9Stage(str, Enum):
    STAGE_1 = "STAGE_1"
    STAGE_2 = "STAGE_2"
    STAGE_3 = "STAGE_3"


class PDStage(str, Enum):
    RAW = "RAW"
    CALIBRATED = "CALIBRATED"
    FINAL = "FINAL"


@dataclass(frozen=True)
class IFRS9PolicyConfig:
    pd_floor_stage_1: float = 0.0025
    pd_floor_stage_2: float = 0.0100

    min_stage3_risk_floor: float = 0.50

    stage2_ltv_trigger: float = 0.70
    stage3_ltv_trigger: float = 1.00

    maturity_stage2_days: int = 365
    maturity_stage3_days: int = 30

    default_lifetime_years_stage_1: float = 1.0

    flat_lifetime_pd_warning: bool = True


@dataclass(frozen=True)
class IFRS9PolicyOutput:
    dd_stage_proposed: DDStage
    dd_stage_effective: DDStage
    ifrs9_stage_effective: IFRS9Stage

    sicr_triggers: List[str]
    credit_impaired_triggers: List[str]

    pd_input: float
    pd_accounting: float
    pd_risk: float
    pd_12month: float
    lifetime_pd_accounting: float
    lifetime_pd_risk: float

    pd_stage: PDStage
    pd_lineage: List[str]

    lgd: float
    lgd_sigma: Optional[float]
    lgd_volatility_method: str

    remaining_term_years: float
    lifetime_years: float
    lifetime_pd_method: str

    accounting_el_basis: str
    risk_el_basis: str
    interest_revenue_basis: str
    credit_impaired: bool

    dynamic_stage3_risk_floor: Optional[float]

    manual_override_detected: bool
    approval_required_flags: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class IFRS9PolicyLayer:
    """
    IFRS9 staged ECL policy layer.

    핵심 원칙:
    - 사용자가 제안한 stage는 신뢰하지 않는다.
    - SICR / credit-impaired trigger로 stage를 강제 상향할 수 있다.
    - Stage 3 accounting PD는 hardcoded 1.0이다.
    - Stage 3 risk PD는 model PD를 유지하되 dynamic floor를 적용한다.
    """

    def __init__(self, config: Optional[IFRS9PolicyConfig] = None) -> None:
        self.config = config or IFRS9PolicyConfig()

    def apply(
        self,
        inputs: Dict[str, Any],
        vectors: Optional[Dict[str, Any]] = None,
    ) -> IFRS9PolicyOutput:
        vectors = vectors or {}
        warnings: List[str] = []
        approval_flags: List[str] = []

        pd_input = self._to_ratio(inputs["pd"], "pd")
        lgd = self._to_ratio(inputs["lgd"], "lgd")

        lgd_sigma = self._optional_ratio(inputs.get("lgd_sigma"))
        lgd_volatility_method = str(
            inputs.get("lgd_volatility_method", "MISSING")
        ).upper()

        dd_stage_proposed = self._parse_dd_stage(
            inputs.get("dd_stage_proposed", inputs.get("dd_stage"))
        )

        remaining_term_years = self._to_positive_float(
            inputs["remaining_term_years"],
            "remaining_term_years",
        )

        lifetime_years = remaining_term_years

        if "lifetime_years" in inputs and inputs.get("lifetime_years") is not None:
            proposed_lifetime_years = self._to_positive_float(
                inputs["lifetime_years"],
                "lifetime_years",
            )

            ratio = self._ratio_gap(proposed_lifetime_years, remaining_term_years)

            if ratio >= 2.0:
                raise IFRS9PolicyError(
                    "BLOCKING: LIFETIME_YEARS_REMAINING_TERM_MISMATCH: "
                    f"lifetime_years={proposed_lifetime_years:.4f}, "
                    f"remaining_term_years={remaining_term_years:.4f}."
                )

            if ratio >= 1.20:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "LIFETIME_YEARS_OVERRIDDEN_BY_REMAINING_TERM",
                        (
                            f"lifetime_years={proposed_lifetime_years:.4f} differs from "
                            f"remaining_term_years={remaining_term_years:.4f}. "
                            "Remaining term is used."
                        ),
                    )
                )
                approval_flags.append("LIFETIME_YEARS_OVERRIDE_SUPPRESSED")

        pd_stage = self._parse_pd_stage(inputs.get("pd_stage", "RAW"))
        pd_lineage = self._parse_pd_lineage(inputs.get("pd_lineage"))

        if pd_stage == PDStage.RAW:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "RAW_PD_USED_IN_ECL",
                    "Raw PD used. Final ECL should use calibrated / overlay-adjusted PD.",
                )
            )
            approval_flags.append("RAW_PD_USED_IN_ECL")

        effective_ltv = self._optional_ratio_allow_inf(inputs.get("effective_ltv"))
        days_to_maturity = self._optional_float(inputs.get("days_to_maturity"))
        maturity_risk_state = str(inputs.get("maturity_risk_state", "")).upper()
        refi_gate_state = str(inputs.get("refi_gate_state", "")).upper()

        covenant_breach_flag = self._bool_like(inputs.get("covenant_breach_flag", False))
        payment_default_flag = self._bool_like(inputs.get("payment_default_flag", False))
        default_event_flag = self._bool_like(inputs.get("default_event_flag", False))
        credit_impaired_flag = self._bool_like(inputs.get("credit_impaired_flag", False))

        sicr_triggers = self._sicr_triggers(
            effective_ltv=effective_ltv,
            days_to_maturity=days_to_maturity,
            maturity_risk_state=maturity_risk_state,
            refi_gate_state=refi_gate_state,
            covenant_breach_flag=covenant_breach_flag,
        )

        credit_impaired_triggers = self._credit_impaired_triggers(
            effective_ltv=effective_ltv,
            days_to_maturity=days_to_maturity,
            payment_default_flag=payment_default_flag,
            default_event_flag=default_event_flag,
            credit_impaired_flag=credit_impaired_flag,
            proposed_stage=dd_stage_proposed,
        )

        dd_stage_effective = self._forced_stage(
            proposed=dd_stage_proposed,
            sicr_triggers=sicr_triggers,
            credit_impaired_triggers=credit_impaired_triggers,
        )

        if self._stage_rank(dd_stage_effective) > self._stage_rank(dd_stage_proposed):
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "SICR_OR_CREDIT_IMPAIRED_TRIGGER_FORCED_STAGE_UPGRADE",
                    (
                        f"Proposed stage {dd_stage_proposed.value} was upgraded to "
                        f"{dd_stage_effective.value} by system triggers."
                    ),
                )
            )
            approval_flags.append("SYSTEM_FORCED_STAGE_UPGRADE")

        ifrs9_stage_effective = self._map_ifrs9_stage(dd_stage_effective)

        pd_12month = max(
            pd_input,
            self.config.pd_floor_stage_1
            if dd_stage_effective == DDStage.PRE
            else self.config.pd_floor_stage_2,
        )

        if dd_stage_effective == DDStage.FULL:
            if pd_input < 1.0:
                warnings.append(
                    make_warning(
                        WarningSeverity.CRITICAL,
                        "STAGE3_ACCOUNTING_PD_IS_NONNEGOTIABLE",
                        (
                            f"Input PD {pd_input:.2%} supplied for Stage 3. "
                            "Accounting PD is hardcoded to 100%."
                        ),
                    )
                )
                approval_flags.append("STAGE3_ACCOUNTING_PD_OVERRIDE_ATTEMPTED")

            pd_accounting = 1.0
            dynamic_floor = self._dynamic_stage3_risk_floor(effective_ltv)
            pd_risk = max(pd_input, dynamic_floor)

            lifetime_pd_accounting = 1.0
            lifetime_pd_risk = pd_risk
            lifetime_pd_method = "STAGE3_ACCOUNTING_PD_HARDCODED_AND_RISK_PD_FLOORED"

            if lgd_sigma is None:
                raise IFRS9PolicyError(
                    "BLOCKING: STAGE3_REQUIRES_LGD_SIGMA: "
                    "lgd_sigma is required for Stage 3 LGD-volatility UL proxy."
                )

            if lgd_volatility_method == "MANUAL":
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "MANUAL_LGD_SIGMA_INPUT",
                        "lgd_sigma is manually supplied. Recovery-engine-derived lgd_sigma preferred.",
                    )
                )
                approval_flags.append("MANUAL_LGD_SIGMA_INPUT")

        else:
            pd_accounting = pd_12month
            pd_risk = pd_12month
            dynamic_floor = None

            lifetime_pd_accounting, lifetime_pd_risk, lifetime_pd_method = (
                self._resolve_lifetime_pd(
                    inputs=inputs,
                    pd_12month=pd_12month,
                    lifetime_years=lifetime_years,
                    warnings=warnings,
                    approval_flags=approval_flags,
                )
            )

        credit_impaired = dd_stage_effective == DDStage.FULL

        if dd_stage_effective == DDStage.PRE:
            accounting_el_basis = "12_MONTH_ECL"
            risk_el_basis = "12_MONTH_RISK_EL"
            interest_revenue_basis = "GROSS_CARRYING_AMOUNT"
        elif dd_stage_effective == DDStage.SOFT:
            accounting_el_basis = "LIFETIME_ECL"
            risk_el_basis = "LIFETIME_RISK_EL"
            interest_revenue_basis = "GROSS_CARRYING_AMOUNT"
        else:
            accounting_el_basis = "LIFETIME_ECL_CREDIT_IMPAIRED"
            risk_el_basis = "STAGE3_RISK_EL_WITH_DYNAMIC_PD_FLOOR"
            interest_revenue_basis = "NET_CARRYING_AMOUNT"

        pd_source_type = self._vector_source_type(vectors, "pd")

        if pd_source_type == SourceType.MANUAL:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "MANUAL_PD_INPUT",
                    "PD came from MANUAL source. Manual PD is not acceptable for final use.",
                )
            )
            approval_flags.append("MANUAL_PD_INPUT")

        manual_override_detected = (
            self._bool_like(inputs.get("manual_override_flag", False))
            or pd_source_type == SourceType.MANUAL
            or bool(approval_flags)
        )

        return IFRS9PolicyOutput(
            dd_stage_proposed=dd_stage_proposed,
            dd_stage_effective=dd_stage_effective,
            ifrs9_stage_effective=ifrs9_stage_effective,
            sicr_triggers=sicr_triggers,
            credit_impaired_triggers=credit_impaired_triggers,
            pd_input=pd_input,
            pd_accounting=pd_accounting,
            pd_risk=pd_risk,
            pd_12month=pd_12month,
            lifetime_pd_accounting=lifetime_pd_accounting,
            lifetime_pd_risk=lifetime_pd_risk,
            pd_stage=pd_stage,
            pd_lineage=pd_lineage,
            lgd=lgd,
            lgd_sigma=lgd_sigma,
            lgd_volatility_method=lgd_volatility_method,
            remaining_term_years=remaining_term_years,
            lifetime_years=lifetime_years,
            lifetime_pd_method=lifetime_pd_method,
            accounting_el_basis=accounting_el_basis,
            risk_el_basis=risk_el_basis,
            interest_revenue_basis=interest_revenue_basis,
            credit_impaired=credit_impaired,
            dynamic_stage3_risk_floor=dynamic_floor,
            manual_override_detected=manual_override_detected,
            approval_required_flags=approval_flags,
            warnings=warnings,
        )

    def _resolve_lifetime_pd(
        self,
        *,
        inputs: Dict[str, Any],
        pd_12month: float,
        lifetime_years: float,
        warnings: List[str],
        approval_flags: List[str],
    ) -> tuple[float, float, str]:
        if inputs.get("hazard_lifetime_pd") is not None:
            value = self._to_ratio(inputs["hazard_lifetime_pd"], "hazard_lifetime_pd")
            return value, value, "HAZARD_ENGINE_LIFETIME_PD"

        if inputs.get("tail_balance_ratio") is not None:
            tail_balance_ratio = self._to_positive_float(
                inputs["tail_balance_ratio"],
                "tail_balance_ratio",
            )

            slope_multiplier = min(3.0, max(1.0, tail_balance_ratio))
            adjusted_annual_pd = min(1.0, pd_12month * slope_multiplier)
            lifetime_pd = 1.0 - ((1.0 - adjusted_annual_pd) ** lifetime_years)

            warnings.append(
                make_warning(
                    WarningSeverity.CAUTION,
                    "LIFETIME_PD_REVERSE_DEBT_SLOPE_ADJUSTED",
                    (
                        f"tail_balance_ratio={tail_balance_ratio:.2f} applied as "
                        "hazard slope proxy."
                    ),
                )
            )

            return lifetime_pd, lifetime_pd, "REVERSE_DEBT_TAIL_BALANCE_ADJUSTED"

        if inputs.get("lifetime_pd") is not None:
            value = self._to_ratio(inputs["lifetime_pd"], "lifetime_pd")
            return value, value, "DIRECT_LIFETIME_PD"

        lifetime_pd = 1.0 - ((1.0 - pd_12month) ** lifetime_years)

        warnings.append(
            make_warning(
                WarningSeverity.MATERIAL,
                "LIFETIME_PD_FLAT_APPROXIMATION_USED",
                (
                    "Lifetime PD used flat cumulative approximation because no hazard "
                    "or reverse-debt term-structure input was supplied."
                ),
            )
        )
        approval_flags.append("LIFETIME_PD_FLAT_APPROXIMATION_USED")

        return lifetime_pd, lifetime_pd, "FLAT_CUMULATIVE_APPROXIMATION"

    def _sicr_triggers(
        self,
        *,
        effective_ltv: Optional[float],
        days_to_maturity: Optional[float],
        maturity_risk_state: str,
        refi_gate_state: str,
        covenant_breach_flag: bool,
    ) -> List[str]:
        triggers: List[str] = []

        if effective_ltv is not None and effective_ltv >= self.config.stage2_ltv_trigger:
            triggers.append("EFFECTIVE_LTV_STAGE2_TRIGGER")

        if days_to_maturity is not None and days_to_maturity <= self.config.maturity_stage2_days:
            triggers.append("MATURITY_WITHIN_STAGE2_WINDOW")

        if maturity_risk_state in {"WARNING", "CRITICAL"}:
            triggers.append("MATURITY_MONITOR_WARNING_OR_CRITICAL")

        if refi_gate_state in {"WEAK", "FAILED", "BLOCKED"}:
            triggers.append("REFI_GATE_WEAK_OR_FAILED")

        if covenant_breach_flag:
            triggers.append("COVENANT_BREACH")

        return triggers

    def _credit_impaired_triggers(
        self,
        *,
        effective_ltv: Optional[float],
        days_to_maturity: Optional[float],
        payment_default_flag: bool,
        default_event_flag: bool,
        credit_impaired_flag: bool,
        proposed_stage: DDStage,
    ) -> List[str]:
        triggers: List[str] = []

        if proposed_stage == DDStage.FULL:
            triggers.append("PROPOSED_FULL_STAGE")

        if effective_ltv is not None and effective_ltv >= self.config.stage3_ltv_trigger:
            triggers.append("EFFECTIVE_LTV_STAGE3_TRIGGER")

        if days_to_maturity is not None and days_to_maturity <= self.config.maturity_stage3_days:
            triggers.append("MATURITY_WITHIN_STAGE3_WINDOW")

        if payment_default_flag:
            triggers.append("PAYMENT_DEFAULT")

        if default_event_flag:
            triggers.append("DEFAULT_EVENT")

        if credit_impaired_flag:
            triggers.append("CREDIT_IMPAIRED_FLAG")

        return triggers

    def _forced_stage(
        self,
        *,
        proposed: DDStage,
        sicr_triggers: List[str],
        credit_impaired_triggers: List[str],
    ) -> DDStage:
        if credit_impaired_triggers:
            return DDStage.FULL

        if sicr_triggers and proposed == DDStage.PRE:
            return DDStage.SOFT

        return proposed

    def _dynamic_stage3_risk_floor(self, effective_ltv: Optional[float]) -> float:
        if effective_ltv is None:
            return self.config.min_stage3_risk_floor

        if effective_ltv < 0.80:
            floor = 0.50
        elif effective_ltv < 0.90:
            floor = 0.65
        elif effective_ltv < 1.00:
            floor = 0.80
        else:
            floor = 0.95

        return max(self.config.min_stage3_risk_floor, floor)

    def _map_ifrs9_stage(self, stage: DDStage) -> IFRS9Stage:
        if stage == DDStage.PRE:
            return IFRS9Stage.STAGE_1

        if stage == DDStage.SOFT:
            return IFRS9Stage.STAGE_2

        return IFRS9Stage.STAGE_3

    def _stage_rank(self, stage: DDStage) -> int:
        return {
            DDStage.PRE: 1,
            DDStage.SOFT: 2,
            DDStage.FULL: 3,
        }[stage]

    def _parse_dd_stage(self, value: Any) -> DDStage:
        try:
            return DDStage(str(value).upper())
        except ValueError as exc:
            raise IFRS9PolicyError(
                "BLOCKING: INVALID_DD_STAGE: dd_stage must be PRE, SOFT, or FULL."
            ) from exc

    def _parse_pd_stage(self, value: Any) -> PDStage:
        try:
            return PDStage(str(value).upper())
        except ValueError as exc:
            raise IFRS9PolicyError(
                "BLOCKING: INVALID_PD_STAGE: pd_stage must be RAW, CALIBRATED, or FINAL."
            ) from exc

    def _parse_pd_lineage(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return [str(item) for item in value]

        return [str(value)]

    def _to_float(self, value: Any, field_name: str) -> float:
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

        if result < 0.0 or result > 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

        return result

    def _optional_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _optional_ratio(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        result = self._to_ratio(value, "optional_ratio")
        return result

    def _optional_ratio_allow_inf(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        result = self._to_float(value, "effective_ltv")

        if result < 0:
            raise ValueError("effective_ltv must be non-negative.")

        return result

    def _ratio_gap(self, a: float, b: float) -> float:
        return max(a, b) / max(min(a, b), 1e-9)

    def _vector_source_type(self, vectors: Dict[str, Any], name: str) -> Optional[SourceType]:
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
