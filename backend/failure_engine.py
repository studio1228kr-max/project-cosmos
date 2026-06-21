"""
COSMOS Failure Diagnostic Engine
Core — asset-class agnostic
딜을 넣으면 어디서 실패하는지 계산한다.
"""
import os, psycopg2, psycopg2.extras, json
from datetime import datetime
from core.quant_client import evaluate_deal, QuantClientError
from core.quant_inputs import assemble_merton_inputs, assemble_cecl_inputs, assemble_cox_hazard_inputs

# ── 정량엔진(Merton/KMV + CECL) House 임계값 ──────────────────
# House 가정(avm_sigma, LGD) 의존 — avm_engine/recovery_strategy_engine_kr
# 완성되면 이 임계값들의 입력 신뢰도가 올라간다. 임계값 자체는 House Canon 기준.
PD_CRITICAL_THRESHOLD = 0.50
PD_MODERATE_THRESHOLD = 0.15
EL_RATIO_CRITICAL_THRESHOLD = 0.10
EL_RATIO_MODERATE_THRESHOLD = 0.03


def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL", "postgresql://kimminwoo@localhost/cosmos"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )


# ── Gate 도출 규칙 ──────────────────────────────────────────
# CRITICAL 하나라도 있으면 → HOLD
# CRITICAL 없고 MODERATE 있으면 → RESTRUCTURE
# 둘 다 없으면 → ADVANCE
# ────────────────────────────────────────────────────────────

def derive_gate(critical: int, moderate: int) -> tuple[str, str]:
    """(final_gate, provisional_gate) 반환"""
    if critical > 0:
        provisional = "RESTRUCTURE" if moderate > 0 or critical > 0 else "ADVANCE"
        return "HOLD", provisional
    if moderate > 0:
        return "RESTRUCTURE", None
    return "ADVANCE", None


def derive_overall_severity(critical: int, moderate: int) -> str:
    if critical > 0:
        return "CRITICAL"
    if moderate > 0:
        return "MODERATE"
    return "CLEAR"


# ── Stage-aware evidence 평가 ────────────────────────────────
# PRE 단계 딜에 Full-DD급 증빙을 CRITICAL로 요구하지 않기 위한 게이트.
# required_stage / status 는 deal_evidence 테이블 컬럼에서 직접 읽는다 (DB가 정답, 코드에 하드코딩 안 함).
STAGE_RANK = {"PRE": 0, "SOFT": 1, "FULL": 2}


def stage_satisfied(deal_stage: str, required_stage: str) -> bool:
    """딜이 아직 그 단계에 도달하지 않았으면 해당 항목은 평가 대상에서 제외한다."""
    return STAGE_RANK.get(deal_stage, 0) >= STAGE_RANK.get(required_stage, 0)


def evidence_status_severity(status: str, required_stage: str, deal_stage: str):
    """
    이 항목이 deal_stage 기준 아직 필요한 단계가 아니면 None(평가 안 함).
    필요한 단계가 됐으면 status로 심각도 결정:
      verified      -> None (문제 없음)
      approx        -> MODERATE (역추론 엔진이 추정 완료, 리스크는 줄었으나 검증 전)
      not_attempted -> CRITICAL
    """
    if not stage_satisfied(deal_stage, required_stage):
        return None
    if status == "verified":
        return None
    if status == "approx":
        return "MODERATE"
    return "CRITICAL"


# ── 5개 차원 진단 함수 ──────────────────────────────────────

