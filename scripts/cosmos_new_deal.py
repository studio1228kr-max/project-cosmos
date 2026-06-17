#!/usr/bin/env python3
import argparse, os, sys, psycopg2

def main():
    p = argparse.ArgumentParser(description="신규 딜 등록 + evidence checklist 자동생성 + 초기 게이트 산정")
    p.add_argument("--deal-code", required=True)
    p.add_argument("--deal-name", required=True)
    p.add_argument("--deal-type", required=True)
    p.add_argument("--asset-class", default="CRE")
    p.add_argument("--module-code", default="CRE_SECURED_CREDIT")
    p.add_argument("--origination-posture", default="MIXED")
    p.add_argument("--source-type", default="UNKNOWN")
    p.add_argument("--source-replicability", default="UNKNOWN")
    p.add_argument("--source-note", default="")
    p.add_argument("--is-test", action="store_true")
    args = p.parse_args()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM deal_type_registry WHERE deal_type_code=%s", (args.deal_type,))
        if cur.fetchone() is None:
            print(f"ERROR: 알 수 없는 deal_type '{args.deal_type}'"); sys.exit(2)
        cur.execute("SELECT id FROM deal_master WHERE deal_code=%s", (args.deal_code,))
        if cur.fetchone():
            print(f"ERROR: deal_code '{args.deal_code}' 이미 존재"); sys.exit(2)

        cur.execute("""
            INSERT INTO deal_master
                (deal_code, deal_name, deal_type, stage, source_type, source_replicability, source_note,
                 asset_class, module_code, origination_posture, is_test)
            VALUES (%s,%s,%s,'INTAKE',%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (args.deal_code, args.deal_name, args.deal_type, args.source_type, args.source_replicability,
              args.source_note, args.asset_class, args.module_code, args.origination_posture, args.is_test))
        deal_id = cur.fetchone()[0]
        print(f"[1] deal_master 등록 완료 id={deal_id}")

        cur.execute("SELECT fn_create_deal_checklist(%s, %s)", (deal_id, args.deal_type))
        n = cur.fetchone()[0]
        print(f"[2] evidence checklist {n}건 자동생성")

        cur.execute("SELECT fn_compute_initial_gate(%s)", (deal_id,))
        gate = cur.fetchone()[0]
        print(f"[3] 초기 게이트: {gate}")

        cur.execute("""
            INSERT INTO gate_results
                (deal_master_id, policy_id, data_gate, structural_gate, credit_gate, final_gate, provisional_gate,
                 model_version, gate_version)
            VALUES (%s,'LUSKA_GATE_V0_1','MINIMAL_NOT_MET',%s,%s,%s,%s,'v1','v1')
        """, (deal_id, gate, gate, gate, gate))
        print(f"[4] gate_results 등록 완료")
        conn.commit()
        print("=== 커밋 완료 ===\n--- Checklist ---")

        cur.execute("""
            SELECT evidence_item_code, requirement_level, status FROM deal_evidence_checklist
            WHERE deal_master_id=%s ORDER BY requirement_level, evidence_item_code
        """, (deal_id,))
        for row in cur.fetchall(): print(" ", row)
    except Exception as e:
        conn.rollback(); print("ERROR:", e)
    finally:
        cur.close(); conn.close()

if __name__ == "__main__":
    main()
