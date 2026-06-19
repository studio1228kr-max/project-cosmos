import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
import bcrypt
import psycopg2
import psycopg2.extras
from evidence_engine import evaluate_evidence_engine
from refi_path_engine import evaluate_refi_path_engine
from recovery_strategy_engine_kr import evaluate_korea_recovery_strategy_engine
from deal_pipeline_orchestrator import evaluate_deal_pipeline
from fastapi import FastAPI, HTTPException, Depends, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 30


def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL", "postgresql://kimminwoo@localhost/cosmos"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


app = FastAPI(title="COSMOS Deal OS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    email: str
    password: str


def create_token(email: str, role: str) -> str:
    payload = {
        "sub": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}




@app.get("/dart/scan")
def dart_scan(days: int = 1, payload: dict = Depends(verify_token)):
    import requests as req_lib
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DART_API_KEY not set")

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)

    SIGNALS = {
        "기한이익상실":     ("NEG","P0",10),
        "채무불이행":       ("NEG","P0",10),
        "부도":             ("NEG","P0",10),
        "회생절차":         ("NEG","P0",10),
        "법정관리":         ("NEG","P0",10),
        "감사의견거절":     ("NEG","P0", 9),
        "감사의견부적정":   ("NEG","P0", 9),
        "계속기업":         ("NEG","P0", 9),
        "워크아웃":         ("NEG","P0", 9),
        "감사의견한정":     ("NEG","P0", 8),
        "영업정지":         ("NEG","P0", 8),
        "채권단":           ("NEG","P0", 8),
        "주채권은행":       ("NEG","P0", 8),
        "공동관리":         ("NEG","P0", 8),
        "자본잠식":         ("NEG","P0", 8),
        "주식담보":         ("NEG","P1", 7),
        "지분담보":         ("NEG","P1", 7),
        "자산양도":         ("NEG","P1", 7),
        "자산매각":         ("NEG","P1", 7),
        "상환유예":         ("NEG","P1", 7),
        "영업양도":         ("NEG","P1", 7),
        "사업부문양도":     ("NEG","P1", 7),
        "담보제공":         ("NEG","P1", 6),
        "근저당권설정":     ("NEG","P1", 6),
        "질권설정":         ("NEG","P1", 6),
        "최대주주변경":     ("NEG","P1", 6),
        "신종자본증권":     ("NEG","P1", 6),
        "만기연장":         ("NEG","P1", 6),
        "채무인수":         ("NEG","P1", 6),
        "사업부문양수":     ("NEG","P1", 6),
        "경영권변경":       ("NEG","P1", 5),
        "전환사채":         ("NEG","P1", 5),
        "신주인수권부사채": ("NEG","P1", 5),
        "지급보증":         ("NEG","P1", 5),
        "손상차손":         ("NEG","P1", 5),
        "공시번복":         ("NEG","P2", 5),
        "등급하향":         ("NEG","P2", 4),
        "제3자배정":        ("NEG","P2", 4),
        "대규모차입":       ("NEG","P2", 4),
        "영업손실":         ("NEG","P2", 4),
        "차입금증가":       ("NEG","P2", 3),
        "유상증자":         ("NEG","P2", 3),
        "신용등급":         ("NEG","P2", 3),
        "순손실":           ("NEG","P2", 3),
        "충당부채":         ("NEG","P2", 3),
        "특별배당":         ("NEG","P2", 3),
        "정정공시":         ("NEG","P2", 2),
        "재평가":           ("NEG","P2", 2),
        "차입금상환":       ("POS","P1", 6),
        "신용등급상향":     ("POS","P1", 6),
        "등급상향":         ("POS","P1", 6),
        "흑자전환":         ("POS","P1", 6),
        "담보해지":         ("POS","P1", 5),
        "조기상환":         ("POS","P1", 5),
        "출자전환":         ("POS","P1", 5),
        "전망상향":         ("POS","P1", 5),
        "부채감축":         ("POS","P1", 5),
        "재무구조개선":     ("POS","P1", 5),
        "전략적투자자":     ("POS","P2", 4),
        "재무적투자자":     ("POS","P2", 4),
        "지분투자유치":     ("POS","P2", 4),
        "관리종목해제":     ("POS","P2", 4),
        "감시해제":         ("POS","P2", 4),
        "수주증가":         ("POS","P2", 3),
        "영업이익증가":     ("POS","P2", 3),
        "순이익증가":       ("POS","P2", 3),
        "장기임대차":       ("POS","P2", 3),
        "장기공급계약":     ("POS","P2", 3),
    }

    try:
        resp = req_lib.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={"crtfc_key": api_key,
                    "bgn_de": start_dt.strftime("%Y%m%d"),
                    "end_de": end_dt.strftime("%Y%m%d"),
                    "last_reprt_at": "N", "page_count": 100},
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"DART error: {e}")

    if data.get("status") != "000":
        raise HTTPException(status_code=502, detail=data.get("message", "DART API error"))

    hits = []
    for item in data.get("list", []):
        title = item.get("report_nm", "")
        matched = [(kw, pol, p, s) for kw, (pol, p, s) in SIGNALS.items() if kw in title]
        if not matched:
            continue
        neg = [(kw, p, s) for kw, pol, p, s in matched if pol == "NEG"]
        pos = [(kw, p, s) for kw, pol, p, s in matched if pol == "POS"]
        neg_score = sum(s for _, _, s in neg)
        pos_score = sum(s for _, _, s in pos)
        if neg:
            priority = "P0" if any(p=="P0" for _,p,_ in neg) else                        "P1" if any(p=="P1" for _,p,_ in neg) else "P2"
        else:
            priority = "WATCH"
        distress = "HIGH" if neg_score>=15 else "MEDIUM" if neg_score>=8 else "LOW" if neg_score>0 else "NONE"
        oppty    = "STRONG" if pos_score>=8 else "POSITIVE" if pos_score>=4 else "MILD" if pos_score>0 else "NEUTRAL"
        hits.append({
            "corp_name":           item.get("corp_name",""),
            "report_title":        title,
            "disclosed_at":        item.get("rcept_dt",""),
            "dart_url":            f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no','')}",
            "neg_signals":         [{"keyword":kw,"score":s} for kw,_,s in neg],
            "pos_signals":         [{"keyword":kw,"score":s} for kw,_,s in pos],
            "neg_score":           neg_score,
            "pos_score":           pos_score,
            "priority":            priority,
            "distress_profile":    distress,
            "opportunity_profile": oppty,
        })

    po = {"P0":0,"P1":1,"P2":2,"WATCH":3}
    hits.sort(key=lambda x: (po.get(x["priority"],4), -x["neg_score"]))

    return {
        "scanned_at":    datetime.utcnow().isoformat(),
        "days":          days,
        "total_scanned": len(data.get("list",[])),
        "summary": {
            "P0":            sum(1 for h in hits if h["priority"]=="P0"),
            "P1":            sum(1 for h in hits if h["priority"]=="P1"),
            "P2":            sum(1 for h in hits if h["priority"]=="P2"),
            "WATCH":         sum(1 for h in hits if h["priority"]=="WATCH"),
            "total_hits":    len(hits),
            "high_distress": sum(1 for h in hits if h["distress_profile"]=="HIGH"),
            "opportunity":   sum(1 for h in hits if h["opportunity_profile"] in ("STRONG","POSITIVE")),
        },
        "hits": hits,
    }