def check_evidence(cur, deal_id: int, asset_class: str, deal_stage: str = "PRE") -> list[dict]:
    """EVIDENCE 차원: 증거 미비 / 신뢰도 부족"""
    failures = []

    cur.execute("""
        SELECT evidence_type, verification_status, confidence_level, distribution_level,
               required_stage, status
        FROM deal_evidence WHERE deal_master_id = %s
    """, (deal_id,))
    evidences = cur.fetchall()

    if not evidences:
        failures.append({
            "dimension": "EVIDENCE",
            "code": "EVIDENCE_NO_ITEMS",
            "label": "증거 항목 없음 — 최소 증거 세트 미구성",
            "severity": "CRITICAL",
            "asset_class": None,
        })
        return failures

    # 라벨용 — 알려진 evidence_type은 구체적 설명, 그 외는 일반 라벨 (화이트리스트로 평가 자체를 막지 않음)
    known_labels = {
        "AUDIT_REPORT": "NOI / 재무수치 미검증",
        "LOAN_AGREEMENT": "대출조건 미검증",
    }

    for ev in evidences:
        sev = evidence_status_severity(
            status=ev.get("status", "not_attempted"),
            required_stage=ev.get("required_stage", "PRE"),
            deal_stage=deal_stage,
        )
        if sev is None:
            continue

        label_detail = known_labels.get(ev["evidence_type"], "증빙 미비")
        failures.append({
            "dimension": "EVIDENCE",
            "code": f"EVIDENCE_{ev['evidence_type']}_{ev.get('status','not_attempted').upper()}",
            "label": f"{ev['evidence_type']} {ev.get('status','not_attempted')} 상태 — {label_detail}",
            "severity": sev,
            "asset_class": asset_class,
        })

    # 담보가치 — Pre/Soft 단계는 AVM approx로 충분, FULL 단계부터 감정평가급 요구
    cur.execute("""
        SELECT collateral_value_base, valuation_confidence
        FROM deal_financials WHERE deal_master_id = %s AND is_current = TRUE LIMIT 1
    """, (deal_id,))
    fin = cur.fetchone()
    if fin and fin["valuation_confidence"] in ("LOW", None):
        if stage_satisfied(deal_stage, "FULL"):
            failures.append({
                "dimension": "EVIDENCE",
                "code": "EVIDENCE_COLLATERAL_UNVERIFIED",
                "label": "담보가치 미검증 — 감정평가서 또는 실거래 comps 필요",
                "severity": "CRITICAL",
                "asset_class": asset_class,
                "metric_name": "valuation_confidence",
                "metric_value": None,
            })
        else:
            failures.append({
                "dimension": "EVIDENCE",
                "code": "EVIDENCE_COLLATERAL_APPROX_ONLY",
                "label": "담보가치 Approx 단계 — AVM 추정치, Full-DD 시 감정평가로 검증 필요",
                "severity": "DEFERRED",
                "asset_class": asset_class,
                "metric_name": "valuation_confidence",
                "metric_value": None,
            })

    # evidence completeness PARTIAL/INSUFFICIENT
    if fin and fin.get("data_gate_status") in ("INSUFFICIENT",):
        failures.append({
            "dimension": "EVIDENCE",
            "code": "EVIDENCE_COMPLETENESS_INSUFFICIENT",
            "label": "증거 완성도 INSUFFICIENT — Gate 판단 불가",
            "severity": "CRITICAL",
            "asset_class": None,
        })
    elif fin and fin.get("data_gate_status") in ("PARTIAL",):
        failures.append({
            "dimension": "EVIDENCE",
            "code": "EVIDENCE_COMPLETENESS_PARTIAL",
            "label": "증거 완성도 PARTIAL — 핵심 항목 미완성",
            "severity": "MODERATE",
            "asset_class": None,
        })

    return failures


