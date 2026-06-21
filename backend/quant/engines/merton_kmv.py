from __future__ import annotations

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
from quant.structural.structural_confidence import StructuralConfidenceBuilder
from quant.structural.structural_math import StructuralMath
from quant.structural.structural_policy import (
    StructuralPolicyError,
    StructuralPolicyLayer,
)
from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
    warning_summary,
)


class MertonKMVEngine(QuantEngine):
    """
    COSMOS Structural Distance Engine v0.3

    Registry 호환을 위해 engine_name은 merton_kmv로 유지한다.

    역할:
    - StructuralPolicyLayer 호출
    - StructuralMath 호출
    - StructuralConfidenceBuilder 호출
    - EngineResult 포장

    이 엔진은 최종 underwriting PD 엔진이 아니다.
    출력 PD는 pd_structural_raw이며, calibration / hazard / refi / behavioral overlay
    이전의 구조적 raw signal이다.
    """

    engine_name = "merton_kmv"
    model_version = "v0.3"

    REQUIRED_INPUTS = [
        "avm_value",
        "avm_sigma",
        "current_debt_balance",
        "default_threshold",
        "days_to_maturity",
        "asset_class",
        "collateral_type",
        "valuation_date",
        "debt_as_of_date",
        "sigma_method",
        "liquidity_haircut",
        "enforcement_cost_ratio",
    ]

    OPTIONAL_INPUTS = [
        "horizon_years",
        "jurisdictional_friction_haircut",
        "asset_drift",
        "breach_ltv_floor",
        "valuation_confidence",
        "house_rule_version",
        "override_approver",
        "manual_override_flag",
    ]

    def __init__(self) -> None:
        self.policy_layer = StructuralPolicyLayer()
        self.structural_math = StructuralMath()
        self.confidence_builder = StructuralConfidenceBuilder()

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
                        "objects. Direct numeric input is blocked."
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
                    WarningSeverity.MATERIAL,
                    "DIRECT_INPUT_LOW_CONFIDENCE_MODE",
                    (
                        "FeatureVector layer missing. Direct input is allowed only because "
                        "strict vector mode is disabled. Data confidence is forced to LOW."
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

        try:
            policy_output = self.policy_layer.apply(
                inputs=inputs,
                vectors=vectors,
            )
        except StructuralPolicyError as exc:
            warnings.append(str(exc))

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="Structural policy violation.",
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

        warnings.extend(policy_output.warnings)

        try:
            gross_result = self.structural_math.calculate_structural_point(
                asset_value=policy_output.avm_value,
                default_barrier=policy_output.default_barrier,
                sigma=policy_output.avm_sigma_effective,
                horizon_years=policy_output.locked_horizon_years,
                drift=policy_output.effective_asset_drift,
                label="GROSS",
            )

            effective_result = self.structural_math.calculate_structural_point(
                asset_value=policy_output.effective_asset_value,
                default_barrier=policy_output.default_barrier,
                sigma=policy_output.avm_sigma_effective,
                horizon_years=policy_output.locked_horizon_years,
                drift=policy_output.effective_asset_drift,
                label="EFFECTIVE",
            )

        except ValueError as exc:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "STRUCTURAL_MATH_FAILED",
                    str(exc),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="Structural math failed.",
            )

        warnings.extend(gross_result.warnings)
        warnings.extend(effective_result.warnings)

        risk_state = self._risk_state(
            gross_state=gross_result.risk_state,
            effective_state=effective_result.risk_state,
        )

        confidence, confidence_metrics = self.confidence_builder.build(
            inputs=inputs,
            vectors=vectors,
            required_inputs=self.REQUIRED_INPUTS,
            policy_output=policy_output,
            warnings=warnings,
            direct_input_mode=direct_input_mode,
        )

        summary = warning_summary(warnings)

        calculation_status = (
            "EXTREME_RISK_COMPLETED"
            if risk_state == "EXTREME_RISK"
            else "COMPLETED"
        )

        metrics = {
            "calculation_status": calculation_status,
            "risk_state": risk_state,
            "engine_role": "structural_distance_subengine",
            "should_feed_directly_to_deal_gate": False,
            "calibration_required": True,
            "final_underwriting_pd_available": False,
            "distance_to_default_gross": gross_result.distance_to_default,
            "distance_to_default_effective": effective_result.distance_to_default,
            "pd_structural_raw_gross": gross_result.pd_structural_raw,
            "pd_structural_raw": effective_result.pd_structural_raw,
            "pd_structural_calibrated": None,
            "gross_absolute_default_triggered": gross_result.absolute_default_triggered,
            "effective_absolute_default_triggered": (
                effective_result.absolute_default_triggered
            ),
            "pd_forced_to_100": (
                gross_result.forced_pd_100 or effective_result.forced_pd_100
            ),
            "asset_value_proxy": policy_output.avm_value,
            "effective_asset_value": policy_output.effective_asset_value,
            "current_debt_balance": policy_output.current_debt_balance,
            "default_threshold": policy_output.default_threshold,
            "default_barrier": policy_output.default_barrier,
            "breach_ltv_floor": policy_output.breach_ltv_floor,
            "current_ltv_gross": policy_output.current_ltv_gross,
            "current_ltv_effective": policy_output.current_ltv_effective,
            "threshold_ltv_gross": policy_output.threshold_ltv_gross,
            "threshold_ltv_effective": policy_output.threshold_ltv_effective,
            "avm_sigma_input": policy_output.avm_sigma_input,
            "avm_sigma_floored": policy_output.avm_sigma_floored,
            "avm_sigma_effective": policy_output.avm_sigma_effective,
            "volatility_floor_applied": (
                policy_output.avm_sigma_floored > policy_output.avm_sigma_input
            ),
            "sigma_method": policy_output.sigma_method,
            "asset_drift_input": policy_output.asset_drift_input,
            "effective_asset_drift": policy_output.effective_asset_drift,
            "positive_drift_forced_to_zero": (
                policy_output.asset_drift_input > policy_output.effective_asset_drift
            ),
            "days_to_maturity": policy_output.days_to_maturity,
            "locked_horizon_years": policy_output.locked_horizon_years,
            "manual_horizon_years": policy_output.manual_horizon_years,
            "liquidity_haircut": policy_output.liquidity_haircut,
            "enforcement_cost_ratio": policy_output.enforcement_cost_ratio,
            "jurisdictional_friction_haircut": (
                policy_output.jurisdictional_friction_haircut
            ),
            "stale_haircut": policy_output.stale_haircut,
            "total_effective_haircut": policy_output.total_effective_haircut,
            "valuation_date": policy_output.valuation_date.isoformat(),
            "debt_as_of_date": policy_output.debt_as_of_date.isoformat(),
            "valuation_staleness_days": policy_output.valuation_staleness_days,
            "debt_staleness_days": policy_output.debt_staleness_days,
            "as_of_date_gap_days": policy_output.as_of_date_gap_days,
            "asset_class": policy_output.asset_class,
            "collateral_type": policy_output.collateral_type,
            **confidence_metrics,
            "manual_override_detected": policy_output.manual_override_detected,
            "approval_required_flags": policy_output.approval_required_flags,
            "warning_summary": summary,
            "house_rule_version": inputs.get(
                "house_rule_version",
                "COSMOS_STRUCTURAL_DISTANCE_v0.3",
            ),
            "override_approver": inputs.get("override_approver"),
            "strict_vector_mode": strict_vector_mode,
            "direct_input_mode": direct_input_mode,
            "model_family": "Merton/KMV structural distance",
            "model_adaptation": "secured_credit_effective_collateral_barrier",
        }

        return EngineResult(
            deal_master_id=deal_master_id,
            engine_name=self.engine_name,
            metrics=metrics,
            confidence=confidence,
            provenance=Provenance(
                model_version=self.model_version,
                engine_name=self.engine_name,
                inputs=self._build_provenance_inputs(inputs, vectors, direct_input_mode),
                notes=(
                    "Structural distance sub-engine only. Gross and effective DD are "
                    "computed after policy-layer volatility floor, maturity lock, "
                    "non-positive drift policy, stale valuation haircut, and enforcement "
                    "friction adjustments. Raw structural PD must not be treated as final "
                    "underwriting PD without calibration, hazard, refinance, and behavioral "
                    "overlays."
                ),
            ),
            warnings=warnings,
        )

    def _risk_state(self, gross_state: str, effective_state: str) -> str:
        if "EXTREME_RISK" in {gross_state, effective_state}:
            return "EXTREME_RISK"
        return "NORMAL"

    def _strict_vector_mode(self) -> bool:
        raw = os.getenv("COSMOS_STRICT_VECTOR_MODE", "true").strip().lower()
        return raw not in {"false", "0", "no", "n"}

    def _build_provenance_inputs(
        self,
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
                            "direct_engine_input_without_feature_vector_dev_mode"
                        ),
                        as_of_date=datetime.now(timezone.utc),
                        confidence_contribution=(
                            StructuralConfidenceBuilder.DIRECT_INPUT_CONFIDENCE
                        ),
                    )
                )

        return provenance_inputs

    def _failed_result(
        self,
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
                "engine_role": "structural_distance_subengine",
                "should_feed_directly_to_deal_gate": False,
                "calibration_required": True,
                "final_underwriting_pd_available": False,
                "distance_to_default_gross": None,
                "distance_to_default_effective": None,
                "pd_structural_raw_gross": None,
                "pd_structural_raw": None,
                "pd_structural_calibrated": None,
                "warning_summary": warning_summary(warnings),
            },
            confidence=self.confidence_builder.failed_confidence(reason),
            provenance=Provenance(
                model_version=self.model_version,
                engine_name=self.engine_name,
                inputs=self._build_provenance_inputs(
                    inputs=inputs,
                    vectors=inputs.get("_vectors") if isinstance(inputs.get("_vectors"), dict) else {},
                    direct_input_mode=direct_input_mode,
                ),
                notes=(
                    "Structural distance calculation failed before valid output. "
                    "This represents technical or policy failure, not an extreme-risk "
                    "numeric result."
                ),
            ),
            warnings=warnings,
        )