@app.get("/assets/onbid")
def onbid_search(
    keyword: str = "",
    page: int = 1,
    size: int = 20,
    payload: dict = Depends(verify_token)
):
    import requests as req_lib
    api_key = os.getenv("DATA_GO_KR_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DATA_GO_KR_KEY not set")

    try:
        resp = req_lib.get(
            "https://apis.data.go.kr/B010003/OnbidRlstListSrvc2/getRlstCltrList2",
            params={"serviceKey": api_key, "pageNo": page, "numOfRows": size,
                    "prptDivCd": "10", "pvctTrgtYn": "Y", "type": "json"},
            timeout=15,
        )
        if not resp.text.strip():
            return {"fetched_at": datetime.utcnow().isoformat(), "total_count": 0, "returned": 0, "items": [], "note": "no data"}
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OnBid error: {e}")

    body = data.get("response", {}).get("body", {})
    total_count = body.get("totalCount", 0)
    items = body.get("items", {})
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        items = []

    if keyword:
        items = [i for i in items if keyword in (i.get("ldNm", "") or "")]

    results = []
    for item in items:
        results.append({
            "cltr_no":        item.get("cltrNo"),
            "name":           item.get("cltrNm"),
            "asset_type":     item.get("prdtylNm"),
            "location":       item.get("ldNm"),
            "area":           item.get("area"),
            "appraised_value": item.get("apprsAmt"),
            "min_bid_price":  item.get("minBidPrc"),
            "bid_start":      item.get("bidBeginDt"),
            "bid_end":        item.get("bidEndDt"),
            "disp_method":    item.get("dspsMethodNm"),
        })

    return {
        "fetched_at":  datetime.utcnow().isoformat(),
        "total_count": total_count,
        "returned":    len(results),
        "items":       results,
    }