def check_financial(cur, deal_id: int, asset_class: str) -> list[dict]:
    """FINANCIAL 차원: 수치 기준 미달"""
    failures = []

    cur.execute("""
        SELECT df.*, gp.min_dscr_advance, gp.min_dscr_hold,
               gp.max_ltv_advance, gp.max_ltv_restructure, gp.min_debt_yield
        FROM deal_financials df
        CROSS JOIN gate_policy gp
        WHERE df.deal_master_id = %s AND df.is_current = TRUE
          AND gp.asset_class = %s AND gp.is_current = TRUE
        LIMIT 1
    """, (deal_id, asset_class))
    row = cur.fetchone()

    if not row:
        # gate_policy 없으면 CORE 기본값으로
        cur.execute("""
            SELECT * FROM deal_financials
            WHERE deal_master_id = %s AND is_current = TRUE LIMIT 1
        """, (deal_id,))
        row = cur.fetchone()
        if not row:
            return failures
        # 기본 임계값
        row = dict(row)
        row.update({"min_dscr_advance": 1.20, "min_dscr_hold": 1.00,
                    "max_ltv_advance": 0.60, "max_ltv_restructure": 0.65,
                    "min_debt_yield": 0.10})

    row = dict(row)

    # DSCR 체크
    if row.get("dscr") is not None:
        dscr = float(row["dscr"])
        if dscr < float(row["min_dscr_hold"]):
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_DSCR_BELOW_HOLD",
                "label": f"Base DSCR {dscr:.2f}x — Hold 기준 {row['min_dscr_hold']}x 미달",
                "severity": "CRITICAL",
                "metric_name": "dscr",
                "metric_value": dscr,
                "threshold_value": float(row["min_dscr_hold"]),
                "breach_amount": float(row["min_dscr_hold"]) - dscr,
                "asset_class": asset_class,
            })
        elif dscr < float(row["min_dscr_advance"]):
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_DSCR_BELOW_ADVANCE",
                "label": f"Base DSCR {dscr:.2f}x — Advance 기준 {row['min_dscr_advance']}x 미달",
                "severity": "MODERATE",
                "metric_name": "dscr",
                "metric_value": dscr,
                "threshold_value": float(row["min_dscr_advance"]),
                "breach_amount": float(row["min_dscr_advance"]) - dscr,
                "asset_class": asset_class,
            })

    # LTV 체크
    if row.get("ltv_net") is not None:
        ltv = float(row["ltv_net"])
        if ltv > float(row["max_ltv_restructure"]):
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_LTV_ABOVE_RESTRUCTURE",
                "label": f"LTV Net {ltv*100:.1f}% — Restructure 임계 {row['max_ltv_restructure']*100:.0f}% 초과",
                "severity": "CRITICAL",
                "metric_name": "ltv_net",
                "metric_value": ltv,
                "threshold_value": float(row["max_ltv_restructure"]),
                "breach_amount": ltv - float(row["max_ltv_restructure"]),
                "asset_class": asset_class,
            })
        elif ltv > float(row["max_ltv_advance"]):
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_LTV_ABOVE_ADVANCE",
                "label": f"LTV Net {ltv*100:.1f}% — Advance 임계 {row['max_ltv_advance']*100:.0f}% 초과",
                "severity": "MODERATE",
                "metric_name": "ltv_net",
                "metric_value": ltv,
                "threshold_value": float(row["max_ltv_advance"]),
                "breach_amount": ltv - float(row["max_ltv_advance"]),
                "asset_class": asset_class,
            })

    # Downside 시나리오 체크 (COMBINED — 가장 중요)
    cur.execute("""
        SELECT scenario_id, stressed_dscr, stressed_ltv_gross, scenario_gate, breach_vector
        FROM risk_scenarios
        WHERE deal_master_id = %s AND scenario_id = 'COMBINED'
        LIMIT 1
    """, (deal_id,))
    combined = cur.fetchone()
    if combined and combined["stressed_dscr"] is not None:
        sdscr = float(combined["stressed_dscr"])
        if sdscr < 1.0:
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_COMBINED_DSCR_BREACH",
                "label": f"Combined Downside DSCR {sdscr:.2f}x — 1.0x 미달. 구조보강 필요",
                "severity": "MODERATE",
                "metric_name": "combined_dscr",
                "metric_value": sdscr,
                "threshold_value": 1.0,
                "breach_amount": 1.0 - sdscr,
                "asset_class": asset_class,
            })

    return failures


