from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from quant.structural.structural_warnings import (
    WarningSeverity,
    make_warning,
)


class ULMethod(str, Enum):
    BINOMIAL_SINGLE_NAME_PROXY = "BINOMIAL_SINGLE_NAME_PROXY"
    STAGE3_LGD_VOLATILITY_PROXY = "STAGE3_LGD_VOLATILITY_PROXY"


@dataclass(frozen=True)
class ECLMathResult:
    expected_loss_accounting: float
    expected_loss_risk: float
    single_name_ul_proxy: float
    recovery_uncertainty_ul_proxy: Optional[float]
    ul_method: ULMethod

    pd_accounting_used: float
    pd_risk_used: float
    lgd_used: float
    lgd_sigma_used: Optional[float]
    ead_used: float
    z_score: float

    warnings: List[str]


class IFRS9Math:
    """
    IFRS9-style ECL math layer.

    담당:
    - accounting EL = pd_accounting × LGD × EAD
    - risk EL       = pd_risk × LGD × EAD
    - Stage 1/2 UL proxy = z × LGD × EAD × sqrt(PD × (1-PD))
    - Stage 3 UL proxy   = z × EAD × lgd_sigma

    주의:
    이 UL은 economic capital / portfolio VaR가 아니다.
    single-name diagnostic proxy다.
    """

    DEFAULT_UL_Z_SCORE = 1.645
    MIN_BINOMIAL_VARIANCE_TERM = 0.05

    def calculate(
        self,
        *,
        pd_accounting: float,
        pd_risk: float,
        lgd: float,
        ead: float,
        is_stage3: bool,
        lgd_sigma: Optional[float] = None,
        z_score: float = DEFAULT_UL_Z_SCORE,
    ) -> ECLMathResult:
        warnings: List[str] = []

        self._validate_ratio(pd_accounting, "pd_accounting")
        self._validate_ratio(pd_risk, "pd_risk")
        self._validate_ratio(lgd, "lgd")

        if ead < 0:
            raise ValueError("ead must be greater than or equal to 0.")

        if z_score <= 0:
            raise ValueError("z_score must be greater than 0.")

        expected_loss_accounting = pd_accounting * lgd * ead
        expected_loss_risk = pd_risk * lgd * ead

        recovery_uncertainty_ul_proxy: Optional[float] = None

        if is_stage3:
            if lgd_sigma is None:
                raise ValueError(
                    "lgd_sigma is required for Stage 3 LGD-volatility UL proxy."
                )

            self._validate_ratio(lgd_sigma, "lgd_sigma")

            single_name_ul_proxy = z_score * ead * lgd_sigma
            recovery_uncertainty_ul_proxy = single_name_ul_proxy
            ul_method = ULMethod.STAGE3_LGD_VOLATILITY_PROXY

            warnings.append(
                make_warning(
                    WarningSeverity.CAUTION,
                    "STAGE3_UL_USES_LGD_VOLATILITY",
                    (
                        "Stage 3 UL proxy uses LGD volatility because default uncertainty "
                        "has moved from PD to recovery process uncertainty."
                    ),
                )
            )

        else:
            variance_term = math.sqrt(max(0.0, pd_risk * (1.0 - pd_risk)))

            if variance_term < self.MIN_BINOMIAL_VARIANCE_TERM:
                warnings.append(
                    make_warning(
                        WarningSeverity.CAUTION,
                        "UL_VARIANCE_TERM_FLOORED",
                        (
                            f"Binomial variance term {variance_term:.4f} was floored to "
                            f"{self.MIN_BINOMIAL_VARIANCE_TERM:.4f} to avoid zero-UL "
                            "single-name artifact."
                        ),
                    )
                )
                variance_term = self.MIN_BINOMIAL_VARIANCE_TERM

            single_name_ul_proxy = z_score * lgd * ead * variance_term
            ul_method = ULMethod.BINOMIAL_SINGLE_NAME_PROXY

        if ead == 0:
            warnings.append(
                make_warning(
                    WarningSeverity.MATERIAL,
                    "ZERO_EAD",
                    "EAD is zero. Confirm exposure is truly extinguished.",
                )
            )

        return ECLMathResult(
            expected_loss_accounting=expected_loss_accounting,
            expected_loss_risk=expected_loss_risk,
            single_name_ul_proxy=single_name_ul_proxy,
            recovery_uncertainty_ul_proxy=recovery_uncertainty_ul_proxy,
            ul_method=ul_method,
            pd_accounting_used=pd_accounting,
            pd_risk_used=pd_risk,
            lgd_used=lgd,
            lgd_sigma_used=lgd_sigma,
            ead_used=ead,
            z_score=z_score,
            warnings=warnings,
        )

    def _validate_ratio(self, value: float, name: str) -> None:
        if value < 0.0 or value > 1.0:
            raise ValueError(f"{name} must be a ratio between 0.0 and 1.0.")
