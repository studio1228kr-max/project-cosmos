from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from quant.credit_loss.ifrs9_policy import IFRS9PolicyOutput
from quant.schemas import ConfidenceInfo, ConfidenceTier, SourceType
from quant.structural.structural_warnings import warning_profile


class IFRS9ConfidenceBuilder:
    DIRECT_INPUT_CONFIDENCE = 0.20

    def build(
        self,
        *,
        vectors: Optional[Dict[str, Any]],
        required_inputs: Iterable[str],
        policy_output: IFRS9PolicyOutput,
        warnings: List[str],
        direct_input_mode: bool,
    ) -> tuple[ConfidenceInfo, Dict[str, float | str]]:
        data_confidence = self._data_confidence(
            vectors=vectors,
            required_inputs=required_inputs,
            direct_input_mode=direct_input_mode,
        )

        stage_confidence = self._stage_semantics_confidence(policy_output)
        model_fit_confidence = self._model_fit_confidence(policy_output, vectors)
        execution_confidence = self._execution_confidence(warnings)

        final_score = min(
            data_confidence,
            stage_confidence,
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
                "IFRS9 ECL confidence uses min-dominant aggregation of data, "
                "stage semantics, model fit, and execution confidence. Stage manipulation, "
                "raw PD use, manual LGD sigma, and direct input mode are penalized."
            ),
        )

        metrics = {
            "data_confidence": data_confidence,
            "stage_semantics_confidence": stage_confidence,
            "model_fit_confidence": model_fit_confidence,
            "execution_confidence": execution_confidence,
            "model_fit_flag": self._fit_flag(model_fit_confidence),
        }

        return confidence, metrics

    def failed_confidence(self, reason: str) -> ConfidenceInfo:
        return ConfidenceInfo(
            tier=ConfidenceTier.LOW,
            score=0.0,
            reasoning=f"IFRS9 ECL computation failed: {reason}",
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
            vector = vectors.get(name)

            if vector is not None and hasattr(vector, "confidence_score"):
                scores.append(float(vector.confidence_score))
            else:
                scores.append(self.DIRECT_INPUT_CONFIDENCE)

        if not scores:
            return self.DIRECT_INPUT_CONFIDENCE

        weakest = min(scores)
        average = sum(scores) / len(scores)

        return max(0.0, min(1.0, 0.75 * weakest + 0.25 * average))

    def _stage_semantics_confidence(self, policy_output: IFRS9PolicyOutput) -> float:
        score = 0.85

        if policy_output.sicr_triggers or policy_output.credit_impaired_triggers:
            score *= 0.95

        if policy_output.dd_stage_effective != policy_output.dd_stage_proposed:
            score *= 0.70

        if policy_output.lifetime_pd_method == "FLAT_CUMULATIVE_APPROXIMATION":
            score *= 0.75

        return max(0.0, min(1.0, score))

    def _model_fit_confidence(
        self,
        policy_output: IFRS9PolicyOutput,
        vectors: Optional[Dict[str, Any]],
    ) -> float:
        score = 0.85

        if policy_output.pd_stage.value == "RAW":
            score *= 0.60
        elif policy_output.pd_stage.value == "CALIBRATED":
            score *= 0.85
        elif policy_output.pd_stage.value == "FINAL":
            score *= 1.00

        if policy_output.lgd_volatility_method == "RECOVERY_ENGINE_DERIVED":
            score *= 1.00
        elif policy_output.lgd_volatility_method == "HOUSE_RULE_ASSET_CLASS":
            score *= 0.80
        elif policy_output.lgd_volatility_method == "MANUAL":
            score *= 0.50
        elif policy_output.dd_stage_effective.value == "FULL":
            score *= 0.50

        if vectors:
            pd_vector = vectors.get("pd")
            if pd_vector is not None and getattr(pd_vector, "source_type", None) == SourceType.MANUAL:
                score *= 0.50

            lgd_vector = vectors.get("lgd")
            if lgd_vector is not None and getattr(lgd_vector, "source_type", None) == SourceType.MANUAL:
                score *= 0.75

        return max(0.0, min(1.0, score))

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
