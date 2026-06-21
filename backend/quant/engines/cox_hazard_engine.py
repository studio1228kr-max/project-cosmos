# backend/quant/engines/cox_hazard_engine.py

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant.base import QuantEngine
from quant.schemas import (
    ConfidenceInfo,
    ConfidenceTier,
    EngineResult,
    Provenance,
    ProvenanceInput,
    SourceType,
)
from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
    warning_profile,
    warning_summary,
)


class CoxHazardEngine(QuantEngine):
    """
    Cox Hazard Engine v0.2

    Registry 호환을 위해 engine_name은 cox_hazard_engine으로 유지한다.
    단, 실제 구현은 Cox Proportional Hazard가 아니다.

    실제 방법론:
        PIECEWISE_HOUSE_RULE

    목적:
    - merton_kmv.pd_structural_raw 또는 calibrated 12M PD를 받아
    - maturity_monitor.days_to_maturity와
    - reverse_debt_engine.tail_balance_ratio를 이용해
    - private credit maturity-wall hazard curve를 생성한다.

    핵심 원칙:
    - fallback은 계산 continuity용이지 operational use permission이 아니다.
    - manual PD는 confidence haircut이 아니라 contamination event로 본다.
    - amortizing 구조는 리스크 감소를 인정하되 sanity monitoring은 유지한다.
    - 수치 포화는 traceable saturation으로 남기고 lifetime PD를 100%로 고정한다.
    """

    engine_name = "cox_hazard_engine"
    model_version = "v0.2"

    REQUIRED_INPUTS = [
        "pd_12m",
        "days_to_maturity",
    ]

    OPTIONAL_INPUTS = [
        "tail_balance_ratio",
        "pd_type",
        "house_rule_version",
        "manual_override_flag",
        "override_approver",
    ]

    PD_FLOOR = 0.0025
    MAX_HAZARD_RATE = 0.9999
    MAX_TAIL_BALANCE_RATIO = 3.0

    DAYS_PER_YEAR = 365.25
    MAX_DAYS_TO_MATURITY = 3650.0  # 10Y private-credit operating range cap

    SURVIVAL_PROBABILITY_FLOOR = 1e-9
    SUM_LOG_SATURATION_THRESHOLD = math.log(SURVIVAL_PROBABILITY_FLOOR)

    DIRECT_INPUT_CONFIDENCE = 0.20

    def compute(self, deal_master_id: int, inputs: Dict[str, Any]) -> EngineResult:
        warnings: List[str] = []

        vectors = inputs.get("_vectors")

        strict_vector_mode = self._strict_vector_mode()
        direct_input_mode = not isinstance(vectors, dict) or not vectors

        if direct_input_mode and strict_vector_mode:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "VECTOR_LAYER_REQUIRED",
                    (
                        "Production path requires inputs['_vectors'] with FeatureVector "
                        "objects. Direct hazard input is blocked."
                    ),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="FeatureVector layer missing under strict vector mode.",
            )

        if direct_input_mode and not strict_vector_mode:
            warnings.append(
                make_warning(
                    WarningSeverity.CRITICAL,
                    "NON_PRODUCTION_INPUT_MODE",
                    (
                        "FeatureVector layer missing. Direct input is allowed only because "
                        "strict vector mode is disabled. Output must not feed deal gate."
                    ),
                )
            )
            vectors = {}

        missing = self.validate_inputs(inputs, self.REQUIRED_INPUTS)

        if missing:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "MISSING_REQUIRED_INPUTS",
                    f"Missing required inputs: {missing}",
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="Required input missing.",
            )

        if not direct_input_mode:
            missing_vectors = [
                name for name in self.REQUIRED_INPUTS if name not in vectors
            ]

            if missing_vectors:
                warnings.append(
                    make_warning(
                        WarningSeverity.BLOCKING,
                        "MISSING_REQUIRED_FEATURE_VECTORS",
                        f"Missing required FeatureVectors: {missing_vectors}",
                    )
                )

                return self._failed_result(
                    deal_master_id=deal_master_id,
                    inputs=inputs,
                    warnings=warnings,
                    reason="Required FeatureVector missing.",
                )

        pd_type = str(inputs.get("pd_type", "structural_raw")).lower()

        try:
            pd_12m_input = self._to_ratio(inputs["pd_12m"], "pd_12m")
            days_to_maturity_input = self._to_float(
                inputs["days_to_maturity"],
                "days_to_maturity",
            )
        except ValueError as exc:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "INPUT_CONVERSION_OR_VALIDATION_FAILED",
                    str(exc),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="Input conversion or validation failed.",
            )

        pd_12m = pd_12m_input

        if pd_12m < self.PD_FLOOR:
            pd_12m = self.PD_FLOOR
            warnings.append(
                make_warning(
                    WarningSeverity.CAUTION,
                    "PD_FLOORED_MINIMUM_HAZARD",
                    (
                        f"pd_12m input {pd_12m_input:.4%} was floored to "
                        f"{self.PD_FLOOR:.4%}, consistent with IFRS9 Stage 1 PD floor."
                    ),
                )
            )

        pd_input_is_manual = self._pd_input_is_manual(
            vectors=vectors,
            pd_type=pd_type,
        )
        manual_pd_contagion_detected = pd_input_is_manual

        if manual_pd_contagion_detected:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "MANUAL_PD_INPUT_CONTAGION",
                    (
                        "pd_12m is manual or pd_type=manual. This contaminates the hazard "
                        "curve and prevents direct gate feed."
                    ),
                )
            )

        if days_to_maturity_input <= 0:
            return self._maturity_expired_fallback(
                deal_master_id=deal_master_id,
                inputs=inputs,
                vectors=vectors,
                direct_input_mode=direct_input_mode,
                strict_vector_mode=strict_vector_mode,
                pd_12m_input=pd_12m_input,
                pd_12m=pd_12m,
                pd_type=pd_type,
                pd_input_is_manual=pd_input_is_manual,
                manual_pd_contagion_detected=manual_pd_contagion_detected,
                days_to_maturity_input=days_to_maturity_input,
                warnings=warnings,
            )

        days_to_maturity_eff = days_to_maturity_input
        days_to_maturity_capped = False

        if days_to_maturity_input > self.MAX_DAYS_TO_MATURITY:
            days_to_maturity_eff = self.MAX_DAYS_TO_MATURITY
            days_to_maturity_capped = True

            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "DAYS_TO_MATURITY_CAPPED_AT_PRIVATE_CREDIT_OPERATING_RANGE",
                    (
                        f"days_to_maturity_input={days_to_maturity_input:.2f} exceeds "
                        f"private-credit operating range cap "
                        f"{self.MAX_DAYS_TO_MATURITY:.2f}. "
                        "days_to_maturity_eff is capped for hazard calculation."
                    ),
                )
            )

        exact_years = days_to_maturity_eff / self.DAYS_PER_YEAR
        N = max(1, int(math.ceil(exact_years)))

        tail_ratio_invalid_fallback_applied = False
        tail_balance_ratio_present = (
            "tail_balance_ratio" in inputs
            and inputs.get("tail_balance_ratio") is not None
        )

        try:
            tail_ratio_info = self._resolve_tail_ratio(inputs, warnings)
        except ValueError as exc:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "TAIL_BALANCE_RATIO_CONVERSION_FAILED_NEUTRAL_FALLBACK",
                    (
                        f"{exc}. tail_ratio_eff set to 1.0 for calculation continuity. "
                        "Output must not feed deal gate."
                    ),
                )
            )

            tail_ratio_info = {
                "tail_ratio_input": inputs.get("tail_balance_ratio"),
                "tail_ratio_eff": 1.0,
                "tail_ratio_invalid_fallback_applied": True,
                "tail_ratio_missing": False,
            }

        tail_ratio_input = tail_ratio_info["tail_ratio_input"]
        tail_ratio_eff = float(tail_ratio_info["tail_ratio_eff"])
        tail_ratio_invalid_fallback_applied = bool(
            tail_ratio_info["tail_ratio_invalid_fallback_applied"]
        )
        tail_ratio_missing = bool(tail_ratio_info["tail_ratio_missing"])

        is_amortizing = tail_ratio_eff < 1.0

        if N == 1:
            warnings.append(
                make_warning(
                    WarningSeverity.CAUTION,
                    "SHORT_MATURITY_SINGLE_PERIOD_HAZARD",
                    (
                        "N == 1. Hazard curve has no ramp period and only terminal jump. "
                        "This is intentional for short maturity-wall risk."
                    ),
                )
            )

            if tail_ratio_eff == 1.0:
                warnings.append(
                    make_warning(
                        WarningSeverity.CAUTION,
                        "SHORT_MATURITY_NO_TAIL_UPLIFT_HAZARD_EQUALS_12M_PD",
                        (
                            "N == 1 and tail_ratio_eff == 1.0. Hazard lifetime PD will "
                            "be close to 12M PD unless other clamps or floors apply."
                        ),
                    )
                )

        slope_mid = 1.0 + (tail_ratio_eff - 1.0) * 0.5

        hazard_curve: List[Dict[str, Any]] = []
        hazard_rate_clamped = False
        hazard_rate_clamp_count = 0
        hazard_rate_clamp_periods: List[int] = []
        terminal_hazard_clamped = False
        ramp_hazard_clamp_count = 0

        for t in range(1, N):
            raw_hazard = pd_12m * (1.0 + (t / N) * (slope_mid - 1.0))

            if raw_hazard < 0.0:
                warnings.append(
                    make_warning(
                        WarningSeverity.BLOCKING,
                        "NEGATIVE_RAMP_HAZARD_RATE_COMPUTED",
                        (
                            f"Negative ramp hazard computed at t={t}: {raw_hazard}. "
                            "This indicates invalid tail ratio or model logic."
                        ),
                    )
                )

                return self._failed_result(
                    deal_master_id=deal_master_id,
                    inputs=inputs,
                    warnings=warnings,
                    reason="Negative ramp hazard rate computed.",
                )

            clamped_hazard = min(raw_hazard, self.MAX_HAZARD_RATE)
            clamped = clamped_hazard < raw_hazard

            if clamped:
                hazard_rate_clamped = True
                hazard_rate_clamp_count += 1
                hazard_rate_clamp_periods.append(t)
                ramp_hazard_clamp_count += 1

            hazard_curve.append(
                {
                    "t": t,
                    "period_type": "RAMP",
                    "raw_hazard": raw_hazard,
                    "hazard_rate": clamped_hazard,
                    "clamped": clamped,
                }
            )

        terminal_raw_hazard = pd_12m * tail_ratio_eff

        if terminal_raw_hazard < 0.0:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "NEGATIVE_TERMINAL_HAZARD_RATE_COMPUTED",
                    (
                        f"Negative terminal hazard computed: {terminal_raw_hazard}. "
                        "This indicates invalid tail ratio or model logic."
                    ),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="Negative terminal hazard rate computed.",
            )

        terminal_hazard = min(terminal_raw_hazard, self.MAX_HAZARD_RATE)
        terminal_clamped = terminal_hazard < terminal_raw_hazard

        if terminal_clamped:
            hazard_rate_clamped = True
            hazard_rate_clamp_count += 1
            hazard_rate_clamp_periods.append(N)
            terminal_hazard_clamped = True

        hazard_curve.append(
            {
                "t": N,
                "period_type": "TERMINAL_JUMP",
                "raw_hazard": terminal_raw_hazard,
                "hazard_rate": terminal_hazard,
                "clamped": terminal_clamped,
            }
        )

        all_hazard_rates_clamped = (
            bool(hazard_curve)
            and all(bool(item["clamped"]) for item in hazard_curve)
        )

        single_terminal_clamp_only = (
            hazard_rate_clamp_count == 1
            and terminal_hazard_clamped
            and ramp_hazard_clamp_count == 0
        )

        if hazard_rate_clamped:
            if all_hazard_rates_clamped:
                warnings.append(
                    make_warning(
                        WarningSeverity.CRITICAL,
                        "ALL_HAZARD_RATES_AT_CEILING_FORCED_REVIEW",
                        (
                            "All hazard rates were clamped to the log-stability ceiling. "
                            "Output must not feed deal gate."
                        ),
                    )
                )
            elif single_terminal_clamp_only:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "TERMINAL_HAZARD_RATE_CLAMPED_REVIEW",
                        (
                            "Only terminal hazard was clamped. This may be valid for "
                            "maturity-wall stress, but requires review."
                        ),
                    )
                )
            else:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "MULTIPLE_OR_RAMP_HAZARD_RATES_CLAMPED_REVIEW",
                        (
                            "Ramp and/or multiple hazard rates were clamped. This indicates "
                            "severe hazard pressure and should restrict direct gate feed."
                        ),
                    )
                )

        sum_log = 0.0
        sum_log_saturated = False
        saturation_triggered_at_period: Optional[int] = None

        try:
            for item in hazard_curve:
                t = int(item["t"])
                h_t = float(item["hazard_rate"])

                if h_t >= 1.0:
                    raise ValueError(
                        f"Hazard rate must be below 1.0 after clamp. Got {h_t}."
                    )

                if h_t < 0.0:
                    raise ValueError(f"Hazard rate cannot be negative. Got {h_t}.")

                sum_log += math.log1p(-h_t)

                if sum_log <= self.SUM_LOG_SATURATION_THRESHOLD:
                    sum_log_saturated = True
                    saturation_triggered_at_period = t

                    warnings.append(
                        make_warning(
                            WarningSeverity.CRITICAL,
                            "SUM_LOG_SATURATED_LIFETIME_PD_FORCED_TO_100",
                            (
                                f"Survival probability fell below "
                                f"{self.SURVIVAL_PROBABILITY_FLOOR:.1e} at period {t}. "
                                "lifetime_pd_hazard forced to 100% for numerical stability "
                                "and economic saturation."
                            ),
                        )
                    )

                    break

            if sum_log_saturated:
                lifetime_pd_hazard = 1.0
            else:
                lifetime_pd_hazard = -math.expm1(sum_log)

        except ValueError as exc:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "LOG_SPACE_HAZARD_AGGREGATION_FAILED",
                    str(exc),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="Log-space hazard aggregation failed.",
            )

        invariant_violation_detected = False
        invariant_precision_adjusted = False
        invariant_epsilon = max(1e-12, pd_12m * 1e-10)

        if not is_amortizing and not sum_log_saturated:
            if lifetime_pd_hazard < pd_12m - invariant_epsilon:
                invariant_violation_detected = True

                warnings.append(
                    make_warning(
                        WarningSeverity.CRITICAL,
                        "INVARIANT_VIOLATED_LIFETIME_PD_BELOW_12M_REVIEW_LOGIC",
                        (
                            f"lifetime_pd_hazard {lifetime_pd_hazard:.8%} is below "
                            f"pd_12m {pd_12m:.8%} beyond epsilon "
                            f"{invariant_epsilon:.2e}. Lifetime PD floored to 12M PD."
                        ),
                    )
                )

                lifetime_pd_hazard = pd_12m

            elif lifetime_pd_hazard < pd_12m:
                invariant_precision_adjusted = True

                warnings.append(
                    make_warning(
                        WarningSeverity.CAUTION,
                        "LIFETIME_PD_FLOAT_PRECISION_ADJUSTED",
                        (
                            f"lifetime_pd_hazard {lifetime_pd_hazard:.8%} was slightly "
                            f"below pd_12m {pd_12m:.8%} within floating-point epsilon. "
                            "Adjusted to pd_12m."
                        ),
                    )
                )

                lifetime_pd_hazard = pd_12m

        if is_amortizing and not sum_log_saturated:
            if lifetime_pd_hazard < pd_12m * 0.10:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "AMORTIZING_LIFETIME_PD_EXTREMELY_LOW_VERIFY_DATA",
                        (
                            f"Amortizing lifetime PD {lifetime_pd_hazard:.8%} is below "
                            f"10% of pd_12m {pd_12m:.8%}. Verify tail balance data."
                        ),
                    )
                )

        pd_flat_lifetime = 1.0 - ((1.0 - pd_12m) ** exact_years)

        hazard_lift_vs_flat: Optional[float]

        if invariant_violation_detected:
            hazard_lift_vs_flat = None
            warnings.append(
                make_warning(
                    WarningSeverity.CAUTION,
                    "HAZARD_LIFT_UNDEFINED_DUE_TO_INVARIANT_VIOLATION",
                    (
                        "hazard_lift_vs_flat is undefined because lifetime PD was floored "
                        "after invariant violation."
                    ),
                )
            )
        elif pd_flat_lifetime > 0:
            hazard_lift_vs_flat = lifetime_pd_hazard / pd_flat_lifetime
        else:
            hazard_lift_vs_flat = None

        if hazard_lift_vs_flat is not None and hazard_lift_vs_flat < 1.0:
            if is_amortizing:
                warnings.append(
                    make_warning(
                        WarningSeverity.CAUTION,
                        "HAZARD_LIFT_BELOW_1_EXPECTED_FOR_AMORTIZING_STRUCTURE",
                        (
                            f"hazard_lift_vs_flat={hazard_lift_vs_flat:.4f}. "
                            "This is expected when amortizing structure reduces terminal risk."
                        ),
                    )
                )
            else:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "HAZARD_LIFT_BELOW_1_IN_NON_AMORTIZING_DEAL",
                        (
                            f"hazard_lift_vs_flat={hazard_lift_vs_flat:.4f} in a "
                            "non-amortizing deal. Verify hazard curve logic."
                        ),
                    )
                )

        severe_clamp_gate_block = (
            all_hazard_rates_clamped
            or ramp_hazard_clamp_count > 0
            or hazard_rate_clamp_count > 1
        )

        should_feed_directly_to_deal_gate = (
            not direct_input_mode
            and not invariant_violation_detected
            and not sum_log_saturated
            and not severe_clamp_gate_block
            and not tail_ratio_invalid_fallback_applied
            and not manual_pd_contagion_detected
        )

        confidence, confidence_metrics = self._build_confidence(
            vectors=vectors,
            direct_input_mode=direct_input_mode,
            tail_balance_ratio_present=tail_balance_ratio_present,
            warnings=warnings,
            invariant_violation_detected=invariant_violation_detected,
            hazard_rate_clamp_count=hazard_rate_clamp_count,
            all_hazard_rates_clamped=all_hazard_rates_clamped,
            sum_log_saturated=sum_log_saturated,
            pd_type=pd_type,
            pd_input_is_manual=pd_input_is_manual,
        )

        metrics = {
            "calculation_status": "COMPLETED",
            "hazard_method": "PIECEWISE_HOUSE_RULE",
            "actual_engine": "piecewise_hazard_engine",
            "engine_alias_warning": (
                "ENGINE_NAME_COX_BUT_METHOD_PIECEWISE_HOUSE_RULE"
            ),

            "pd_12m_input": pd_12m_input,
            "pd_12m_used": pd_12m,
            "pd_floor_applied": pd_12m > pd_12m_input,
            "pd_type": pd_type,
            "pd_input_is_manual": pd_input_is_manual,
            "manual_pd_contagion_detected": manual_pd_contagion_detected,

            "days_to_maturity": days_to_maturity_input,
            "days_to_maturity_input": days_to_maturity_input,
            "days_to_maturity_eff": days_to_maturity_eff,
            "days_to_maturity_capped": days_to_maturity_capped,
            "max_days_to_maturity": self.MAX_DAYS_TO_MATURITY,
            "maturity_cap_basis": "PRIVATE_CREDIT_OPERATING_RANGE_CAP",
            "days_per_year": self.DAYS_PER_YEAR,
            "exact_years": exact_years,
            "N": N,

            "tail_balance_ratio_input": tail_ratio_input,
            "tail_ratio_eff": tail_ratio_eff,
            "tail_ratio_missing": tail_ratio_missing,
            "tail_ratio_invalid_fallback_applied": tail_ratio_invalid_fallback_applied,
            "is_amortizing": is_amortizing,
            "slope_mid": slope_mid,

            "hazard_curve": hazard_curve,
            "lifetime_pd_hazard": lifetime_pd_hazard,
            "pd_flat_lifetime": pd_flat_lifetime,
            "pd_flat_lifetime_method": "EXACT_YEARS_365_25",
            "hazard_lift_vs_flat": hazard_lift_vs_flat,

            "sum_log": sum_log,
            "survival_probability_floor": self.SURVIVAL_PROBABILITY_FLOOR,
            "sum_log_saturation_threshold": self.SUM_LOG_SATURATION_THRESHOLD,
            "sum_log_saturated": sum_log_saturated,
            "saturation_triggered_at_period": saturation_triggered_at_period,
            "hazard_rate_clamp_detected": hazard_rate_clamped,
            "hazard_rate_clamp_count": hazard_rate_clamp_count,
            "hazard_rate_clamp_periods": hazard_rate_clamp_periods,
            "all_hazard_rates_clamped": all_hazard_rates_clamped,
            "terminal_hazard_clamped": terminal_hazard_clamped,
            "ramp_hazard_clamp_count": ramp_hazard_clamp_count,
            "single_terminal_clamp_only": single_terminal_clamp_only,
            "severe_clamp_gate_block": severe_clamp_gate_block,

            "invariant_violation_detected": invariant_violation_detected,
            "invariant_precision_adjusted": invariant_precision_adjusted,
            "invariant_epsilon": invariant_epsilon,

            "warning_summary": warning_summary(warnings),
            "strict_vector_mode": strict_vector_mode,
            "direct_input_mode": direct_input_mode,
            "non_production_input_mode": direct_input_mode,
            "should_feed_directly_to_deal_gate": should_feed_directly_to_deal_gate,
            "house_rule_version": inputs.get(
                "house_rule_version",
                "COSMOS_PIECEWISE_HAZARD_v0.2",
            ),
            "override_approver": inputs.get("override_approver"),

            **confidence_metrics,
        }

        return self._result(
            deal_master_id=deal_master_id,
            inputs=inputs,
            vectors=vectors,
            direct_input_mode=direct_input_mode,
            metrics=metrics,
            confidence=confidence,
            warnings=warnings,
        )

    def _maturity_expired_fallback(
        self,
        *,
        deal_master_id: int,
        inputs: Dict[str, Any],
        vectors: Optional[Dict[str, Any]],
        direct_input_mode: bool,
        strict_vector_mode: bool,
        pd_12m_input: float,
        pd_12m: float,
        pd_type: str,
        pd_input_is_manual: bool,
        manual_pd_contagion_detected: bool,
        days_to_maturity_input: float,
        warnings: List[str],
    ) -> EngineResult:
        warnings.append(
            make_warning(
                WarningSeverity.CRITICAL,
                "MATURITY_EXPIRED_OR_ZERO_HAZARD_MODEL_NOT_APPLICABLE",
                (
                    f"days_to_maturity={days_to_maturity_input}. "
                    "Hazard curve is not applicable. Returning 12M PD fallback."
                ),
            )
        )

        confidence, confidence_metrics = self._build_confidence(
            vectors=vectors,
            direct_input_mode=direct_input_mode,
            tail_balance_ratio_present=(
                "tail_balance_ratio" in inputs
                and inputs.get("tail_balance_ratio") is not None
            ),
            warnings=warnings,
            invariant_violation_detected=False,
            hazard_rate_clamp_count=0,
            all_hazard_rates_clamped=False,
            sum_log_saturated=False,
            pd_type=pd_type,
            pd_input_is_manual=pd_input_is_manual,
        )

        metrics = {
            "calculation_status": "MATURITY_EXPIRED_FALLBACK",
            "hazard_method": "PIECEWISE_HOUSE_RULE",
            "actual_engine": "piecewise_hazard_engine",
            "engine_alias_warning": (
                "ENGINE_NAME_COX_BUT_METHOD_PIECEWISE_HOUSE_RULE"
            ),

            "pd_12m_input": pd_12m_input,
            "pd_12m_used": pd_12m,
            "pd_floor_applied": pd_12m > pd_12m_input,
            "pd_type": pd_type,
            "pd_input_is_manual": pd_input_is_manual,
            "manual_pd_contagion_detected": manual_pd_contagion_detected,

            "days_to_maturity": days_to_maturity_input,
            "days_to_maturity_input": days_to_maturity_input,
            "days_to_maturity_eff": 0.0,
            "days_to_maturity_capped": False,
            "max_days_to_maturity": self.MAX_DAYS_TO_MATURITY,
            "maturity_cap_basis": "PRIVATE_CREDIT_OPERATING_RANGE_CAP",
            "days_per_year": self.DAYS_PER_YEAR,
            "exact_years": 0.0,
            "N": 0,

            "tail_balance_ratio_input": inputs.get("tail_balance_ratio"),
            "tail_ratio_eff": None,
            "tail_ratio_missing": inputs.get("tail_balance_ratio") is None,
            "tail_ratio_invalid_fallback_applied": False,
            "is_amortizing": False,
            "slope_mid": None,

            "hazard_curve": [],
            "lifetime_pd_hazard": pd_12m,
            "pd_flat_lifetime": pd_12m,
            "pd_flat_lifetime_method": "MATURITY_EXPIRED_FALLBACK",
            "hazard_lift_vs_flat": None,

            "sum_log": None,
            "survival_probability_floor": self.SURVIVAL_PROBABILITY_FLOOR,
            "sum_log_saturation_threshold": self.SUM_LOG_SATURATION_THRESHOLD,
            "sum_log_saturated": False,
            "saturation_triggered_at_period": None,
            "hazard_rate_clamp_detected": False,
            "hazard_rate_clamp_count": 0,
            "hazard_rate_clamp_periods": [],
            "all_hazard_rates_clamped": False,
            "terminal_hazard_clamped": False,
            "ramp_hazard_clamp_count": 0,
            "single_terminal_clamp_only": False,
            "severe_clamp_gate_block": False,

            "invariant_violation_detected": False,
            "invariant_precision_adjusted": False,
            "invariant_epsilon": max(1e-12, pd_12m * 1e-10),

            "warning_summary": warning_summary(warnings),
            "strict_vector_mode": strict_vector_mode,
            "direct_input_mode": direct_input_mode,
            "non_production_input_mode": direct_input_mode,
            "should_feed_directly_to_deal_gate": False,
            "house_rule_version": inputs.get(
                "house_rule_version",
                "COSMOS_PIECEWISE_HAZARD_v0.2",
            ),
            "override_approver": inputs.get("override_approver"),

            **confidence_metrics,
        }

        return self._result(
            deal_master_id=deal_master_id,
            inputs=inputs,
            vectors=vectors,
            direct_input_mode=direct_input_mode,
            metrics=metrics,
            confidence=confidence,
            warnings=warnings,
        )

    def _resolve_tail_ratio(
        self,
        inputs: Dict[str, Any],
        warnings: List[str],
    ) -> Dict[str, Any]:
        raw = inputs.get("tail_balance_ratio")

        if raw is None:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "TAIL_BALANCE_RATIO_MISSING_NO_MATURITY_UPLIFT",
                    (
                        "tail_balance_ratio is missing. No reverse-debt maturity uplift "
                        "is applied. tail_ratio_eff set to 1.0."
                    ),
                )
            )

            return {
                "tail_ratio_input": None,
                "tail_ratio_eff": 1.0,
                "tail_ratio_invalid_fallback_applied": False,
                "tail_ratio_missing": True,
            }

        try:
            tail_ratio = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"tail_balance_ratio cannot be converted to float: {raw}"
            ) from exc

        if not math.isfinite(tail_ratio):
            raise ValueError(
                f"tail_balance_ratio must be finite. Got {tail_ratio}."
            )

        if tail_ratio < 0.0:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "NEGATIVE_TAIL_BALANCE_RATIO_INVALID_NEUTRAL_FALLBACK",
                    (
                        f"tail_balance_ratio={tail_ratio:.4f} is negative. "
                        "Negative debt tail is invalid. tail_ratio_eff set to 1.0 "
                        "for calculation continuity, but output must not feed deal gate."
                    ),
                )
            )

            return {
                "tail_ratio_input": tail_ratio,
                "tail_ratio_eff": 1.0,
                "tail_ratio_invalid_fallback_applied": True,
                "tail_ratio_missing": False,
            }

        if tail_ratio < 1.0:
            if tail_ratio < 0.30:
                warnings.append(
                    make_warning(
                        WarningSeverity.MATERIAL,
                        "EXTREME_AMORTIZING_TAIL_RATIO_VERIFY_DATA",
                        (
                            f"tail_balance_ratio={tail_ratio:.4f} is below 0.30. "
                            "Amortizing risk reduction is reflected, but data should be verified."
                        ),
                    )
                )
            else:
                warnings.append(
                    make_warning(
                        WarningSeverity.CAUTION,
                        "AMORTIZING_STRUCTURE_MATURITY_RISK_REDUCED",
                        (
                            f"tail_balance_ratio={tail_ratio:.4f} is below 1.0. "
                            "Terminal hazard is reduced to reflect amortizing structure."
                        ),
                    )
                )

            return {
                "tail_ratio_input": tail_ratio,
                "tail_ratio_eff": tail_ratio,
                "tail_ratio_invalid_fallback_applied": False,
                "tail_ratio_missing": False,
            }

        if tail_ratio > self.MAX_TAIL_BALANCE_RATIO:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "TAIL_BALANCE_RATIO_CAPPED_AT_3X",
                    (
                        f"tail_balance_ratio={tail_ratio:.4f} exceeds "
                        f"{self.MAX_TAIL_BALANCE_RATIO:.1f}x. "
                        "Capped at 3.0x for hazard slope stability."
                    ),
                )
            )

            return {
                "tail_ratio_input": tail_ratio,
                "tail_ratio_eff": self.MAX_TAIL_BALANCE_RATIO,
                "tail_ratio_invalid_fallback_applied": False,
                "tail_ratio_missing": False,
            }

        return {
            "tail_ratio_input": tail_ratio,
            "tail_ratio_eff": tail_ratio,
            "tail_ratio_invalid_fallback_applied": False,
            "tail_ratio_missing": False,
        }

    def _build_confidence(
        self,
        *,
        vectors: Optional[Dict[str, Any]],
        direct_input_mode: bool,
        tail_balance_ratio_present: bool,
        warnings: List[str],
        invariant_violation_detected: bool,
        hazard_rate_clamp_count: int,
        all_hazard_rates_clamped: bool,
        sum_log_saturated: bool,
        pd_type: str,
        pd_input_is_manual: bool,
    ):
        data_confidence = self._data_confidence(
            vectors=vectors,
            direct_input_mode=direct_input_mode,
            tail_balance_ratio_present=tail_balance_ratio_present,
            pd_type=pd_type,
            pd_input_is_manual=pd_input_is_manual,
        )

        model_fit_confidence = 0.85

        if pd_input_is_manual:
            model_fit_confidence *= 0.50

        if pd_type == "structural_raw":
            model_fit_confidence *= 0.80

        if invariant_violation_detected:
            model_fit_confidence *= 0.30

        if sum_log_saturated:
            model_fit_confidence *= 0.70

        if all_hazard_rates_clamped:
            model_fit_confidence *= 0.50
        elif hazard_rate_clamp_count > 0:
            model_fit_confidence *= 0.70

        execution_confidence = self._execution_confidence(warnings)

        final_score = min(
            data_confidence,
            model_fit_confidence,
            execution_confidence,
        )

        profile = warning_profile(warnings)

        if profile["blocking"] > 0:
            final_score *= 0.30
        elif profile["critical"] > 0:
            final_score *= 0.45
        elif profile["material"] > 0:
            final_score *= max(0.55, 1.0 - 0.08 * profile["material"])
        elif profile["caution"] > 0:
            final_score *= max(0.80, 1.0 - 0.03 * profile["caution"])

        final_score = max(0.0, min(1.0, final_score))

        if final_score >= 0.75:
            tier = ConfidenceTier.HIGH
        elif final_score >= 0.45:
            tier = ConfidenceTier.MEDIUM
        else:
            tier = ConfidenceTier.LOW

        confidence = ConfidenceInfo(
            tier=tier,
            score=final_score,
            reasoning=(
                "Confidence uses min-dominant aggregation of data_confidence, "
                "model_fit_confidence, and execution_confidence. Manual PD, missing tail "
                "balance ratio, hazard clamp, invariant violation, saturation, and direct "
                "input mode are penalized."
            ),
        )

        metrics = {
            "data_confidence": data_confidence,
            "model_fit_confidence": model_fit_confidence,
            "execution_confidence": execution_confidence,
            "model_fit_flag": self._fit_flag(model_fit_confidence),
        }

        return confidence, metrics

    def _data_confidence(
        self,
        *,
        vectors: Optional[Dict[str, Any]],
        direct_input_mode: bool,
        tail_balance_ratio_present: bool,
        pd_type: str,
        pd_input_is_manual: bool,
    ) -> float:
        if direct_input_mode or not vectors:
            return self.DIRECT_INPUT_CONFIDENCE

        scores: List[float] = []

        for name in ["pd_12m", "days_to_maturity", "tail_balance_ratio"]:
            vector = vectors.get(name)

            if name == "tail_balance_ratio" and not tail_balance_ratio_present:
                scores.append(0.30)
                continue

            if vector is not None and hasattr(vector, "confidence_score"):
                score = float(vector.confidence_score)

                if name == "pd_12m":
                    source_type = getattr(vector, "source_type", None)

                    if source_type == SourceType.MANUAL or pd_type == "manual":
                        score = self.DIRECT_INPUT_CONFIDENCE

                scores.append(max(0.0, min(1.0, score)))
            else:
                scores.append(self.DIRECT_INPUT_CONFIDENCE)

        if pd_input_is_manual:
            scores.append(self.DIRECT_INPUT_CONFIDENCE)

        weakest = min(scores)
        average = sum(scores) / len(scores)

        return max(0.0, min(1.0, 0.75 * weakest + 0.25 * average))

    def _execution_confidence(self, warnings: List[str]) -> float:
        profile = warning_profile(warnings)

        if profile["blocking"] > 0:
            return 0.30

        return 0.95

    def _fit_flag(self, score: float) -> str:
        if score >= 0.70:
            return "HIGH_FIT"

        if score >= 0.45:
            return "MEDIUM_FIT"

        return "LOW_FIT"

    def _failed_confidence(self, reason: str) -> ConfidenceInfo:
        return ConfidenceInfo(
            tier=ConfidenceTier.LOW,
            score=0.0,
            reasoning=f"Piecewise hazard calculation failed: {reason}",
        )

    def _result(
        self,
        *,
        deal_master_id: int,
        inputs: Dict[str, Any],
        vectors: Optional[Dict[str, Any]],
        direct_input_mode: bool,
        metrics: Dict[str, Any],
        confidence: ConfidenceInfo,
        warnings: List[str],
    ) -> EngineResult:
        return EngineResult(
            deal_master_id=deal_master_id,
            engine_name=self.engine_name,
            metrics=metrics,
            confidence=confidence,
            provenance=Provenance(
                model_version=self.model_version,
                engine_name=self.engine_name,
                inputs=self._build_provenance_inputs(
                    inputs=inputs,
                    vectors=vectors,
                    direct_input_mode=direct_input_mode,
                ),
                notes=(
                    "Engine name is cox_hazard_engine for registry compatibility, "
                    "but actual method is PIECEWISE_HOUSE_RULE, not Cox Proportional "
                    "Hazards. Terminal jump at maturity is intentional. Fallbacks are "
                    "calculation-continuity mechanisms and do not imply gate-use permission. "
                    "Output lifetime_pd_hazard is designed to feed IFRS9 ECL "
                    "hazard_lifetime_pd."
                ),
            ),
            warnings=warnings,
        )

    def _failed_result(
        self,
        *,
        deal_master_id: int,
        inputs: Dict[str, Any],
        warnings: List[str],
        reason: str,
    ) -> EngineResult:
        direct_input_mode = not isinstance(inputs.get("_vectors"), dict)

        return EngineResult(
            deal_master_id=deal_master_id,
            engine_name=self.engine_name,
            metrics={
                "calculation_status": "FAILED",
                "failure_reason": reason,
                "hazard_method": "PIECEWISE_HOUSE_RULE",
                "actual_engine": "piecewise_hazard_engine",
                "engine_alias_warning": (
                    "ENGINE_NAME_COX_BUT_METHOD_PIECEWISE_HOUSE_RULE"
                ),
                "hazard_curve": [],
                "lifetime_pd_hazard": None,
                "pd_flat_lifetime": None,
                "hazard_lift_vs_flat": None,
                "sum_log_saturated": False,
                "saturation_triggered_at_period": None,
                "invariant_violation_detected": None,
                "tail_ratio_invalid_fallback_applied": None,
                "pd_input_is_manual": None,
                "manual_pd_contagion_detected": None,
                "warning_summary": warning_summary(warnings),
                "should_feed_directly_to_deal_gate": False,
                "non_production_input_mode": direct_input_mode,
            },
            confidence=self._failed_confidence(reason),
            provenance=Provenance(
                model_version=self.model_version,
                engine_name=self.engine_name,
                inputs=self._build_provenance_inputs(
                    inputs=inputs,
                    vectors=inputs.get("_vectors")
                    if isinstance(inputs.get("_vectors"), dict)
                    else {},
                    direct_input_mode=direct_input_mode,
                ),
                notes=(
                    "Piecewise hazard calculation failed before valid output. "
                    "Failure represents technical or policy failure, not a hazard result."
                ),
            ),
            warnings=warnings,
        )

    def _build_provenance_inputs(
        self,
        *,
        inputs: Dict[str, Any],
        vectors: Optional[Dict[str, Any]],
        direct_input_mode: bool,
    ) -> List[ProvenanceInput]:
        vectors = vectors or {}
        provenance_inputs: List[ProvenanceInput] = []

        for name in self.REQUIRED_INPUTS + self.OPTIONAL_INPUTS:
            if name not in inputs and name not in vectors:
                continue

            vector = vectors.get(name)

            if vector is not None and hasattr(vector, "to_provenance_input"):
                provenance_inputs.append(vector.to_provenance_input())
                continue

            if direct_input_mode:
                provenance_inputs.append(
                    ProvenanceInput(
                        metric_name=name,
                        value=inputs.get(name),
                        source_type=SourceType.MANUAL,
                        source_detail=(
                            "direct_piecewise_hazard_input_without_feature_vector_dev_mode"
                        ),
                        as_of_date=datetime.now(timezone.utc),
                        confidence_contribution=self.DIRECT_INPUT_CONFIDENCE,
                    )
                )

        return provenance_inputs

    def _pd_input_is_manual(
        self,
        *,
        vectors: Optional[Dict[str, Any]],
        pd_type: str,
    ) -> bool:
        if pd_type == "manual":
            return True

        vectors = vectors or {}
        vector = vectors.get("pd_12m")

        if vector is None:
            return False

        return getattr(vector, "source_type", None) == SourceType.MANUAL

    def _strict_vector_mode(self) -> bool:
        raw = os.getenv("COSMOS_STRICT_VECTOR_MODE", "true").strip().lower()
        return raw not in {"false", "0", "no", "n"}

    def _to_float(self, value: Any, field_name: str) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} cannot be converted to float: {value}") from exc

        if not math.isfinite(result):
            raise ValueError(f"{field_name} must be finite. Got {result}.")

        return result

    def _to_ratio(self, value: Any, field_name: str) -> float:
        result = self._to_float(value, field_name)

        if result < 0.0 or result > 1.0:
            raise ValueError(f"{field_name} must be a ratio between 0.0 and 1.0.")

        return result
