from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from quant.schemas import ConfidenceInfo, ConfidenceTier, SourceType
from quant.structural.structural_policy import StructuralPolicyOutput
from quant.structural.structural_warnings import warning_profile


class StructuralConfidenceBuilder:
    """
    Confidence aggregation layer.

    분리 기준:
    - data_confidence: 입력값 출처/신뢰도
    - model_fit_confidence: 해당 자산/담보/방법론에 이 모델이 맞는지
    - execution_confidence: 파이프라인이 정상적으로 실행됐는지

    최종 confidence는 min-dominant aggregation.
    """

    DIRECT_INPUT_CONFIDENCE = 0.20

    HIGH_FIT_ASSET_CLASSES = {
        "CRE",
        "COMMERCIAL_REAL_ESTATE",
        "REAL_ESTATE_SECURED_CREDIT",
        "SENIOR_SECURED_CRE",
    }

    MEDIUM_FIT_ASSET_CLASSES = {
        "CORPORATE_DIRECT_LENDING",
        "ASSET_BACKED_CREDIT",
        "SPECIAL_SITUATION_SECURED",
    }

    LOW_FIT_ASSET_CLASSES = {
        "HOTEL_DEVELOPMENT_BRIDGE",
        "LAND_BRIDGE",
        "CONSTRUCTION_BRIDGE",
        "OPERATING_COMPANY_UNSECURED",
    }

    def build(
        self,
        *,
        inputs: Dict[str, Any],
        vectors: Optional[Dict[str, Any]],
        required_inputs: Iterable[str],
        policy_output: StructuralPolicyOutput,
        warnings: List[str],
        direct_input_mode: bool,
    ) -> tuple[ConfidenceInfo, Dict[str, float | str]]:
        data_confidence = self._data_confidence(
            vectors=vectors,
            required_inputs=required_inputs,
            direct_input_mode=direct_input_mode,
        )

        model_fit_confidence = self._model_fit_confidence(
            policy_output=policy_output,
            warnings=warnings,
        )

        execution_confidence = self._execution_confidence(warnings=warnings)

        final_score = min(
            data_confidence,
            model_fit_confidence,
            execution_confidence,
        )

        profile = warning_profile(warnings)

        if profile["blocking"] > 0:
            final_score *= 0.30
        elif profile["critical"] > 0:
            final_score *= 0.35
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

        info = ConfidenceInfo(
            tier=tier,
            score=final_score,
            reasoning=(
                "Confidence uses min-dominant aggregation of data_confidence, "
                "model_fit_confidence, and execution_confidence. Direct input mode "
                "is heavily penalized. Warning penalty is severity-weighted."
            ),
        )

        metrics = {
            "data_confidence": data_confidence,
            "model_fit_confidence": model_fit_confidence,
            "execution_confidence": execution_confidence,
            "model_fit_flag": self._model_fit_flag(model_fit_confidence),
        }

        return info, metrics

    def failed_confidence(self, reason: str) -> ConfidenceInfo:
        return ConfidenceInfo(
            tier=ConfidenceTier.LOW,
            score=0.0,
            reasoning=f"Structural distance computation failed: {reason}",
        )

    def _data_confidence(
        self,
        *,
        vectors: Optional[Dict[str, Any]],
        required_inputs: Iterable[str],
        direct_input_mode: bool,
    ) -> float:
        if direct_input_mode or not vectors:
            return self.DIRECT_INPUT_CONFIDENCE

        scores: List[float] = []

        for name in required_inputs:
            vector = vectors.get(name) if vectors else None

            if vector is not None and hasattr(vector, "confidence_score"):
                scores.append(float(vector.confidence_score))
            else:
                scores.append(self.DIRECT_INPUT_CONFIDENCE)

        if not scores:
            return self.DIRECT_INPUT_CONFIDENCE

        weakest = min(scores)
        average = sum(scores) / len(scores)

        score = 0.75 * weakest + 0.25 * average

        sigma_vector = vectors.get("avm_sigma") if vectors else None

        if sigma_vector is not None:
            if getattr(sigma_vector, "source_type", None) == SourceType.MANUAL:
                score *= 0.50

        return max(0.0, min(1.0, score))

    def _model_fit_confidence(
        self,
        *,
        policy_output: StructuralPolicyOutput,
        warnings: List[str],
    ) -> float:
        asset_class = policy_output.asset_class
        collateral_type = policy_output.collateral_type
        sigma_method = policy_output.sigma_method

        if asset_class in self.HIGH_FIT_ASSET_CLASSES:
            score = 0.80
        elif asset_class in self.MEDIUM_FIT_ASSET_CLASSES:
            score = 0.60
        elif asset_class in self.LOW_FIT_ASSET_CLASSES:
            score = 0.35
        else:
            score = 0.50

        if "LAND" in collateral_type or "DEVELOPMENT" in collateral_type:
            score *= 0.65

        if sigma_method == "market_comp_dispersion":
            score *= 1.00
        elif sigma_method == "appraisal_band_proxy":
            score *= 0.90
        elif sigma_method == "cap_rate_noi_stress":
            score *= 0.85
        elif sigma_method == "house_assumption":
            score *= 0.70

        profile = warning_profile(warnings)

        if profile["critical"] > 0:
            score *= 0.50
        elif profile["material"] > 0:
            score *= 0.75

        return max(0.0, min(1.0, score))

    def _execution_confidence(self, *, warnings: List[str]) -> float:
        profile = warning_profile(warnings)

        if profile["blocking"] > 0:
            return 0.30

        return 0.95

    def _model_fit_flag(self, model_fit_confidence: float) -> str:
        if model_fit_confidence >= 0.70:
            return "HIGH_FIT"
        if model_fit_confidence >= 0.45:
            return "MEDIUM_FIT"
        return "LOW_FIT"
