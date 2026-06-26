"""1회성 백필 — signal_room 기존 엔티티 재무 백필 + 재스코어.

dedupe-skip 때문에 워커가 소급 처리 못 하는 기존 signal_room 신호에 대해:
  corp_code → DART 재무 fetch → entity_financial_features 저장(엔티티당 current 1기)
  → financial_engine.detect_signals → signal_engine 재스코어(재무신호 포함)
  → signal_room 카드(점수/딜타입/urgency/thesis/reason) 갱신.

엔티티당 feats[0](최신기)만 저장 → period_end 충돌(미해결 #2) 회피.
실행: python backfill_financial.py
"""
from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, ".")

import db
from engines.financial_engine import FinancialEngine
from engines.signal_engine import SignalEngine
from fetchers.dart_financial_fetcher import DartFinancialFetcher


async def rescore(se: SignalEngine, row: dict, fin_signals: list) -> dict:
    signal = {
        "signal_type": row.get("signal_type"),
        "suggested_deal_type": row.get("suggested_deal_type"),
        "financial_signals": fin_signals,
        "cb_signals": [],
    }
    scores = await se.score_all(signal)
    return await se.aggregate(scores)


async def main() -> None:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, entity_name, entity_id, signal_type, suggested_deal_type,
                  aggregate_score, thesis_suggestion, urgency
           FROM signal_room ORDER BY id"""
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()

    fetcher = DartFinancialFetcher()
    fe = FinancialEngine()
    se = SignalEngine()

    before, after = {}, {}
    fin_saved = 0

    for row in rows:
        rid = row["id"]
        corp = row["entity_id"]
        before[rid] = {
            "name": row["entity_name"],
            "score": row["aggregate_score"],
            "deal_type": row["suggested_deal_type"],
            "urgency": row["urgency"],
            "thesis": row["thesis_suggestion"],
        }

        fin_signals: list = []
        z_zone = icr_val = None
        if corp:
            # 저장: Mythos (1회계연도 4보고서)
            try:
                mythos_rows = await fetcher.fetch_mythos_rows(corp, row["entity_name"])
                if mythos_rows:
                    await asyncio.to_thread(db.save_financial_rows, corp, mythos_rows)
                    fin_saved += 1
            except Exception as e:
                print(f"  mythos save err {row['entity_name']}: {str(e)[:80]}")
            # 스코어: raw features → detect_signals
            try:
                feats = await fetcher.fetch_multi_period(corp, corp, row["entity_name"], periods=4)
            except Exception as e:
                feats = []
                print(f"  fetch err {row['entity_name']}: {str(e)[:60]}")
            if feats:
                cur_feat = feats[0]
                z = fe.calculate_altman_z(cur_feat)
                icr = fe.calculate_icr(cur_feat)
                z_zone, icr_val = z.get("z_zone"), icr.get("icr")
                fin_signals = fe.detect_signals(cur_feat, feats[1:])

        agg = await rescore(se, row, fin_signals)

        conn2 = db.get_conn()
        c2 = conn2.cursor()
        c2.execute(
            """UPDATE signal_room
               SET aggregate_score=%s, suggested_deal_type=%s, urgency=%s,
                   thesis_suggestion=%s, reason_summary=%s, updated_at=NOW()
               WHERE id=%s""",
            (agg["aggregate_score"], agg["suggested_deal_type"], agg["urgency"],
             agg["thesis_suggestion"],
             json.dumps(agg["reason_codes"], ensure_ascii=False), rid),
        )
        conn2.commit()
        c2.close()
        conn2.close()

        after[rid] = {
            "score": agg["aggregate_score"],
            "deal_type": agg["suggested_deal_type"],
            "urgency": agg["urgency"],
            "thesis": agg["thesis_suggestion"],
            "fin_signals": len(fin_signals),
            "z_zone": z_zone,
            "icr": icr_val,
        }
        print(f"  [{rid}] {row['entity_name']:12s} {before[rid]['score']:>3}→{agg['aggregate_score']:>3}점"
              f"  fin신호 {len(fin_signals)}  Z={z_zone} ICR={icr_val}")
        await asyncio.sleep(0.2)

    # ── 리포트 ──
    print("\n" + "=" * 70)
    print("entity_financial_features 저장:", fin_saved, "엔티티")

    def dist(snap):
        d = {}
        for v in snap.values():
            k = v["score"]
            d[k] = d.get(k, 0) + 1
        return dict(sorted(d.items()))

    print("\n점수 분포 BEFORE:", dist(before))
    print("점수 분포 AFTER :", dist(after))

    print("\n변경된 카드:")
    for rid in before:
        b, a = before[rid], after[rid]
        if (b["score"] != a["score"]) or (b["thesis"] != a["thesis"]):
            print(f"  {b['name']:12s} {b['score']}→{a['score']}점 | {b['urgency']}→{a['urgency']}")
            print(f"      thesis: {b['thesis']}")
            print(f"          → : {a['thesis']}")

    print("\n한화투자증권 thesis 변경 확인:")
    for rid in before:
        if before[rid]["name"] == "한화투자증권":
            b, a = before[rid], after[rid]
            print(f"  BEFORE: {b['score']}점 / {b['urgency']} / {b['thesis']}")
            print(f"  AFTER : {a['score']}점 / {a['urgency']} / {a['thesis']}")
            print(f"  재무:   Z={a['z_zone']} ICR={a['icr']} fin신호={a['fin_signals']}")


if __name__ == "__main__":
    asyncio.run(main())