@app.delete("/api/risk-book/deals/{deal_code}")
def delete_deal(deal_code: str, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, is_test FROM deal_master WHERE deal_code = %s", (deal_code,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="deal not found")
    deal_id = row["id"]
    cur.execute("DELETE FROM deal_evidence_checklist WHERE deal_master_id = %s", (deal_id,))
    cur.execute("DELETE FROM gate_results WHERE deal_master_id = %s", (deal_id,))
    cur.execute("DELETE FROM risk_scenarios WHERE deal_master_id = %s", (deal_id,))
    cur.execute("DELETE FROM exception_log WHERE deal_master_id = %s", (deal_id,))
    cur.execute("DELETE FROM deal_master WHERE id = %s", (deal_id,))
    conn.commit()
    cur.close(); conn.close()
    return {"deleted": deal_code}




def _auto_triage(hit: dict) -> dict:
    """DART/OnBid hit → 4분기 triage + reason codes"""
    reason_codes = []
    neg_score = hit.get("neg_score", 0)
    priority = hit.get("priority", "P2")
    regulatory_risk = "low"
    legal_flag = False
    foreign_flag = False
    political_flag = False

    # 비재무 리스크 키워드 감지
    title = (hit.get("report_title", "") or "").lower()
    corp = (hit.get("corp_name", "") or "")

    if any(k in title for k in ["외국법인","해외","suntrans","international","overseas"]):
        foreign_flag = True
        reason_codes.append("FLAG_FOREIGN_ENTITY")

    if any(k in title for k in ["행정처분","영업정지","과태료","행정명령","세금체납","압류"]):
        legal_flag = True
        regulatory_risk = "high"
        reason_codes.append("FLAG_LEGAL_ISSUE")

    if any(k in title for k in ["국가기간","방산","국방","공공기관","국유","공기업"]):
        political_flag = True
        regulatory_risk = "high"
        reason_codes.append("FLAG_POLITICAL_SENSITIVITY")

    if priority == "P0":
        regulatory_risk = "high" if regulatory_risk == "low" else regulatory_risk

    # 4분기 결정
    if regulatory_risk == "high" and legal_flag:
        decision = "AUTO_REJECT"
        reason_codes.append("REJECT_REGULATORY_LEGAL")
        explanation = f"규제/법적 리스크 HIGH. 자동 거절."
    elif priority == "P0" and neg_score >= 15:
        decision = "AUTO_REJECT"
        reason_codes.append("REJECT_EXTREME_DISTRESS")
        explanation = f"NEG score {neg_score}, P0. 극단적 distress — 구조화 여지 검토 필요."
    elif foreign_flag or political_flag:
        decision = "MANUAL_REVIEW"
        reason_codes.append("MANUAL_FOREIGN_OR_POLITICAL")
        explanation = f"외국법인/정치 민감도 플래그. 수동 검토 필요."
    elif priority == "P0" or (priority == "P1" and neg_score >= 8):
        decision = "AUTO_CREATE_DEAL"
        reason_codes.append(f"AUTO_P{priority[1]}_DISTRESS_SIGNAL")
        explanation = f"{priority} 신호 (neg_score={neg_score}). deal_candidates 등록."
    elif priority == "P1":
        decision = "WATCHLIST"
        reason_codes.append("WATCH_P1_MILD")
        explanation = f"P1 신호이나 score 낮음 ({neg_score}). 모니터링."
    else:
        decision = "WATCHLIST"
        reason_codes.append("WATCH_P2_LOW_SIGNAL")
        explanation = f"P2 약한 신호. 와치리스트."

    return {
        "decision": decision,
        "regulatory_risk": regulatory_risk,
        "legal_issue_flag": legal_flag,
        "foreign_entity_flag": foreign_flag,
        "political_sensitivity_flag": political_flag,
        "decision_reason_codes": reason_codes,
        "decision_explanation": explanation,
    }


@app.post("/api/sourcing/dart-to-candidates")
def dart_to_candidates(days: int = 1, payload: dict = Depends(verify_token)):
    """DART scan → deal_candidates 자동 저장 + triage"""
    import requests as req_lib
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DART_API_KEY not set")

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)

    SIGNALS = {
        "기한이익상실":("NEG","P0",10),"채무불이행":("NEG","P0",10),"부도":("NEG","P0",10),
        "회생절차":("NEG","P0",10),"법정관리":("NEG","P0",10),"감사의견거절":("NEG","P0",9),
        "계속기업":("NEG","P0",9),"워크아웃":("NEG","P0",9),"자본잠식":("NEG","P0",8),
        "채권단":("NEG","P0",8),"주채권은행":("NEG","P0",8),"영업정지":("NEG","P0",8),
        "주식담보":("NEG","P1",7),"자산양도":("NEG","P1",7),"상환유예":("NEG","P1",7),
        "담보제공":("NEG","P1",6),"최대주주변경":("NEG","P1",6),"만기연장":("NEG","P1",6),
        "전환사채":("NEG","P1",5),"손상차손":("NEG","P1",5),
    }

    try:
        resp = req_lib.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={"crtfc_key": api_key,
                    "bgn_de": start_dt.strftime("%Y%m%d"),
                    "end_de": end_dt.strftime("%Y%m%d"),
                    "last_reprt_at": "N", "page_count": 100},
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    conn = get_conn()
    cur = conn.cursor()
    created = 0
    skipped = 0

    for item in data.get("list", []):
        title = item.get("report_nm", "")
        matched = [(kw, pol, p, s) for kw, (pol, p, s) in SIGNALS.items() if kw in title]
        if not matched:
            continue

        neg = [(kw, p, s) for kw, pol, p, s in matched if pol == "NEG"]
        neg_score = sum(s for _, _, s in neg)
        priority = "P0" if any(p=="P0" for _,p,_ in neg) else "P1" if any(p=="P1" for _,p,_ in neg) else "P2"

        hit = {
            "corp_name": item.get("corp_name",""),
            "report_title": title,
            "disclosed_at": item.get("rcept_dt",""),
            "dart_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no','')}",
            "neg_score": neg_score,
            "pos_score": 0,
            "priority": priority,
            "distress_profile": "HIGH" if neg_score>=15 else "MEDIUM" if neg_score>=8 else "LOW",
            "neg_signals": [{"keyword":kw,"score":s} for kw,_,s in neg],
        }

        t = _auto_triage(hit)

        # 중복 체크 (같은 dart_url)
        cur.execute("SELECT id FROM deal_candidates WHERE dart_url = %s", (hit["dart_url"],))
        if cur.fetchone():
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO deal_candidates
            (source_system, corp_name, report_title, disclosed_at, dart_url,
             neg_score, pos_score, priority, distress_profile, neg_signals,
             regulatory_risk, legal_issue_flag, foreign_entity_flag, political_sensitivity_flag,
             decision, decision_reason_codes, decision_explanation)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            "DART", hit["corp_name"], hit["report_title"], hit["disclosed_at"], hit["dart_url"],
            hit["neg_score"], hit["pos_score"], hit["priority"], hit["distress_profile"],
            psycopg2.extras.Json(hit["neg_signals"]),
            t["regulatory_risk"], t["legal_issue_flag"], t["foreign_entity_flag"],
            t["political_sensitivity_flag"], t["decision"],
            psycopg2.extras.Json(t["decision_reason_codes"]), t["decision_explanation"]
        ))
        created += 1

    conn.commit()
    cur.close(); conn.close()

    return {
        "scanned_at": datetime.utcnow().isoformat(),
        "days": days,
        "created": created,
        "skipped_duplicates": skipped,
    }