def check_structural(cur, deal_id: int, asset_class: str, deal_stage: str = "PRE") -> list[dict]:
    """STRUCTURAL 차원: 거래 구조 닫히지 않음"""
    failures = []

    cur.execute("""
        SELECT current_lender, proposed_lender
        FROM deal_master WHERE id = %s
    """, (deal_id,))
    dm = cur.fetchone()

    # 신규 대주 미정
    if not dm or not dm["proposed_lender"]:
        failures.append({
            "dimension": "STRUCTURAL",
            "code": "STRUCTURAL_NO_TAKEOUT_LENDER",
            "label": "신규 대주 미정 — Takeout Lender 확보 필요",
            "severity": "CRITICAL",
            "asset_class": None,
        })

    # 1순위 담보권 관련 증거
    cur.execute("""
        SELECT verification_status, required_stage, status FROM deal_evidence
        WHERE deal_master_id = %s AND evidence_type = 'LOAN_AGREEMENT'
        LIMIT 1
    """, (deal_id,))
    lien_ev = cur.fetchone()

    if not lien_ev:
        sev = evidence_status_severity("not_attempted", "SOFT", deal_stage)
    else:
        sev = evidence_status_severity(
            lien_ev.get("status", "not_attempted"),
            lien_ev.get("required_stage", "SOFT"),
            deal_stage,
        )

    if sev is not None:
        failures.append({
            "dimension": "STRUCTURAL",
            "code": "STRUCTURAL_SENIOR_LIEN_UNCLEAR",
            "label": "신규 1순위 담보권 진입 가능 여부 미확인 — 등기부 및 Payoff 절차 미검증",
            "severity": sev,
            "asset_class": asset_class,
        })
    elif lien_ev is None or lien_ev.get("status") != "verified":
        failures.append({
            "dimension": "STRUCTURAL",
            "code": "STRUCTURAL_SENIOR_LIEN_PENDING_SOFT_DD",
            "label": "1순위 담보권 확인은 Soft-DD(LOI/NDA) 단계 이후 진행 예정",
            "severity": "DEFERRED",
            "asset_class": asset_class,
        })

    # NTS 압류 해소 여부
    cur.execute("""
        SELECT nts_seizure_amount FROM deal_financials
        WHERE deal_master_id = %s AND is_current = TRUE LIMIT 1
    """, (deal_id,))
    fin = cur.fetchone()
    if fin and fin["nts_seizure_amount"] and float(fin["nts_seizure_amount"]) > 0:
        cur.execute("""
            SELECT verification_status FROM deal_evidence
            WHERE deal_master_id = %s AND evidence_type = 'NTS_SEIZURE'
            LIMIT 1
        """, (deal_id,))
        nts_ev = cur.fetchone()
        if not nts_ev or nts_ev["verification_status"] in ("UNVERIFIED", "ESTIMATED"):
            failures.append({
                "dimension": "STRUCTURAL",
                "code": "STRUCTURAL_NTS_PAYOFF_UNKNOWN",
                "label": f"NTS 압류 해소 메커니즘 미확인 — 선순위 부담 {float(fin['nts_seizure_amount']):.2f}억",
                "severity": "MODERATE",
                "metric_name": "nts_seizure_amount",
                "metric_value": float(fin["nts_seizure_amount"]),
                "asset_class": asset_class,
            })

    return failures


def check_legal(cur, deal_id: int, asset_class: str) -> list[dict]:
    """LEGAL 차원: 역할/권리/절차 미정리 — 지금은 DEFERRED로"""
    failures = []
    failures.append({
        "dimension": "LEGAL",
        "code": "LEGAL_ROLE_BOUNDARY_DEFERRED",
        "label": "역할 경계 및 접촉 프로토콜 미정리 — K&C 검토 대기",
        "severity": "DEFERRED",
        "asset_class": None,
    })
    return failures


