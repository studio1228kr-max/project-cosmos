from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant.base import QuantEngine
from quant.credit_loss.ifrs9_confidence import IFRS9ConfidenceBuilder
from quant.credit_loss.ifrs9_ead_policy import IFRS9EADPolicy
from quant.credit_loss.ifrs9_math import IFRS9Math
from quant.credit_loss.ifrs9_policy import IFRS9PolicyError, IFRS9PolicyLayer
from quant.schemas import EngineResult, Provenance, ProvenanceInput, SourceType
from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
    warning_summary,
)


class IFRS9ECLEngine(QuantEngine):
    """
    IFRS9 staged ECL proxy engine v0.2.

    이 엔진은 회계 판단을 확정하지 않는다.
    COSMOS 내부의 credit-loss proxy를 산출한다.

    핵심:
    - pd_accounting / pd_risk 분리
    - Stage 3 pd_accounting = 1.0 hardcoded
    - Stage 3 UL proxy = z × EAD × lgd_sigma
    - SICR / credit-impaired trigger로 stage 강제 상향
    - EAD basis / alternative EAD cross-check
    """

    engine_name = "ifrs9_ecl_engine"
    model_version = "v0.2"

    REQUIRED_INPUTS = [
        "pd",
        "lgd",
        "dd_stage",
        "remaining_term_years",
    ]

    OPTIONAL_INPUTS = [
        "lgd_sigma",
        "lgd_volatility_method",
        "pd_stage",
        "pd_lineage",
        "ead",
        "ead_primary",
        "ead_alternative",
        "current_balance",
        "undrawn_commitment",
        "ccf",
        "ead_basis",
        "ead_source_engine",
        "reverse_debt_default_threshold",
        "effective_ltv",
        "days_to_maturity",
        "maturity_risk_state",
        "refi_gate_state",
        "covenant_breach_flag",
        "payment_default_flag",
        "default_event_flag",
        "credit_impaired_flag",
        "hazard_lifetime_pd",
        "tail_balance_ratio",
        "lifetime_pd",
        "lifetime_years",
        "z_score",
        "manual_override_flag",
        "house_rule_version",
        "override_approver",
    ]

    def __init__(self) -> None:
        self.ead_policy = IFRS9EADPolicy()
        self.policy_layer = IFRS9PolicyLayer()
        self.math = IFRS9Math()
        self.confidence_builder = IFRS9ConfidenceBuilder()

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
                    "Production path requires FeatureVector inputs['_vectors'].",
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

        try:
            ead_output = self.ead_policy.apply(inputs)
        except ValueError as exc:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "EAD_POLICY_FAILED",
                    str(exc),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="EAD policy failed.",
            )

        warnings.extend(ead_output.warnings)

        merged_inputs = dict(inputs)
        merged_inputs["ead"] = ead_output.ead

        try:
            policy_output = self.policy_layer.apply(
                inputs=merged_inputs,
                vectors=vectors,
            )
        except IFRS9PolicyError as exc:
            warnings.append(str(exc))

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="IFRS9 policy violation.",
            )
        except ValueError as exc:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "IFRS9_POLICY_INPUT_FAILED",
                    str(exc),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="IFRS9 policy input failed.",
            )

        warnings.extend(policy_output.warnings)

        try:
            math_result = self.math.calculate(
                pd_accounting=policy_output.pd_accounting,
                pd_risk=policy_output.pd_risk,
                lgd=policy_output.lgd,
                ead=ead_output.ead,
                is_stage3=policy_output.credit_impaired,
                lgd_sigma=policy_output.lgd_sigma,
                z_score=self._to_positive_float(inputs.get("z_score", 1.645), "z_score"),
            )
        except ValueError as exc:
            warnings.append(
                make_warning(
                    WarningSeverity.BLOCKING,
                    "IFRS9_MATH_FAILED",
                    str(exc),
                )
            )

            return self._failed_result(
                deal_master_id=deal_master_id,
                inputs=inputs,
                warnings=warnings,
                reason="IFRS9 math failed.",
            )

        warnings.extend(math_result.warnings)

        confidence, confidence_metrics = self.confidence_builder.build(
            vectors=vectors,
            required_inputs=self.REQUIRED_INPUTS,
            policy_output=policy_output,
            warnings=warnings,
            direct_input_mode=direct_input_mode,
        )

        metrics = {
            "calculation_status": "COMPLETED",
            "engine_role": "ifrs9_staged_ecl_proxy",
            "loss_framework": "IFRS9_STAGED_ECL",
            "engine_alias_warning": None,
            "expected_loss_accounting": math_result.expected_loss_accounting,
            "expected_loss_risk": math_result.expected_loss_risk,
            "single_name_ul_proxy": math_result.single_name_ul_proxy,
            "recovery_uncertainty_ul_proxy": math_result.recovery_uncertainty_ul_proxy,
            "expected_loss": math_result.expected_loss_accounting,
            "unexpected_loss": math_result.single_name_ul_proxy,
            "dd_stage_proposed": policy_output.dd_stage_proposed.value,
            "dd_stage_effective": policy_output.dd_stage_effective.value,
            "ifrs9_stage_effective": policy_output.ifrs9_stage_effective.value,
            "sicr_triggers": policy_output.sicr_triggers,
            "credit_impaired_triggers": policy_output.credit_impaired_triggers,
            "credit_impaired": policy_output.credit_impaired,
            "pd_input": policy_output.pd_input,
            "pd_accounting": policy_output.pd_accounting,
            "pd_risk": policy_output.pd_risk,
            "pd_12month": policy_output.pd_12month,
            "lifetime_pd_accounting": policy_output.lifetime_pd_accounting,
            "lifetime_pd_risk": policy_output.lifetime_pd_risk,
            "dynamic_stage3_risk_floor": policy_output.dynamic_stage3_risk_floor,
            "pd_stage": policy_output.pd_stage.value,
            "pd_lineage": policy_output.pd_lineage,
            "lgd": policy_output.lgd,
            "lgd_sigma": policy_output.lgd_sigma,
            "lgd_volatility_method": policy_output.lgd_volatility_method,
            "ead": ead_output.ead,
            "ead_primary": ead_output.ead_primary,
            "ead_alternative": ead_output.ead_alternative,
            "ead_delta": ead_output.ead_delta,
            "ead_delta_ratio": ead_output.ead_delta_ratio,
            "current_balance": ead_output.current_balance,
            "undrawn_commitment": ead_output.undrawn_commitment,
            "ccf": ead_output.ccf,
            "ccf_applied": ead_output.ccf_applied,
            "ead_basis": ead_output.ead_basis.value,
            "ead_source_engine": ead_output.ead_source_engine,
            "remaining_term_years": policy_output.remaining_term_years,
            "lifetime_years": policy_output.lifetime_years,
            "lifetime_pd_method": policy_output.lifetime_pd_method,
            "accounting_el_basis": policy_output.accounting_el_basis,
            "risk_el_basis": policy_output.risk_el_basis,
            "interest_revenue_basis": policy_output.interest_revenue_basis,
            "ul_method": math_result.ul_method.value,
            "z_score": math_result.z_score,
            "manual_override_detected": policy_output.manual_override_detected,
            "approval_required_flags": (
                policy_output.approval_required_flags + ead_output.approval_required_flags
            ),
            "warning_summary": warning_summary(warnings),
            "strict_vector_mode": strict_vector_mode,
            "direct_input_mode": direct_input_mode,
            "non_production_input_mode": direct_input_mode,
            "should_feed_directly_to_deal_gate": not direct_input_mode,
            "house_rule_version": inputs.get(
                "house_rule_version",
                "COSMOS_IFRS9_ECL_PROXY_v0.2",
            ),
            "override_approver": inputs.get("override_approver"),
            **confidence_metrics,
        }

        if direct_input_mode:
            metrics["should_feed_directly_to_deal_gate"] = False

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
                    "IFRS9 staged ECL proxy. This engine separates accounting PD and risk PD. "
                    "Stage 3 accounting PD is hardcoded to 100%, while risk PD preserves model "
                    "differentiation via a dynamic risk floor. Stage 3 UL proxy uses LGD "
                    "volatility rather than PD variance. This is not an external accounting "
                    "opinion and should be used as an internal credit-loss proxy."
                ),
            ),
            warnings=warnings,
        )

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
                        source_detail="direct_ifrs9_ecl_input_without_feature_vector_dev_mode",
                        as_of_date=datetime.now(timezone.utc),
                        confidence_contribution=IFRS9ConfidenceBuilder.DIRECT_INPUT_CONFIDENCE,
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
                "engine_role": "ifrs9_staged_ecl_proxy",
                "loss_framework": "IFRS9_STAGED_ECL",
                "expected_loss_accounting": None,
                "expected_loss_risk": None,
                "single_name_ul_proxy": None,
                "expected_loss": None,
                "unexpected_loss": None,
                "warning_summary": warning_summary(warnings),
                "should_feed_directly_to_deal_gate": False,
                "non_production_input_mode": direct_input_mode,
            },
            confidence=self.confidence_builder.failed_confidence(reason),
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
                notes="IFRS9 ECL proxy calculation failed before valid output.",
            ),
            warnings=warnings,
        )

    def _to_positive_float(self, value: Any, field_name: str) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} cannot be converted to float: {value}") from exc

        if result <= 0:
            raise ValueError(f"{field_name} must be greater than 0.")

        return result