@app.get("/api/sourcing/candidates")
def get_candidates(decision: str = "", limit: int = 50, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    if decision:
        cur.execute(
            "SELECT * FROM deal_candidates WHERE decision = %s ORDER BY created_at DESC LIMIT %s",
            (decision, limit)
        )
    else:
        cur.execute("SELECT * FROM deal_candidates ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {"candidates": rows, "total": len(rows)}




@app.get("/api/sourcing/naver-news")
def naver_news_scan(query: str = "기한이익상실 OR 채무불이행 OR 워크아웃 OR 회생절차 OR 자본잠식", display: int = 20, payload: dict = Depends(verify_token)):
    import requests as req_lib
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="NAVER API keys not set")

    KEYWORDS = ["기한이익상실","채무불이행","워크아웃","회생절차","자본잠식","담보제공","최대주주변경","부도"]
    seen = set()
    results = []
    for kw in KEYWORDS:
        try:
            r = req_lib.get(
                "https://openapi.naver.com/v1/search/news.json",
                headers={"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret},
                params={"query": kw, "display": 10, "sort": "date"},
                timeout=10,
            )
            if r.status_code != 200:
                continue
            for item in r.json().get("items", []):
                link = item.get("link","")
                if link in seen:
                    continue
                seen.add(link)
                results.append({
                    "keyword": kw,
                    "title": item.get("title","").replace("<b>","").replace("</b>",""),
                    "description": item.get("description","").replace("<b>","").replace("</b>",""),
                    "pub_date": item.get("pubDate",""),
                    "link": link,
                    "originallink": item.get("originallink",""),
                })
        except:
            continue
    results.sort(key=lambda x: x["pub_date"], reverse=True)
    return {"total": len(results), "keywords_scanned": len(KEYWORDS), "items": results}




@app.post("/api/risk-book/evidence/evaluate")
def evidence_evaluate(body: dict, payload: dict = Depends(verify_token)):
    """범용 Evidence Engine — 어떤 deal_master/evidence_items이든 입력받아 평가"""
    try:
        result = evaluate_evidence_engine(
            deal_master=body.get("deal_master", {}),
            evidence_items=body.get("evidence_items", []),
            required_fields=body.get("required_fields"),
            p0_fields=body.get("p0_fields"),
            field_policies=body.get("field_policies"),
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@app.post("/api/risk-book/refi-path/evaluate")
def refi_path_evaluate(body: dict, payload: dict = Depends(verify_token)):
    """범용 Refi Path Engine — 월별 refi capacity/gap/DSRA depletion 경로 분석"""
    try:
        result = evaluate_refi_path_engine(
            deal_master=body.get("deal_master", {}),
            refi_path_input=body.get("refi_path_input", {}),
            scenarios=body.get("scenarios"),
            policy=body.get("policy"),
            evidence_package=body.get("evidence_package"),
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@app.post("/api/risk-book/recovery-kr/evaluate")
def recovery_kr_evaluate(body: dict, payload: dict = Depends(verify_token)):
    """한국 특화 Recovery Waterfall Engine — 우선순위(국세/임금/임차보증금/신탁) 반영 LGD"""
    try:
        result = evaluate_korea_recovery_strategy_engine(
            deal_master=body.get("deal_master", {}),
            recovery_input=body.get("recovery_input", {}),
            scenarios=body.get("scenarios"),
            policy=body.get("policy"),
            evidence_package=body.get("evidence_package"),
            refi_path_package=body.get("refi_path_package"),
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@app.post("/api/risk-book/deal-pipeline/evaluate")
def deal_pipeline_evaluate(body: dict, payload: dict = Depends(verify_token)):
    """통합 딜 파이프라인 — Evidence → Refi Path → Recovery Waterfall 순차 실행"""
    try:
        result = evaluate_deal_pipeline(
            deal_master=body.get("deal_master", {}),
            evidence_items=body.get("evidence_items"),
            required_fields=body.get("required_fields"),
            p0_fields=body.get("p0_fields"),
            evidence_field_policies=body.get("evidence_field_policies"),
            refi_path_input=body.get("refi_path_input"),
            refi_scenarios=body.get("refi_scenarios"),
            refi_policy=body.get("refi_policy"),
            recovery_input=body.get("recovery_input"),
            recovery_scenarios=body.get("recovery_scenarios"),
            recovery_policy=body.get("recovery_policy"),
        )
        result_dict = result.to_dict()

        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO pipeline_runs (deal_id, deal_name, input_payload, output_payload, final_gate, combined_gate) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    result_dict.get("deal_id"),
                    result_dict.get("deal_name"),
                    psycopg2.extras.Json(body),
                    psycopg2.extras.Json(result_dict),
                    result_dict.get("final_gate"),
                    result_dict.get("combined_gate"),
                ),
            )
            conn.commit()
            cur.close(); conn.close()
        except Exception:
            pass

        return result_dict
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@app.patch("/api/sourcing/candidates/{candidate_id}/decision")
def update_candidate_decision(candidate_id: int, body: dict, payload: dict = Depends(verify_token)):
    """신호룸 triage 액션 — 등록/보류/폐기"""
    decision = body.get("decision")
    valid = {"WATCHLIST", "REJECTED", "PROMOTED", "MANUAL_REVIEW", "AUTO_CREATE_DEAL"}
    if decision not in valid:
        raise HTTPException(status_code=400, detail=f"decision must be one of {valid}")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE deal_candidates SET decision=%s, reviewed_at=NOW(), reviewed_by=%s WHERE id=%s",
        (decision, body.get("reviewed_by", "mwkim"), candidate_id),
    )
    conn.commit()
    cur.close(); conn.close()
    return {"id": candidate_id, "decision": decision}




@app.get("/api/dashboard/meaningful-changes")
def list_meaningful_changes(payload: dict = Depends(verify_token)):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, title, note, source_link, created_at FROM meaningful_changes ORDER BY created_at DESC LIMIT 5")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"id": r[0], "title": r[1], "note": r[2], "source_link": r[3], "created_at": r[4].isoformat() if r[4] else None} for r in rows]


@app.post("/api/dashboard/meaningful-changes")
def add_meaningful_change(body: dict, payload: dict = Depends(verify_token)):
    title = body.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO meaningful_changes (title, note, source_link) VALUES (%s, %s, %s) RETURNING id",
        (title, body.get("note"), body.get("source_link")),
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return {"id": new_id}


@app.delete("/api/dashboard/meaningful-changes/{change_id}")
def delete_meaningful_change(change_id: int, payload: dict = Depends(verify_token)):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM meaningful_changes WHERE id=%s", (change_id,))
    conn.commit()
    cur.close(); conn.close()
    return {"deleted": change_id}


@app.get("/api/dashboard/market-read")
def get_market_read(payload: dict = Depends(verify_token)):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT text, updated_at FROM market_read WHERE id=1")
    row = cur.fetchone()
    cur.close(); conn.close()
    return {"text": row[0] if row else "", "updated_at": row[1].isoformat() if row and row[1] else None}


@app.put("/api/dashboard/market-read")
def update_market_read(body: dict, payload: dict = Depends(verify_token)):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE market_read SET text=%s, updated_at=NOW() WHERE id=1", (body.get("text", ""),))
    conn.commit()
    cur.close(); conn.close()
    return {"ok": True}




@app.get("/api/dashboard/scores")
def get_dashboard_scores(payload: dict = Depends(verify_token)):
    """Activity Score(0부터 누적) + Execution Health(100부터 감점) — 전부 실제 레코드 기반"""
    conn = get_conn(); cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM deal_candidates WHERE decision != 'PENDING'")
    triage_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM meaningful_changes")
    meaningful_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM deal_master WHERE is_test = false")
    deal_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM deal_evidence_checklist WHERE status IN ('VERIFIED','WAIVED')")
    evidence_done = cur.fetchone()[0]
    cur.execute("SELECT text FROM market_read WHERE id=1")
    mr_row = cur.fetchone()
    market_read_filled = 1 if (mr_row and mr_row[0]) else 0

    activity_score = triage_count + meaningful_count + deal_count + evidence_done + market_read_filled

    cur.execute("""
        SELECT dm.deal_code, gr.final_gate, ev.mandatory_total, ev.mandatory_done
        FROM deal_master dm
        LEFT JOIN LATERAL (
            SELECT final_gate FROM gate_results WHERE deal_master_id=dm.id ORDER BY id DESC LIMIT 1
        ) gr ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*) FILTER (WHERE requirement_level='MANDATORY') AS mandatory_total,
                   COUNT(*) FILTER (WHERE requirement_level='MANDATORY' AND status IN ('VERIFIED','WAIVED')) AS mandatory_done
            FROM deal_evidence_checklist WHERE deal_master_id=dm.id
        ) ev ON true
        WHERE dm.is_test = false
    """)
    deals = cur.fetchall()
    cur.close(); conn.close()

    health = 100
    blocked_count = 0
    missing_mandatory_total = 0
    for d in deals:
        gate, mand_total, mand_done = d[1], d[2] or 0, d[3] or 0
        missing = mand_total - mand_done
        missing_mandatory_total += missing
        if gate == "HOLD":
            health -= 20; blocked_count += 1
        elif gate == "REJECT":
            health -= 40; blocked_count += 1
        health -= missing * 3
    health = max(0, health)

    return {
        "activity_score": activity_score,
        "activity_breakdown": {
            "triage": triage_count,
            "meaningful_changes": meaningful_count,
            "deals_registered": deal_count,
            "evidence_completed": evidence_done,
            "market_read": market_read_filled,
        },
        "health_score": health,
        "health_breakdown": {
            "blocked_deals": blocked_count,
            "missing_mandatory": missing_mandatory_total,
        },
    }


@app.post("/login")
def login(body: LoginRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT email, hashed_password, role FROM users WHERE email = %s",
        (body.email,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(
        body.password.encode(), user["hashed_password"].encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["email"], user["role"])
    return {"token": token, "role": user["role"], "email": user["email"]}


@app.post("/token")
def token(username: str = Form(...), password: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT email, hashed_password, role FROM users WHERE email = %s",
        (username,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(
        password.encode(), user["hashed_password"].encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_token(user["email"], user["role"])
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"], "email": user["email"]}


@app.get("/deals")
def get_deals(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, status, owner, source, deal_record, action_tag,
               next_action, created_at, updated_at
        FROM deals
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@app.get("/today")
def get_today(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, action_tag FROM deals")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    p0 = sum(1 for r in rows if (r["action_tag"] or "").upper() == "P0")
    p1 = sum(1 for r in rows if (r["action_tag"] or "").upper() == "P1")
    p2 = sum(1 for r in rows if (r["action_tag"] or "").upper() == "P2")
    return {"summary": {"P0": p0, "P1": p1, "P2": p2, "total": p0 + p1 + p2}}


@app.get("/ambient")
def get_ambient(payload: dict = Depends(verify_token)):
    return {"market_status": "normal", "server_time": datetime.utcnow().isoformat()}


@app.get("/risk-book/deals")
def risk_book_deals(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT dm.*,
               gr.final_gate, gr.provisional_gate, gr.ic_ready,
               gr.hold_reasons, gr.required_actions,
               ev.evidence_total, ev.mandatory_total, ev.mandatory_done
        FROM deal_master dm
        LEFT JOIN LATERAL (
            SELECT final_gate, provisional_gate, ic_ready, hold_reasons, required_actions
            FROM gate_results WHERE deal_master_id = dm.id
            ORDER BY id DESC LIMIT 1
        ) gr ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS evidence_total,
                   COUNT(*) FILTER (WHERE requirement_level='MANDATORY') AS mandatory_total,
                   COUNT(*) FILTER (WHERE requirement_level='MANDATORY' AND status IN ('VERIFIED','WAIVED')) AS mandatory_done
            FROM deal_evidence_checklist WHERE deal_master_id = dm.id
        ) ev ON true
        ORDER BY dm.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@app.get("/risk-book/deals/{deal_id}/gate")
def risk_book_gate(deal_id: int, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM gate_results WHERE deal_master_id = %s ORDER BY id DESC LIMIT 1",
        (deal_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="no gate result")
    return row


@app.get("/api/risk-book/deals")
def api_risk_book_deals(payload: dict = Depends(verify_token)):
    return risk_book_deals(payload)


@app.get("/api/risk-book/today")
def api_risk_book_today(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT dm.deal_code, dm.deal_name, dm.is_test,
               gr.final_gate, gr.hold_reasons,
               ev.mandatory_total, ev.mandatory_done
        FROM deal_master dm
        LEFT JOIN LATERAL (
            SELECT final_gate, hold_reasons
            FROM gate_results WHERE deal_master_id = dm.id
            ORDER BY id DESC LIMIT 1
        ) gr ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*) FILTER (WHERE requirement_level='MANDATORY') AS mandatory_total,
                   COUNT(*) FILTER (WHERE requirement_level='MANDATORY' AND status IN ('VERIFIED','WAIVED')) AS mandatory_done
            FROM deal_evidence_checklist WHERE deal_master_id = dm.id
        ) ev ON true
        WHERE dm.is_test = false
        ORDER BY dm.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    actions = []
    for r in rows:
        gate = r["final_gate"]
        mand_total = r["mandatory_total"] or 0
        mand_done = r["mandatory_done"] or 0
        missing_count = mand_total - mand_done
        if gate in ("HOLD", "REJECT"):
            priority = "P0"
            reason = f"게이트 {gate} — MANDATORY {mand_done}/{mand_total} 완료"
            missing = (r["hold_reasons"] or [])[:3]
        elif missing_count > 0:
            priority = "P1"
            reason = f"MANDATORY 증거 {missing_count}건 미완료"
            missing = []
        else:
            priority = "P2"
            reason = "MANDATORY 증거 완료 — 다음 단계 검토"
            missing = []
        actions.append({
            "title": r["deal_name"],
            "deal_name": r["deal_name"],
            "deal_id": r["deal_code"],
            "reason": reason,
            "missing": missing,
            "priority": priority,
            "cta_action": "pipeline",
            "cta": "Pipeline에서 보기",
        })

    summary = {
        "P0": sum(1 for a in actions if a["priority"] == "P0"),
        "P1": sum(1 for a in actions if a["priority"] == "P1"),
        "P2": sum(1 for a in actions if a["priority"] == "P2"),
        "total": len(actions),
    }
    return {"actions": actions, "summary": summary}


@app.get("/api/risk-book/deals/{deal_code}/summary")
def api_risk_book_summary(deal_code: str, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deal_master WHERE deal_code = %s", (deal_code,))
    deal = cur.fetchone()
    if not deal:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="deal not found")

    deal_id = deal["id"]

    cur.execute(
        "SELECT * FROM gate_results WHERE deal_master_id = %s ORDER BY id DESC LIMIT 1",
        (deal_id,),
    )
    gate = cur.fetchone()

    cur.execute(
        "SELECT * FROM risk_scenarios WHERE deal_master_id = %s ORDER BY scenario_id",
        (deal_id,),
    )
    scenarios = cur.fetchall()

    cur.execute(
        """
        SELECT * FROM deal_financials
        WHERE deal_master_id = %s
        ORDER BY is_current DESC, updated_at DESC
        LIMIT 1
        """,
        (deal_id,),
    )
    financials = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "deal": deal,
        "gate": gate,
        "scenarios": scenarios,
        "financials": financials,
    }


class NewDealRequest(BaseModel):
    deal_code: str
    deal_name: str
    deal_type: str
    asset_class: str = "CRE"
    module_code: str = "CRE_SECURED_CREDIT"
    origination_posture: str = "MIXED"
    source_type: str = "UNKNOWN"
    source_replicability: str = "UNKNOWN"
    source_note: Optional[str] = None
    is_test: bool = False


class ChecklistUpdateRequest(BaseModel):
    status: str
    waiver_reason: Optional[str] = None
    waived_by: Optional[str] = None
    waiver_expires_at: Optional[str] = None


class GateCheckRequest(BaseModel):
    deal_code: str
    action_type: str
    audience: Optional[str] = None
    document_type: Optional[str] = None
    confidence: Optional[str] = None
    holder: Optional[str] = None
    text: Optional[str] = None
    log_exception: bool = False
    approved_by: Optional[str] = None


def _recompute_and_insert_gate(cur, deal_id):
    cur.execute("SELECT fn_compute_initial_gate(%s) AS gate", (deal_id,))
    gate = cur.fetchone()["gate"]
    cur.execute(
        """
        SELECT evidence_item_label FROM deal_evidence_checklist
        WHERE deal_master_id = %s AND requirement_level = 'MANDATORY'
          AND gate_blocking = true AND status NOT IN ('VERIFIED','WAIVED')
        """,
        (deal_id,),
    )
    missing = [r["evidence_item_label"] for r in cur.fetchall()]
    cur.execute(
        """
        INSERT INTO gate_results
            (deal_master_id, policy_id, data_gate, structural_gate, credit_gate, final_gate, provisional_gate,
             hold_reasons, model_version, gate_version)
        VALUES (%s,'LUSKA_GATE_V0_1','MINIMAL_NOT_MET',%s,%s,%s,%s,%s,'v1','v1')
        """,
        (deal_id, gate, gate, gate, gate, psycopg2.extras.Json(missing)),
    )
    return gate


@app.get("/api/risk-book/deal-types")
def api_deal_types(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deal_type_registry ORDER BY deal_type_code")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@app.get("/api/risk-book/deals/{deal_code}/checklist")
def api_get_checklist(deal_code: str, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
    deal = cur.fetchone()
    if not deal:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="deal not found")
    cur.execute(
        """
        SELECT * FROM deal_evidence_checklist
        WHERE deal_master_id = %s
        ORDER BY requirement_level, evidence_item_code
        """,
        (deal["id"],),
    )
    items = cur.fetchall()
    cur.close()
    conn.close()
    return {"deal_code": deal_code, "checklist": items}


@app.get("/api/risk-book/deals/search")
def api_search_deals(q: str = "", payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    if q.strip():
        cur.execute(
            """
            SELECT deal_code, deal_name, stage
            FROM deal_master
            WHERE deal_code ILIKE %s OR deal_name ILIKE %s
            ORDER BY id DESC
            LIMIT 8
            """,
            (f"%{q}%", f"%{q}%"),
        )
    else:
        cur.execute(
            "SELECT deal_code, deal_name, stage FROM deal_master ORDER BY id DESC LIMIT 8"
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"results": rows}


@app.get("/api/risk-book/action-types")
def api_action_types(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT action_type FROM gate_action_policy ORDER BY action_type")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"results": [r["action_type"] for r in rows]}


@app.get("/api/users")
def api_list_users(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email, role FROM users ORDER BY email")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"results": rows}


@app.post("/api/risk-book/deals")
def api_create_deal(body: NewDealRequest, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM deal_type_registry WHERE deal_type_code = %s", (body.deal_type,))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail=f"unknown deal_type '{body.deal_type}'")

        cur.execute("SELECT 1 FROM deal_master WHERE deal_code = %s", (body.deal_code,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"deal_code '{body.deal_code}' already exists")

        cur.execute(
            """
            INSERT INTO deal_master
                (deal_code, deal_name, deal_type, stage, source_type, source_replicability, source_note,
                 asset_class, module_code, origination_posture, is_test)
            VALUES (%s,%s,%s,'INTAKE',%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (body.deal_code, body.deal_name, body.deal_type, body.source_type, body.source_replicability,
             body.source_note, body.asset_class, body.module_code, body.origination_posture, body.is_test),
        )
        deal_id = cur.fetchone()["id"]

        cur.execute("SELECT fn_create_deal_checklist(%s, %s) AS n", (deal_id, body.deal_type))
        n_items = cur.fetchone()["n"]

        gate = _recompute_and_insert_gate(cur, deal_id)
        conn.commit()

        cur.execute(
            """
            SELECT * FROM deal_evidence_checklist WHERE deal_master_id = %s
            ORDER BY requirement_level, evidence_item_code
            """,
            (deal_id,),
        )
        checklist = cur.fetchall()

        return {
            "deal_id": deal_id,
            "deal_code": body.deal_code,
            "checklist_items_created": n_items,
            "initial_gate": gate,
            "checklist": checklist,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.patch("/api/risk-book/deals/{deal_code}/checklist/{evidence_item_code}")
def api_update_checklist(
    deal_code: str,
    evidence_item_code: str,
    body: ChecklistUpdateRequest,
    payload: dict = Depends(verify_token),
):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="deal not found")
        deal_id = deal["id"]

        if body.status == "WAIVED" and not (body.waiver_reason and body.waived_by and body.waiver_expires_at):
            raise HTTPException(status_code=400, detail="waiver requires waiver_reason, waived_by, waiver_expires_at")

        actor_email = payload.get("sub")
        cur.execute(
            """
            UPDATE deal_evidence_checklist
            SET status = %s, waiver_reason = %s, waived_by = %s, waiver_expires_at = %s,
                performed_by = %s,
                waived_at = CASE WHEN %s = 'WAIVED' THEN now() ELSE waived_at END,
                received_at = CASE WHEN %s IN ('RECEIVED','VERIFIED') THEN now() ELSE received_at END,
                verified_at = CASE WHEN %s = 'VERIFIED' THEN now() ELSE verified_at END,
                updated_at = now()
            WHERE deal_master_id = %s AND evidence_item_code = %s
            RETURNING id
            """,
            (body.status, body.waiver_reason, body.waived_by, body.waiver_expires_at, actor_email,
             body.status, body.status, body.status, deal_id, evidence_item_code),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="checklist item not found")

        gate = _recompute_and_insert_gate(cur, deal_id)
        conn.commit()
        return {
            "deal_code": deal_code,
            "evidence_item_code": evidence_item_code,
            "new_status": body.status,
            "performed_by": actor_email,
            "recomputed_gate": gate,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/api/risk-book/gate-check")
def api_gate_check(body: GateCheckRequest, payload: dict = Depends(verify_token)):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM fn_check_gate_action(%s, %s)", (body.deal_code, body.action_type))
        gate_status, g_allowed, g_watermark, g_approval, g_note = cur.fetchone()

        fin_allowed = True
        fin_requires_tag = None
        fin_tag_text = None
        fin_note = None
        if body.confidence and body.audience:
            cur.execute("SELECT * FROM fn_validate_financial_anchor(%s, %s)", (body.confidence, body.audience))
            fin_allowed, fin_requires_tag, fin_tag_text, fin_note = cur.fetchone()

        ctrl_allowed = True
        ctrl_note = None
        if body.holder and body.text:
            cur.execute("SELECT * FROM fn_validate_control_claim(%s, %s)", (body.holder, body.text))
            ctrl_allowed, _kw, ctrl_note = cur.fetchone()

        blocked = (not g_allowed) or (not ctrl_allowed)
        conditions = []
        if g_allowed and (g_watermark or g_approval):
            if g_watermark:
                conditions.append("HOLD/제한 워터마크 필수")
            if g_approval:
                conditions.append("승인자 명시 필수")
        if fin_requires_tag:
            conditions.append(f"숫자(confidence={body.confidence}) 태그 필요: [UNVERIFIED / SUBJECT TO CONFIRMATION]")

        result = "BLOCK" if blocked else ("ALLOW_WITH_CONDITIONS" if conditions else "ALLOW")

        if body.log_exception and not blocked:
            if not body.approved_by:
                raise HTTPException(status_code=400, detail="approved_by required to log exception")
            cur.execute(
                """
                INSERT INTO exception_log
                    (deal_master_id, action_type, audience, document_type, exception_type, approved_by, conditions_applied)
                SELECT id, %s, %s, %s, %s, %s, %s FROM deal_master WHERE deal_code = %s
                """,
                (body.action_type, body.audience, body.document_type, body.action_type, body.approved_by,
                 "; ".join(conditions), body.deal_code),
            )

        conn.commit()
        return {
            "result": result,
            "gate": {"status": gate_status, "allowed": g_allowed, "watermark": g_watermark, "approval": g_approval, "note": g_note},
            "financial": {"allowed": fin_allowed, "requires_tag": fin_requires_tag, "tag_text": fin_tag_text, "note": fin_note} if body.confidence else None,
            "control": {"allowed": ctrl_allowed, "note": ctrl_note} if body.holder else None,
            "conditions": conditions,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