def check_market(cur, deal_id: int, asset_class: str) -> list[dict]:
    """MARKET 차원: Tail 시나리오 경고"""
    failures = []

    cur.execute("""
        SELECT rs.scenario_id, rs.scenario_gate, rs.gate_weight
        FROM risk_scenarios rs
        WHERE rs.deal_master_id = %s
          AND rs.gate_weight = 'INFORMATIONAL'
          AND rs.scenario_gate IN ('REJECT','RESTRUCTURE')
    """, (deal_id,))
    tails = cur.fetchall()

    for t in tails:
        failures.append({
            "dimension": "MARKET",
            "code": f"MARKET_TAIL_{t['scenario_id']}",
            "label": f"Tail Scenario {t['scenario_id']} → {t['scenario_gate']} (정보성 경고)",
            "severity": "DEFERRED",
            "asset_class": asset_class,
        })

    # MOLIT 실거래가 기반 담보 현재가 추정 + LTV 재계산
    try:
        cur.execute("SAVEPOINT molit_check")
        cur.execute("""
            SELECT dc.bjdong_cd, dc.area_sqm, df.loan_amount, df.collateral_value_base
            FROM deal_collateral dc
            JOIN deal_financials df ON df.deal_master_id = dc.deal_master_id AND df.is_current = TRUE
            WHERE dc.deal_master_id = %s
            LIMIT 1
        """, (deal_id,))
        col = cur.fetchone()
        if col and col["bjdong_cd"]:
            cur.execute("""
                SELECT AVG(price_per_sqm) AS avg_price, COUNT(*) AS trade_count,
                       MAX(deal_date) AS latest_trade
                FROM molit_trade_normalized
                WHERE lawd_cd = LEFT(%s, 5)
                  AND deal_date >= CURRENT_DATE - INTERVAL '3 months'
                  AND building_use NOT IN ('주거')
                  AND price_per_sqm IS NOT NULL
            """, (col["bjdong_cd"],))
            mkt = cur.fetchone()
            if mkt and mkt["avg_price"] and col["area_sqm"]:
                molit_value_man = int(float(mkt["avg_price"]) * float(col["area_sqm"]) / 10000)
                molit_value_eok = round(molit_value_man / 10000, 1)
                loan_amount = float(col["loan_amount"]) if col["loan_amount"] else 0
                molit_ltv = round(loan_amount / molit_value_eok, 4) if molit_value_eok > 0 else None
                base_value = float(col["collateral_value_base"]) if col["collateral_value_base"] else None
                price_change = round((molit_value_man - base_value) / base_value, 4) if base_value else None

                # collateral_risk_flag
                if molit_ltv is not None:
                    if molit_ltv > 0.75:
                        flag, sev = "WEAKENING", "CRITICAL"
                    elif molit_ltv > 0.65:
                        flag, sev = "WATCH", "MODERATE"
                    else:
                        flag, sev = "STABLE", "DEFERRED"
                else:
                    flag, sev = "UNKNOWN", "DEFERRED"

                failures.append({
                    "dimension": "MARKET",
                    "code": f"MARKET_COLLATERAL_MOLIT_{flag}",
                    "label": f"MOLIT 실거래 기반 담보가 {molit_value_eok}억 추정 | LTV {molit_ltv*100:.1f}% | {flag}",
                    "severity": sev,
                    "asset_class": asset_class,
                    "metric_name": "molit_ltv",
                    "metric_value": molit_ltv,
                    "threshold_value": 0.65,
                    "breach_amount": round(molit_ltv - 0.65, 4) if molit_ltv else None,
                    "description": f"실거래 {mkt['trade_count']}건 평균단가 기준 | 최근거래 {mkt['latest_trade']} | 가격변동 {price_change*100:+.1f}%" if price_change is not None else f"실거래 {mkt['trade_count']}건 평균단가 기준 | 최근거래 {mkt['latest_trade']}",
                })
        cur.execute("RELEASE SAVEPOINT molit_check")
    except Exception as e:
        cur.execute("ROLLBACK TO SAVEPOINT molit_check")

    return failures


