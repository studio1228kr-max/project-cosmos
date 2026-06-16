"""
COSMOS Failure Diagnostic Engine
Core — asset-class agnostic
딜을 넣으면 어디서 실패하는지 계산한다.
"""
import os, psycopg2, psycopg2.extras, json
from datetime import datetime


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


# ── 5개 차원 진단 함수 ──────────────────────────────────────

def check_evidence(cur, deal_id: int, asset_class: str) -> list[dict]:
    """EVIDENCE 차원: 증거 미비 / 신뢰도 부족"""
    failures = []

    cur.execute("""
        SELECT evidence_type, verification_status, confidence_level, distribution_level
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

    # 미검증 CRITICAL 필드 체크
    critical_fields = {
        "AUDIT_REPORT": "NOI / 재무수치 미검증",
        "LOAN_AGREEMENT": "대출조건 미검증",
    }
    unverified = [e for e in evidences
                  if e["verification_status"] in ("UNVERIFIED",)
                  and e["evidence_type"] in critical_fields]

    for ev in unverified:
        failures.append({
            "dimension": "EVIDENCE",
            "code": f"EVIDENCE_{ev['evidence_type']}_UNVERIFIED",
            "label": f"{ev['evidence_type']} 미검증 — {critical_fields.get(ev['evidence_type'],'')}",
            "severity": "CRITICAL",
            "asset_class": asset_class,
        })

    # 담보가치 미검증 (CRE 전용이지만 Core에서도 collateral 없으면 CRITICAL)
    cur.execute("""
        SELECT collateral_value_base, valuation_confidence
        FROM deal_financials WHERE deal_master_id = %s AND is_current = TRUE LIMIT 1
    """, (deal_id,))
    fin = cur.fetchone()
    if fin and fin["valuation_confidence"] in ("LOW", None):
        failures.append({
            "dimension": "EVIDENCE",
            "code": "EVIDENCE_COLLATERAL_UNVERIFIED",
            "label": "담보가치 미검증 — 감정평가서 또는 실거래 comps 필요",
            "severity": "CRITICAL",
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


def check_structural(cur, deal_id: int, asset_class: str) -> list[dict]:
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

    # 1순위 담보권 관련 증거 없으면
    cur.execute("""
        SELECT verification_status FROM deal_evidence
        WHERE deal_master_id = %s AND evidence_type = 'LOAN_AGREEMENT'
        LIMIT 1
    """, (deal_id,))
    lien_ev = cur.fetchone()
    if not lien_ev or lien_ev["verification_status"] in ("UNVERIFIED", "ESTIMATED"):
        failures.append({
            "dimension": "STRUCTURAL",
            "code": "STRUCTURAL_SENIOR_LIEN_UNCLEAR",
            "label": "신규 1순위 담보권 진입 가능 여부 미확인 — 등기부 및 Payoff 절차 미검증",
            "severity": "CRITICAL",
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

    return failures


# ── 메인 진단 함수 ──────────────────────────────────────────

def run_failure_diagnostic(deal_id: int) -> dict:
    conn = get_conn()
    cur = conn.cursor()

    # 딜 기본 정보
    cur.execute("SELECT * FROM deal_master WHERE id = %s", (deal_id,))
    deal = dict(cur.fetchone())
    asset_class = deal.get("asset_class", "CRE")

    # 5개 차원 진단
    all_failures = []
    all_failures += check_evidence(cur, deal_id, asset_class)
    all_failures += check_financial(cur, deal_id, asset_class)
    all_failures += check_structural(cur, deal_id, asset_class)
    all_failures += check_legal(cur, deal_id, asset_class)
    all_failures += check_market(cur, deal_id, asset_class)

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
    cur.close()
    conn.close()
    return {"analysis_id": analysis_id, "gate": gate, "severity": overall}


if __name__ == "__main__":
    run_failure_diagnostic(deal_id=1)
