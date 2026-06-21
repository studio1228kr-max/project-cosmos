from __future__ import annotations

from typing import Any, Dict

from quant.credit_loss.ifrs9_ecl_engine import IFRS9ECLEngine


class CECLEngine(IFRS9ECLEngine):
    """
    Backward-compatible registry wrapper.

    기존 registry/API 호환을 위해 cecl_engine 이름은 유지한다.
    실제 구현은 IFRS9ECLEngine이다.
    """

    engine_name = "cecl_engine"
    model_version = "v0.2-wrapper"

    def compute(self, deal_master_id: int, inputs: Dict[str, Any]):
        result = super().compute(deal_master_id=deal_master_id, inputs=inputs)

        result.metrics["actual_engine"] = "ifrs9_ecl_engine"
        result.metrics["engine_alias_warning"] = (
            "ENGINE_NAME_CECL_BUT_POLICY_IFRS9"
        )

        return result