def check_quant(cur, deal_id: int, asset_class: str, deal_stage: str, deal_master: dict) -> list[dict]:
    """
    정량엔진 차원(FINANCIAL에 합산): merton_kmv(PD) → cecl_engine(EL/Stage) 체이닝.
    House 가정(avm_sigma, LGD) 기반이므로 라벨에 명시 — avm_engine,
    recovery_strategy_engine_kr 완성되면 이 가정을 실측값으로 교체한다.
    """
    failures = []

    cur.execute("""
        SELECT * FROM deal_financials
        WHERE deal_master_id = %s AND is_current = TRUE LIMIT 1
    """, (deal_id,))
    fin = cur.fetchone()
    if not fin:
        return failures
    fin = dict(fin)

    merton_inputs = assemble_merton_inputs(deal_master, fin)
    if merton_inputs is None:
        failures.append({
            "dimension": "FINANCIAL",
            "code": "FINANCIAL_QUANT_INPUT_INSUFFICIENT",
            "label": "정량엔진(Merton/KMV) 입력 부족 — 담보가치/부채잔액/만기일 중 누락",
            "severity": "DEFERRED",
            "asset_class": asset_class,
        })
        return failures

    try:
        merton_result = evaluate_deal("merton_kmv", deal_id, merton_inputs)
    except QuantClientError as e:
        failures.append({
            "dimension": "FINANCIAL",
            "code": "FINANCIAL_QUANT_MERTON_FAILED",
            "label": f"Merton/KMV 계산 실패 — {e}",
            "severity": "DEFERRED",
            "asset_class": asset_class,
        })
        return failures

    merton_metrics = merton_result.get("metrics", {})
    pd_value = merton_metrics.get("pd_structural_raw")

    if pd_value is not None:
        if pd_value >= PD_CRITICAL_THRESHOLD:
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_QUANT_PD_CRITICAL",
                "label": f"Merton/KMV 구조적 부도확률 {pd_value*100:.1f}% — Critical 기준 {PD_CRITICAL_THRESHOLD*100:.0f}% 초과 (House 가정 sigma 적용)",
                "severity": "CRITICAL",
                "metric_name": "pd_structural_raw",
                "metric_value": pd_value,
                "threshold_value": PD_CRITICAL_THRESHOLD,
                "breach_amount": pd_value - PD_CRITICAL_THRESHOLD,
                "asset_class": asset_class,
            })
        elif pd_value >= PD_MODERATE_THRESHOLD:
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_QUANT_PD_MODERATE",
                "label": f"Merton/KMV 구조적 부도확률 {pd_value*100:.1f}% — Moderate 기준 {PD_MODERATE_THRESHOLD*100:.0f}% 초과 (House 가정 sigma 적용)",
                "severity": "MODERATE",
                "metric_name": "pd_structural_raw",
                "metric_value": pd_value,
                "threshold_value": PD_MODERATE_THRESHOLD,
                "breach_amount": pd_value - PD_MODERATE_THRESHOLD,
                "asset_class": asset_class,
            })

    # cox_hazard — merton PD → lifetime PD (flat approximation 해소)
    cox_hazard_lifetime_pd = None
    cox_inputs = assemble_cox_hazard_inputs(deal_master, fin, merton_result)
    if cox_inputs is not None:
        try:
            cox_result = evaluate_deal("cox_hazard_engine", deal_id, cox_inputs)
            cox_hazard_lifetime_pd = cox_result.get("metrics", {}).get("lifetime_pd_hazard")
        except QuantClientError:
            cox_hazard_lifetime_pd = None  # cox 실패해도 cecl은 계속

    cecl_inputs = assemble_cecl_inputs(deal_master, fin, merton_result)
    if cecl_inputs is not None and cox_hazard_lifetime_pd is not None:
        cecl_inputs["hazard_lifetime_pd"] = cox_hazard_lifetime_pd

    if cecl_inputs is None:
        return failures

    try:
        cecl_result = evaluate_deal("cecl_engine", deal_id, cecl_inputs)
    except QuantClientError as e:
        failures.append({
            "dimension": "FINANCIAL",
            "code": "FINANCIAL_QUANT_CECL_FAILED",
            "label": f"CECL/IFRS9 ECL 계산 실패 — {e}",
            "severity": "DEFERRED",
            "asset_class": asset_class,
        })
        return failures

    cecl_metrics = cecl_result.get("metrics", {})
    expected_loss = cecl_metrics.get("expected_loss")
    ifrs9_stage = cecl_metrics.get("ifrs9_stage_effective")
    current_balance = cecl_inputs.get("current_balance") or 0

    if expected_loss is not None and current_balance:
        el_ratio = expected_loss / current_balance
        if el_ratio >= EL_RATIO_CRITICAL_THRESHOLD:
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_QUANT_EL_CRITICAL",
                "label": f"예상손실(EL) {expected_loss:,.0f}원 — 대출잔액 대비 {el_ratio*100:.1f}%, Critical 기준 {EL_RATIO_CRITICAL_THRESHOLD*100:.0f}% 초과 (House 가정 LGD 적용)",
                "severity": "CRITICAL",
                "metric_name": "expected_loss_ratio",
                "metric_value": el_ratio,
                "threshold_value": EL_RATIO_CRITICAL_THRESHOLD,
                "breach_amount": el_ratio - EL_RATIO_CRITICAL_THRESHOLD,
                "asset_class": asset_class,
            })
        elif el_ratio >= EL_RATIO_MODERATE_THRESHOLD:
            failures.append({
                "dimension": "FINANCIAL",
                "code": "FINANCIAL_QUANT_EL_MODERATE",
                "label": f"예상손실(EL) {expected_loss:,.0f}원 — 대출잔액 대비 {el_ratio*100:.1f}%, Moderate 기준 {EL_RATIO_MODERATE_THRESHOLD*100:.0f}% 초과 (House 가정 LGD 적용)",
                "severity": "MODERATE",
                "metric_name": "expected_loss_ratio",
                "metric_value": el_ratio,
                "threshold_value": EL_RATIO_MODERATE_THRESHOLD,
                "breach_amount": el_ratio - EL_RATIO_MODERATE_THRESHOLD,
                "asset_class": asset_class,
            })

    if ifrs9_stage == "STAGE_3":
        failures.append({
            "dimension": "FINANCIAL",
            "code": "FINANCIAL_QUANT_IFRS9_STAGE3",
            "label": "IFRS9 Stage 3(Credit-Impaired) 진입 — 회계상 부도 상태로 분류됨",
            "severity": "CRITICAL",
            "metric_name": "ifrs9_stage_effective",
            "metric_value": None,
            "asset_class": asset_class,
        })

    return failures


