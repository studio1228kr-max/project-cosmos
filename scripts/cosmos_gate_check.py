#!/usr/bin/env python3
import argparse, os, sys, datetime, psycopg2

def main():
    p = argparse.ArgumentParser(description="COSMOS 외부 문서 작성 전 preflight check")
    p.add_argument("--deal", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--audience", default="INTERNAL")
    p.add_argument("--document-type", default="")
    p.add_argument("--confidence", action="append", default=[])
    p.add_argument("--holder", default="THIRD_PARTY")
    p.add_argument("--text", default="")
    p.add_argument("--format", choices=["plain","memo"], default="plain")
    p.add_argument("--log-exception", action="store_true")
    p.add_argument("--approved-by", default="")
    args = p.parse_args()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    blocked = False
    warnings = []
    gate_status = "UNKNOWN"
    requires_approval = False
    exception_used = args.action in ("MARKET_DISCOVERY_ONLY","NON_BINDING_APPETITE_TEST")

    cur.execute("SELECT * FROM fn_check_gate_action(%s, %s)", (args.deal, args.action))
    row = cur.fetchone()
    if row is None:
        print(f"BLOCK: '{args.deal}'/'{args.action}' 조회 실패 — fail-closed")
        blocked = True
    else:
        gate_status, allowed, watermark, approval, notes = row
        requires_approval = bool(approval)
        if args.format == "plain":
            print(f"[GATE] status={gate_status} allowed={allowed} watermark={watermark} approval={approval}")
            if notes: print(f"        note: {notes}")
        if not allowed: blocked = True
        if watermark: warnings.append("HOLD/제한 워터마크 필수")
        if approval: warnings.append("승인자 명시 필수")

    for conf in args.confidence:
        cur.execute("SELECT * FROM fn_validate_financial_anchor(%s, %s)", (conf, args.audience))
        a_allowed, requires_tag, tag_text, note = cur.fetchone()
        if args.format == "plain":
            print(f"[FIN]  confidence={conf} audience={args.audience} requires_tag={requires_tag}")
            if note: print(f"        note: {note}")
        if requires_tag: warnings.append(f"숫자(confidence={conf}) 태그 필요: {tag_text}")

    if args.text:
        cur.execute("SELECT * FROM fn_validate_control_claim(%s, %s)", (args.holder, args.text))
        c_allowed, kw, note = cur.fetchone()
        if args.format == "plain":
            print(f"[CTRL] holder={args.holder} allowed={c_allowed}")
            if note: print(f"        note: {note}")
        if not c_allowed: blocked = True

    result = "BLOCK" if blocked else ("ALLOW_WITH_CONDITIONS" if warnings else "ALLOW")

    if args.log_exception:
        if not args.approved_by:
            print("ERROR: --log-exception 사용 시 --approved-by 필수"); sys.exit(2)
        cur.execute("SELECT id FROM deal_master WHERE deal_code=%s", (args.deal,))
        dm = cur.fetchone()
        cur.execute("""
            INSERT INTO exception_log (deal_master_id, action_type, audience, document_type, exception_type, approved_by, conditions_applied)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (dm[0] if dm else None, args.action, args.audience, args.document_type,
              args.action, args.approved_by, "; ".join(warnings)))
        conn.commit()
        print(f"[LOG] 예외 사용 기록됨 (approved_by={args.approved_by})")

    cur.close(); conn.close()

    if args.format == "memo":
        print("Gate Preflight:")
        print(f"  Result: {result}")
        print(f"  Checked At: {datetime.datetime.now().isoformat(timespec='seconds')}")
        print(f"  Deal: {args.deal}")
        print(f"  Action: {args.action}")
        print(f"  Audience: {args.audience}")
        print(f"  Document Type: {args.document_type or 'N/A'}")
        print(f"  Conditions: {'; '.join(warnings) if warnings else 'None'}")
    else:
        print()
        print(f"=== 결과: {result} ===")
        for w in warnings: print(f"  - {w}")

    sys.exit(1 if blocked else 0)

if __name__ == "__main__":
    main()