# ── 메인 진단 함수 ──────────────────────────────────────────

def run_failure_diagnostic(deal_id: int) -> dict:
    conn = get_conn()
    conn.rollback()  # 이전 abort 트랜잭션 클린업
    cur = conn.cursor()

    try:
        # 딜 기본 정보
        cur.execute("SELECT * FROM deal_master WHERE id = %s", (deal_id,))
        deal = dict(cur.fetchone())
        asset_class = deal.get("asset_class", "CRE")
        deal_stage = deal.get("dd_stage", "PRE")

        # 5개 차원 진단
        all_failures = []
        all_failures += check_evidence(cur, deal_id, asset_class, deal_stage)
        all_failures += check_financial(cur, deal_id, asset_class)
        all_failures += check_structural(cur, deal_id, asset_class, deal_stage)
        all_failures += check_legal(cur, deal_id, asset_class)
        all_failures += check_market(cur, deal_id, asset_class)
        all_failures += check_quant(cur, deal_id, asset_class, deal_stage, deal)

        # 집계
        critical = sum(1 for f in all_failures if f["severity"] == "CRITICAL")
        moderate = sum(1 for f in all_failures if f["severity"] == "MODERATE")
        deferred = sum(1 for f in all_failures if f["severity"] == "DEFERRED")

        overall = derive_overall_severity(critical, moderate)
        gate, provisional = derive_gate(critical, moderate)

        # failure_analysis 저장
        cur.execute("""
            INSERT INTO failure_analysis
                (deal_master_id, asset_class, module_code, overall_severity,
                 gate_derived, provisional_gate, critical_count, moderate_count,
                 deferred_count, total_failures, policy_version)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (deal_id, asset_class, deal.get("module_code","CRE_SECURED_CREDIT"),
              overall, gate, provisional, critical, moderate, deferred,
              len(all_failures), "LUSKA_GATE_V0_1"))
        analysis_id = cur.fetchone()["id"]

        # failure_items 저장
        for f in all_failures:
            cur.execute("""
                INSERT INTO failure_items
                    (failure_analysis_id, deal_master_id, failure_dimension,
                     failure_code, failure_label, severity, description,
                     metric_name, metric_value, threshold_value, breach_amount, asset_class)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (analysis_id, deal_id,
                  f["dimension"], f["code"], f["label"], f["severity"],
                  f.get("description"), f.get("metric_name"),
                  f.get("metric_value"), f.get("threshold_value"),
                  f.get("breach_amount"), f.get("asset_class")))

        conn.commit()

        # 결과 출력
        print(f"\n{'='*60}")
        print(f"COSMOS Failure Diagnostic — Deal {deal['deal_code']}")
        print(f"{'='*60}")
        print(f"  Asset Class:      {asset_class}")
        print(f"  Overall Severity: {overall}")
        print(f"  Gate Derived:     {gate}")
        if provisional:
            print(f"  Provisional:      {provisional}")
        print(f"  Failures: CRITICAL={critical} MODERATE={moderate} DEFERRED={deferred}")

        dims = ["EVIDENCE","FINANCIAL","STRUCTURAL","LEGAL","MARKET"]
        for dim in dims:
            dim_failures = [f for f in all_failures if f["dimension"] == dim]
            if dim_failures:
                print(f"\n  [{dim}]")
                for f in dim_failures:
                    icon = "🔴" if f["severity"]=="CRITICAL" else "🟡" if f["severity"]=="MODERATE" else "⚪"
                    print(f"    {icon} [{f['severity']}] {f['label']}")

        print(f"\n  analysis_id: {analysis_id}")
        return {"analysis_id": analysis_id, "gate": gate, "severity": overall}

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_failure_diagnostic(deal_id=1)
