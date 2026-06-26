import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

import jwt
import bcrypt
import psycopg2
import psycopg2.extras
import narrative_gate
import sdd_auto
import ic_memo
from evidence_engine import evaluate_evidence_engine
from refi_path_engine import evaluate_refi_path_engine
from recovery_strategy_engine_kr import evaluate_korea_recovery_strategy_engine
from deal_pipeline_orchestrator import evaluate_deal_pipeline
from fastapi import FastAPI, HTTPException, Depends, Header, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger("cosmos")

# PATCH-01: 기본값 폴백 제거 + fail-closed. 환경변수 없으면 서버 시작 거부.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be set to a >=32-byte random value")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 12  # PATCH-01: 30일 → 12시간


def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL", "postgresql://kimminwoo@localhost/cosmos"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# PATCH-03: prod에서 Swagger/OpenAPI 비공개
IS_PROD = os.getenv("RAILWAY_ENVIRONMENT") == "production"
app = FastAPI(
    title="COSMOS Deal OS API",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

# PATCH-03: 로그인 brute-force 방어.
# 멀티워커/레플리카에서 카운터 공유되도록 Redis 스토리지 사용(없으면 in-memory fallback).
limiter = Limiter(key_func=get_remote_address,
                  storage_uri=os.getenv("REDIS_URL") or "memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded,
    lambda request, exc: JSONResponse(status_code=429, content={"detail": "too many requests"}))

from quant.api import router as quant_router
app.include_router(quant_router)

# PATCH-03: CORS 화이트리스트 (* 제거)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cosmos.luskacapital.com",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# PATCH-03: 보안 헤더
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


# PATCH-03: 미처리 예외 일반화 (스택/DB 내부 노출 차단)
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


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


# PATCH-02: RBAC. 현재 운영 사용자 role='gp'(최상위 권한)이므로 gp를 항상 포함.
ADMIN_ROLES = ("gp", "admin")
EDITOR_ROLES = ("gp", "admin", "editor")


def require_role(*allowed_roles):
    def dep(payload: dict = Depends(verify_token)):
        if payload.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="insufficient role")
        return payload
    return dep


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
def delete_deal(deal_code: str, payload: dict = Depends(require_role(*ADMIN_ROLES))):
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
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
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
@limiter.limit("5/minute")
def token(request: Request, username: str = Form(...), password: str = Form(...)):
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


@app.get("/deals/{deal_code}")
def get_deal_by_code(deal_code: str, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT deal_code as id, deal_name, deal_type,
                   stage as status, stage, origination_posture, is_test,
                   created_at, updated_at,
                   '{}'::json as deal_record,
                   '[]'::json as status_history
            FROM deal_master
            WHERE deal_code = %s
        """, (deal_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="딜 없음")
        return dict(row)
    finally:
        cur.close()
        conn.close()

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
    dd_tier: str = "CDD"
    source_type: str = "UNKNOWN"
    source_replicability: str = "UNKNOWN"
    source_note: Optional[str] = None
    is_test: bool = False
    maturity_date: Optional[str] = None
    exposure_amount: Optional[int] = None


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
def api_get_checklist(deal_code: str, dd_tier: str = None, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, deal_type, dd_tier FROM deal_master WHERE deal_code = %s", (deal_code,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="deal not found")
        deal_id = deal["id"]

        # 대상 티어 결정: 쿼리 파라미터 > 딜의 현재 티어 > CDD
        target = dd_tier or deal["dd_tier"] or "CDD"
        cur.execute("SELECT tier_rank FROM dd_tier_registry WHERE dd_tier = %s", (target,))
        tr = cur.fetchone()
        if not tr:
            raise HTTPException(status_code=400, detail=f"unknown dd_tier '{target}'")
        target_rank = tr["tier_rank"]

        # 레거시 자가치유: dd_tier가 NULL인 기존 체크리스트 행을 템플릿에서 백필
        cur.execute(
            """
            UPDATE deal_evidence_checklist c
            SET dd_tier = t.dd_tier
            FROM evidence_gate_template t
            WHERE c.deal_master_id = %s AND c.dd_tier IS NULL
              AND t.deal_type_code = c.deal_type_code
              AND t.evidence_item_code = c.evidence_item_code
            """,
            (deal_id,),
        )

        # 대상 티어(누적) 항목이 없으면 생성 — 멱등(ON CONFLICT DO NOTHING)
        cur.execute("SELECT fn_create_deal_checklist(%s, %s, %s)", (deal_id, deal["deal_type"], target))

        # 사용자가 명시적으로 티어를 변경한 경우 딜에 반영
        if dd_tier and dd_tier != deal["dd_tier"]:
            cur.execute("UPDATE deal_master SET dd_tier = %s, updated_at = now() WHERE id = %s", (dd_tier, deal_id))
        conn.commit()

        # 대상 티어 이하(누적) 항목만 반환
        cur.execute(
            """
            SELECT c.*, t.tier_rank, t.tier_label
            FROM deal_evidence_checklist c
            JOIN dd_tier_registry t ON t.dd_tier = c.dd_tier
            WHERE c.deal_master_id = %s AND t.tier_rank <= %s
            ORDER BY t.tier_rank, c.requirement_level, c.evidence_item_code
            """,
            (deal_id, target_rank),
        )
        items = cur.fetchall()

        DONE = ("VERIFIED", "WAIVED")
        total = len(items)
        done = sum(1 for i in items if i["status"] in DONE)
        mand_total = sum(1 for i in items if i["requirement_level"] == "MANDATORY")
        mand_done = sum(1 for i in items if i["requirement_level"] == "MANDATORY" and i["status"] in DONE)

        return {
            "deal_code": deal_code,
            "dd_tier": target,
            "counts": {"total": total, "done": done, "mandatory_total": mand_total, "mandatory_done": mand_done},
            "checklist": items,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


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


# ── Deal Intake v1.0 (6-step overlay) ──────────────────────────────
class SourcingDetailIn(BaseModel):
    channel_key: str
    discovery_path: Optional[str] = None
    discovery_note: Optional[str] = None
    discovery_date: Optional[str] = None
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    broker_contact: Optional[str] = None
    broker_history: Optional[str] = None
    broker_fee: Optional[str] = None
    referrer_name: Optional[str] = None
    referrer_org: Optional[str] = None
    referrer_type: Optional[str] = None
    exclusive_share: Optional[bool] = False
    platform_name: Optional[str] = None
    platform_type: Optional[str] = None
    etc_note: Optional[str] = None


class DealRegisterIn(BaseModel):
    deal_name: str
    deal_type: str
    sourcing_channel: str
    sourcing_detail: SourcingDetailIn
    referrer: Optional[str] = None
    thesis: str
    target_irr: Optional[str] = None
    counterparty_motive: str
    info_edge: str
    counterparty_tier: str
    sector: str
    complexity: str
    kill_criteria: List[str] = []
    ic_memo: Optional[str] = None


@app.post("/deals/register")
def register_deal(payload: DealRegisterIn, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM deal_type_registry WHERE deal_type_code = %s", (payload.deal_type,))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail=f"unknown deal_type '{payload.deal_type}'")
        if payload.counterparty_tier not in ("T1", "T2", "T3"):
            raise HTTPException(status_code=400, detail="counterparty_tier must be T1/T2/T3")
        if payload.complexity not in ("단순", "중간", "복잡"):
            raise HTTPException(status_code=400, detail="complexity must be 단순/중간/복잡")

        deal_code = f"LSK-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"
        cur.execute(
            """
            INSERT INTO deal_master (
                deal_code, deal_name, deal_type, dd_tier,
                sourcing_channel, thesis, target_irr,
                counterparty_motive, info_edge,
                counterparty_tier, sector, complexity,
                ic_memo, stage
            ) VALUES (%s,%s,%s,'SDD',%s,%s,%s,%s,%s,%s,%s,%s,%s,'INTAKE')
            RETURNING id
            """,
            (
                deal_code, payload.deal_name, payload.deal_type,
                payload.sourcing_channel, payload.thesis, payload.target_irr,
                payload.counterparty_motive, payload.info_edge,
                payload.counterparty_tier, payload.sector, payload.complexity,
                payload.ic_memo,
            ),
        )
        deal_id = cur.fetchone()["id"]

        sd = payload.sourcing_detail
        cur.execute(
            """
            INSERT INTO deal_sourcing_detail (
                deal_id, channel_key,
                discovery_path, discovery_note, discovery_date,
                broker_name, broker_company, broker_contact,
                broker_history, broker_fee,
                referrer_name, referrer_org, referrer_type, exclusive_share,
                platform_name, platform_type, etc_note
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                deal_id, sd.channel_key,
                sd.discovery_path, sd.discovery_note, sd.discovery_date,
                sd.broker_name, sd.broker_company, sd.broker_contact,
                sd.broker_history, sd.broker_fee,
                sd.referrer_name, sd.referrer_org, sd.referrer_type,
                sd.exclusive_share or False,
                sd.platform_name, sd.platform_type, sd.etc_note,
            ),
        )

        for kc in payload.kill_criteria:
            cur.execute(
                "INSERT INTO deal_kill_criteria (deal_id, criteria, is_custom) VALUES (%s,%s,%s)",
                (deal_id, kc, True),
            )

        # SDD 체크리스트 자동 생성 (evidence_gate_template → deal_checklist_item)
        cur.execute("SELECT fn_create_sdd_checklist(%s, %s) AS n", (deal_id, payload.deal_type))
        sdd_count = cur.fetchone()["n"]

        conn.commit()
        return {"deal_id": deal_id, "deal_code": deal_code, "status": "registered", "sdd_items_created": sdd_count}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


# ── Kill Check v1.0 ────────────────────────────────────────────
class KillCheckIn(BaseModel):
    deal_id: int
    result: str                       # PASS or DROP
    drop_reasons: List[str] = []


@app.post("/deals/kill-check")
def submit_kill_check(payload: KillCheckIn, _auth: dict = Depends(require_role(*EDITOR_ROLES))):
    if payload.result not in ("PASS", "DROP"):
        raise HTTPException(status_code=400, detail="result must be PASS or DROP")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE deal_master
            SET kill_check_status = %s,
                kill_check_at     = NOW(),
                kill_check_drops  = %s,
                stage = CASE WHEN %s = 'PASS' THEN 'SDD' ELSE 'DROPPED' END
            WHERE id = %s
            RETURNING id, deal_code, kill_check_status
            """,
            (payload.result, json.dumps(payload.drop_reasons), payload.result, payload.deal_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="deal not found")

        cur.execute(
            "INSERT INTO deal_kill_check_log (deal_id, result, drop_reasons) VALUES (%s, %s, %s)",
            (payload.deal_id, payload.result, json.dumps(payload.drop_reasons)),
        )

        # PASS 시 SDD AUTO 자동 채움 (corp_code 있을 때 best-effort)
        auto = None
        if payload.result == "PASS":
            cur.execute("SELECT dart_corp_code FROM deal_master WHERE id=%s", (payload.deal_id,))
            cc = cur.fetchone()
            if cc and cc["dart_corp_code"]:
                try:
                    auto = sdd_auto.populate(cur, payload.deal_id, cc["dart_corp_code"])
                except Exception as e:
                    print(f"kill-check auto-populate skip: {e}")

        conn.commit()
        return {"deal_id": row["id"], "deal_code": row["deal_code"], "status": row["kill_check_status"],
                "auto_populated": (auto["filled_count"] if auto else 0)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.get("/deals/dashboard")
def get_dashboard_deals(_auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, deal_code, deal_name, deal_type,
                   kill_check_status, stage, dd_tier,
                   thesis, counterparty_motive, info_edge,
                   registered_at
            FROM deal_master
            WHERE kill_check_status = 'PASS'
            ORDER BY registered_at DESC NULLS LAST
            """
        )
        rows = cur.fetchall()
        return {"deals": [dict(r) for r in rows]}
    finally:
        cur.close()
        conn.close()


# ── Deal Detail (1.5단계) v1.0 ─────────────────────────────────
@app.get("/deals/{deal_id}/detail")
def get_deal_detail(deal_id: int, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM deal_master WHERE id = %s", (deal_id,))
        deal_row = cur.fetchone()
        if not deal_row:
            raise HTTPException(status_code=404, detail="deal not found")
        deal = dict(deal_row)

        cur.execute("SELECT * FROM deal_checklist_item WHERE deal_id = %s ORDER BY dd_tier, display_order, id", (deal_id,))
        checklist = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM deal_field_observation WHERE deal_id = %s ORDER BY created_at DESC", (deal_id,))
        observations = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM deal_gate_result WHERE deal_id = %s ORDER BY created_at DESC LIMIT 1", (deal_id,))
        gate = cur.fetchone()

        return {
            "deal": deal,
            "checklist": checklist,
            "observations": observations,
            "latest_gate": dict(gate) if gate else None,
        }
    finally:
        cur.close()
        conn.close()


class ChecklistUpdateIn(BaseModel):
    item_id: int
    status: str
    value_text: Optional[str] = None
    file_url: Optional[str] = None
    item_status: Optional[str] = None   # Narrative Gate용 (PENDING/CONFIRMED/NOT_AVAILABLE)


@app.patch("/deals/checklist/item")
def update_detail_checklist_item(payload: ChecklistUpdateIn, _auth: dict = Depends(require_role(*EDITOR_ROLES))):
    if payload.item_status is not None and payload.item_status not in ("PENDING", "CONFIRMED", "NOT_AVAILABLE"):
        raise HTTPException(status_code=400, detail="invalid item_status")
    # PATCH-02: VERIFIED는 증빙 file_url 필수 (무증빙 통과 차단)
    if payload.status == "VERIFIED" and not payload.file_url:
        raise HTTPException(status_code=400, detail="VERIFIED requires evidence file_url")
    conn = get_conn()
    cur = conn.cursor()
    try:
        # 감사 로그용 이전 상태 조회
        cur.execute("SELECT status FROM deal_checklist_item WHERE id = %s", (payload.item_id,))
        prev = cur.fetchone()
        old_status = prev["status"] if prev else None
        cur.execute(
            """
            UPDATE deal_checklist_item
            SET status = %s, value_text = %s, file_url = %s,
                item_status = COALESCE(%s, item_status), updated_at = NOW()
            WHERE id = %s
            RETURNING id, status, item_status
            """,
            (payload.status, payload.value_text, payload.file_url, payload.item_status, payload.item_id),
        )
        row = cur.fetchone()
        if row:
            # PATCH-02: 변경 이력 audit
            cur.execute(
                """INSERT INTO checklist_audit_log (item_id, actor, old_status, new_status, file_url)
                   VALUES (%s,%s,%s,%s,%s)""",
                (payload.item_id, _auth.get("sub"), old_status, payload.status, payload.file_url),
            )
        if not row:
            raise HTTPException(status_code=404, detail="checklist item not found")
        conn.commit()
        return dict(row)
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


# ── Narrative Gate (P0) ────────────────────────────────────────
class NarrativeGateRequest(BaseModel):
    thesis_type: str


def _run_narrative_gate(cur, deal_id: int, deal_type: str, thesis_type: str) -> dict:
    """SDD item_status 읽어 게이트 계산 + narrative_gate_results 저장."""
    cur.execute(
        "SELECT item_code, item_name, item_status FROM deal_checklist_item WHERE deal_id=%s AND dd_tier='SDD'",
        (deal_id,),
    )
    items = [dict(r) for r in cur.fetchall()]
    res = narrative_gate.compute_gate(deal_type, thesis_type, items)
    cur.execute(
        """
        INSERT INTO narrative_gate_results
            (deal_id, thesis_type, gate_result, supported_count, contradicted_items, missing_evidence, auto_reason)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id, created_at
        """,
        (deal_id, thesis_type, res["gate_result"], res["supported_count"],
         json.dumps(res["contradicted_items"], ensure_ascii=False),
         json.dumps(res["missing_evidence"], ensure_ascii=False), res["auto_reason"]),
    )
    row = cur.fetchone()
    return {**res, "id": row["id"], "created_at": row["created_at"], "evaluated_items": len(items)}


@app.post("/api/deals/{deal_id}/narrative-gate")
def api_run_narrative_gate(deal_id: int, body: NarrativeGateRequest, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, deal_type, thesis_type FROM deal_master WHERE id=%s", (deal_id,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="deal not found")
        old = deal["thesis_type"]
        # thesis_type 변경 시 이력 저장 + deal 갱신 (→ 자동 재실행)
        if body.thesis_type != old:
            cur.execute(
                "INSERT INTO deal_thesis_history (deal_id, old_thesis_type, new_thesis_type) VALUES (%s,%s,%s)",
                (deal_id, old, body.thesis_type),
            )
            cur.execute("UPDATE deal_master SET thesis_type=%s, updated_at=NOW() WHERE id=%s",
                        (body.thesis_type, deal_id))
        result = _run_narrative_gate(cur, deal_id, deal["deal_type"], body.thesis_type)
        conn.commit()
        return result
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.get("/api/deals/{deal_id}/narrative-gate")
def api_get_narrative_gate(deal_id: int, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT deal_type, thesis_type FROM deal_master WHERE id=%s", (deal_id,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="deal not found")
        cur.execute(
            "SELECT * FROM narrative_gate_results WHERE deal_id=%s ORDER BY id DESC LIMIT 1", (deal_id,)
        )
        latest = cur.fetchone()
        return {
            "deal_type": deal["deal_type"],
            "current_thesis_type": deal["thesis_type"],
            "available_thesis_types": narrative_gate.list_thesis_types(deal["deal_type"]),
            "latest": dict(latest) if latest else None,
        }
    finally:
        cur.close()
        conn.close()


# ── SDD AUTO 연결 (P0) ─────────────────────────────────────────
class SddAutoRequest(BaseModel):
    corp_code: Optional[str] = None


@app.post("/api/deals/{deal_id}/sdd/auto-populate")
def api_sdd_auto_populate(deal_id: int, body: SddAutoRequest, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, deal_type, dart_corp_code FROM deal_master WHERE id=%s", (deal_id,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="deal not found")
        corp_code = body.corp_code or deal["dart_corp_code"]
        if not corp_code:
            raise HTTPException(status_code=400, detail="corp_code 필요 (DART 고유 8자리 코드)")
        if body.corp_code and body.corp_code != deal["dart_corp_code"]:
            cur.execute("UPDATE deal_master SET dart_corp_code=%s, updated_at=NOW() WHERE id=%s", (corp_code, deal_id))
        result = sdd_auto.populate(cur, deal_id, corp_code)
        conn.commit()
        return result
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


# ── IC Memo (Claude 연결) ──
class IcMemoGenIn(BaseModel):
    force: bool = False   # 잠금 무시 강제 생성(테스트용)


@app.post("/api/deals/{deal_id}/ic-memo/generate")
def api_ic_memo_generate(deal_id: int, body: IcMemoGenIn, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE id=%s", (deal_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="deal not found")
        result = ic_memo.generate(cur, deal_id, force=body.force)
        if result.get("locked"):
            conn.rollback()
            raise HTTPException(status_code=423, detail={"message": "IC Memo 잠금 — 조건 미충족", "unlock": result["unlock"]})
        conn.commit()
        return result
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.get("/api/deals/{deal_id}/ic-memo")
def api_ic_memo_get(deal_id: int, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM ic_memos WHERE deal_id=%s ORDER BY generated_at DESC LIMIT 1", (deal_id,))
        memo = cur.fetchone()
        unlock = ic_memo.check_unlock(cur, deal_id)
        return {"memo": dict(memo) if memo else None, "unlock": unlock}
    finally:
        cur.close()
        conn.close()


class IcMemoPatchIn(BaseModel):
    s9_user_input: Optional[dict] = None
    s10_user_input: Optional[str] = None
    s10_recommendation: Optional[str] = None   # PROMOTE | CONDITIONAL | HOLD


@app.patch("/api/deals/{deal_id}/ic-memo")
def api_ic_memo_patch(deal_id: int, body: IcMemoPatchIn, _auth: dict = Depends(verify_token)):
    if body.s10_recommendation and body.s10_recommendation not in ("PROMOTE", "CONDITIONAL", "HOLD"):
        raise HTTPException(status_code=400, detail="invalid recommendation")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM ic_memos WHERE deal_id=%s ORDER BY generated_at DESC LIMIT 1", (deal_id,))
        memo = cur.fetchone()
        if not memo:
            raise HTTPException(status_code=404, detail="ic memo not found — 먼저 생성하세요")
        cur.execute("""UPDATE ic_memos SET
                s9_user_input = COALESCE(%s, s9_user_input),
                s10_user_input = COALESCE(%s, s10_user_input),
                s10_recommendation = COALESCE(%s, s10_recommendation),
                updated_at = NOW()
            WHERE id=%s RETURNING id, s9_user_input, s10_user_input, s10_recommendation""",
            (json.dumps(body.s9_user_input) if body.s9_user_input is not None else None,
             body.s10_user_input, body.s10_recommendation, memo["id"]))
        conn.commit()
        return dict(cur.fetchone())
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


class ObservationIn(BaseModel):
    deal_id: int
    obs_type: str
    severity: str
    obs_text: str
    risk_domain: Optional[str] = None


@app.post("/deals/observation")
def add_observation(payload: ObservationIn, _auth: dict = Depends(verify_token)):
    impact_map = {"INFO": None, "WATCH": "WARNING", "REVIEW": "REVIEW", "CRITICAL": "HOLD", "FATAL": "FAIL"}
    if payload.severity not in impact_map:
        raise HTTPException(status_code=400, detail="invalid severity")
    gate_impact = impact_map.get(payload.severity)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO deal_field_observation
            (deal_id, obs_type, severity, obs_text, risk_domain, gate_impact)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (payload.deal_id, payload.obs_type, payload.severity, payload.obs_text, payload.risk_domain, gate_impact),
        )
        obs_id = cur.fetchone()["id"]
        conn.commit()
        return {"obs_id": obs_id, "gate_impact": gate_impact}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


class GateRequestIn(BaseModel):
    deal_id: int
    dd_tier: str


@app.post("/deals/gate/request")
def request_gate(payload: GateRequestIn, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status IN ('VERIFIED','RECEIVED')) AS done
            FROM deal_checklist_item WHERE deal_id = %s AND dd_tier = %s
            """,
            (payload.deal_id, payload.dd_tier),
        )
        row = cur.fetchone()
        total = row["total"] or 1
        done = row["done"] or 0
        pct = int(done / total * 100)

        cur.execute(
            "SELECT COUNT(*) AS cnt FROM deal_field_observation WHERE deal_id = %s AND severity IN ('CRITICAL','FATAL')",
            (payload.deal_id,),
        )
        rf_cnt = cur.fetchone()["cnt"]

        checklist_gate = "PASS" if pct >= 80 else "INCOMPLETE" if pct >= 50 else "FAIL"
        red_flag_gate = "FAIL" if rf_cnt > 0 else "PASS"
        narrative_gate = "WEAK"  # Phase 2: 엔진 연결 후 자동화
        rank = {"PASS": 3, "INCOMPLETE": 2, "WEAK": 2, "HOLD": 1, "FAIL": 0}
        final = min([checklist_gate, red_flag_gate, narrative_gate], key=lambda g: rank.get(g, 0))
        if final == "WEAK":
            final = "HOLD"

        cur.execute(
            """
            INSERT INTO deal_gate_result
            (deal_id, dd_tier, checklist_gate, red_flag_gate, narrative_gate, final_gate)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id, final_gate
            """,
            (payload.deal_id, payload.dd_tier, checklist_gate, red_flag_gate, narrative_gate, final),
        )
        result = dict(cur.fetchone())
        if final == "PASS" and payload.dd_tier == "SDD":
            cur.execute("UPDATE deal_master SET stage='CDD' WHERE id=%s", (payload.deal_id,))
        conn.commit()
        return {**result, "checklist_pct": pct, "red_flag_count": rf_cnt}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


# ── Signal Room (data-pipeline 연동) ───────────────────────────
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")


@app.post("/api/signals/ingest")
def ingest_signal(payload: dict, x_internal_key: Optional[str] = Header(None)):
    # 내부망 공유 시크릿 인증 (data-pipeline → cosmos)
    if not INTERNAL_API_KEY or x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="invalid internal key")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO signal_room
                (external_signal_id, entity_name, entity_id, signal_type, aggregate_score,
                 suggested_deal_type, urgency, thesis_suggestion, reason_summary)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (external_signal_id) DO NOTHING
            """,
            (
                payload.get("id"), payload.get("entity_name"), payload.get("entity_id"),
                payload.get("signal_type"), payload.get("aggregate_score"),
                payload.get("suggested_deal_type"), payload.get("urgency"),
                payload.get("thesis_suggestion"),
                json.dumps(payload.get("reason_codes", []), ensure_ascii=False),
            ),
        )
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.get("/api/signals")
def get_signals(_auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM signal_room
            WHERE status = 'NEW'
            ORDER BY CASE urgency WHEN 'CRITICAL_72H' THEN 1 WHEN 'WATCH_2W' THEN 2 ELSE 3 END,
                     aggregate_score DESC
            LIMIT 50
            """
        )
        return {"signals": [dict(r) for r in cur.fetchall()]}
    finally:
        cur.close()
        conn.close()


@app.post("/api/signals/{signal_id}/convert")
def convert_to_deal(signal_id: int, _auth: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM signal_room WHERE id = %s", (signal_id,))
        signal = cur.fetchone()
        if not signal:
            raise HTTPException(status_code=404, detail="signal not found")
        return {
            "prefill": {
                "deal_name": signal["entity_name"],
                "deal_type": signal["suggested_deal_type"],
                "thesis": signal["thesis_suggestion"],
                "sourcing_channel": "자동소싱",
            }
        }
    finally:
        cur.close()
        conn.close()


@app.post("/api/signals/{signal_id}/auto-source")
def auto_source_signal(signal_id: int, _auth: dict = Depends(verify_token)):
    """Signal → 딜 자동 등록 → Kill Check 자동 → PASS 시 SDD AUTO → Narrative Gate → IC Memo
    전체 자동화 체인. 사람 개입 시점은 S9 숫자/S10 의견뿐."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM signal_room WHERE id=%s", (signal_id,))
        sig = cur.fetchone()
        if not sig:
            raise HTTPException(status_code=404, detail="signal not found")
        if sig.get("status") == "CONVERTED" and sig.get("deal_id"):
            return {"already_converted": True, "deal_id": sig["deal_id"],
                    "notification": "이미 전환된 신호입니다."}

        deal_type = sig.get("suggested_deal_type") or "DIRECT_LENDING"
        corp_code = sig.get("entity_id")   # signal_room.entity_id == DART corp_code
        thesis = sig.get("thesis_suggestion") or ""
        # 딜타입 첫 thesis_type 자동 선택
        ttypes = narrative_gate.list_thesis_types(deal_type)
        thesis_type = ttypes[0]["thesis_type"] if ttypes else None

        # 1) DealIntake 자동 채움 → deal_master 생성
        deal_code = f"LSK-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"
        cur.execute(
            """INSERT INTO deal_master
                (deal_code, deal_name, deal_type, dd_tier, sourcing_channel, thesis, thesis_type,
                 dart_corp_code, stage, sector)
               VALUES (%s,%s,%s,'SDD','자동소싱',%s,%s,%s,'INTAKE',%s) RETURNING id""",
            (deal_code, sig["entity_name"], deal_type, thesis, thesis_type, corp_code, sig.get("signal_type")))
        deal_id = cur.fetchone()["id"]
        cur.execute("SELECT fn_create_sdd_checklist(%s, %s) AS n", (deal_id, deal_type))

        # 2) Kill Check 자동 실행 (signal 기반 6개 질문 자동 답변)
        kill_qa = [
            {"q": "법인 실존/등기 유효?", "a": f"DART corp_code {corp_code or '미상'} 기준 실존" if corp_code else "corp_code 미상 — 보강 필요"},
            {"q": "명백한 사기/폐업 정황?", "a": "자동 소싱 신호상 없음"},
            {"q": "딜타입 적합성?", "a": f"제안 딜타입 {deal_type}"},
            {"q": "Thesis 성립 가능?", "a": thesis or "신호 thesis 미상"},
            {"q": "규제/제재 대상?", "a": "신호상 해당 없음"},
            {"q": "진행 가치(스코어)?", "a": f"aggregate_score {sig.get('aggregate_score')}"},
        ]
        kill_pass = bool(corp_code)   # corp_code 없으면 DROP(자동 채움 불가)
        kill_result = "PASS" if kill_pass else "DROP"
        kill_drops = [] if kill_pass else ["corp_code 미상 — 자동 소싱 불가"]
        cur.execute(
            """UPDATE deal_master SET kill_check_status=%s, kill_check_at=NOW(), kill_check_drops=%s,
               stage=CASE WHEN %s='PASS' THEN 'SDD' ELSE 'DROPPED' END WHERE id=%s""",
            (kill_result, json.dumps(kill_drops), kill_result, deal_id))
        cur.execute("INSERT INTO deal_kill_check_log (deal_id, result, drop_reasons) VALUES (%s,%s,%s)",
                    (deal_id, kill_result, json.dumps([q["a"] for q in kill_qa], ensure_ascii=False)))

        chain = {"sdd_auto": None, "narrative_gate": None, "ic_memo": None}
        if not kill_pass:
            cur.execute("UPDATE signal_room SET status='CONVERTED', deal_id=%s, updated_at=NOW() WHERE id=%s", (deal_id, signal_id))
            conn.commit()
            return {"deal_id": deal_id, "deal_code": deal_code, "kill_check": kill_result,
                    "kill_qa": kill_qa, "chain": chain,
                    "notification": "Kill Check DROP — corp_code 미상으로 자동 소싱 중단, 수동 확인 필요"}

        # 3) PASS 자동 체인: SDD AUTO → Narrative Gate → IC Memo
        auto = sdd_auto.populate(cur, deal_id, corp_code)
        chain["sdd_auto"] = {"filled": auto["filled_count"], "na": auto["na_count"], "flags": auto["quality_flags"]}

        if thesis_type:
            cur.execute("SELECT item_code, item_name, item_status FROM deal_checklist_item WHERE deal_id=%s AND dd_tier='SDD'", (deal_id,))
            items = [dict(r) for r in cur.fetchall()]
            g = narrative_gate.compute_gate(deal_type, thesis_type, items)
            cur.execute(
                """INSERT INTO narrative_gate_results
                   (deal_id, thesis_type, gate_result, supported_count, contradicted_items, missing_evidence, auto_reason)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (deal_id, thesis_type, g["gate_result"], g["supported_count"],
                 json.dumps(g["contradicted_items"], ensure_ascii=False),
                 json.dumps(g["missing_evidence"], ensure_ascii=False), g["auto_reason"]))
            chain["narrative_gate"] = {"result": g["gate_result"], "supported": g["supported_count"]}

        memo_ready = False
        try:
            memo = ic_memo.generate(cur, deal_id)
            if memo.get("locked"):
                chain["ic_memo"] = {"locked": True, "unlock": memo["unlock"]}
            else:
                memo_ready = True
                chain["ic_memo"] = {"locked": False, "memo_id": memo["memo_id"], "gate_result": memo.get("gate_result")}
        except Exception as e:
            chain["ic_memo"] = {"error": str(e)}

        cur.execute("UPDATE signal_room SET status='CONVERTED', deal_id=%s, updated_at=NOW() WHERE id=%s", (deal_id, signal_id))
        conn.commit()

        notification = ("IC Memo 초안 준비됨 — 확인해줘" if memo_ready
                        else "자동 체인 완료 — IC Memo 잠금(조건 미충족), 딜 상세에서 확인 필요")
        return {"deal_id": deal_id, "deal_code": deal_code, "kill_check": kill_result,
                "kill_qa": kill_qa, "chain": chain, "memo_ready": memo_ready,
                "notification": notification}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.patch("/api/signals/{signal_id}/status")
def update_signal_status(signal_id: int, payload: dict, _auth: dict = Depends(verify_token)):
    status = payload.get("status")
    if status not in ("NEW", "WATCHING", "CONVERTED", "DISMISSED"):
        raise HTTPException(status_code=400, detail="invalid status")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE signal_room SET status = %s, updated_at = NOW() WHERE id = %s RETURNING id, status",
            (status, signal_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="signal not found")
        conn.commit()
        return dict(row)
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.post("/api/risk-book/deals")
def api_create_deal(body: NewDealRequest, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM deal_type_registry WHERE deal_type_code = %s", (body.deal_type,))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail=f"unknown deal_type '{body.deal_type}'")

        cur.execute("SELECT 1 FROM dd_tier_registry WHERE dd_tier = %s", (body.dd_tier,))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail=f"unknown dd_tier '{body.dd_tier}'")

        cur.execute("SELECT 1 FROM deal_master WHERE deal_code = %s", (body.deal_code,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"deal_code '{body.deal_code}' already exists")

        cur.execute(
            """
            INSERT INTO deal_master
                (deal_code, deal_name, deal_type, stage, source_type, source_replicability, source_note,
                 asset_class, module_code, origination_posture, dd_tier, is_test, maturity_date, exposure_amount)
            VALUES (%s,%s,%s,'INTAKE',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (body.deal_code, body.deal_name, body.deal_type, body.source_type, body.source_replicability,
             body.source_note, body.asset_class, body.module_code, body.origination_posture, body.dd_tier,
             body.is_test, body.maturity_date, body.exposure_amount),
        )
        deal_id = cur.fetchone()["id"]

        cur.execute("SELECT fn_create_deal_checklist(%s, %s, %s) AS n",
                    (deal_id, body.deal_type, body.dd_tier))
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
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
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
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
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
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()



@app.get("/api/risk-book/deals/{deal_code}/risk-card")
def api_risk_card(deal_code: str, payload: dict = Depends(verify_token)):
    """
    Risk Card API — 딜 화면 우측 패널용.
    failure_analysis + failure_items 테이블에서 최신 진단 결과를 IC-grade 카드 형태로 반환.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="deal not found")

        deal_id = row["id"]

        # 최신 failure_analysis
        cur.execute("""
            SELECT id, gate_derived, overall_severity, critical_count, moderate_count,
                   created_at
            FROM failure_analysis
            WHERE deal_master_id = %s
            ORDER BY id DESC LIMIT 1
        """, (deal_id,))
        analysis = cur.fetchone()

        if not analysis:
            cur.close()
            conn.close()
            return {
                "deal_code": deal_code,
                "gate_result": "NO_ANALYSIS",
                "gate_reasons": [],
                "quant": {"pd_structural": None, "lifetime_pd_hazard": None, "el_12m": None, "el_ratio": None},
                "diagnostic_summary": {},
                "calculated_at": None,
            }

        analysis_id = analysis["id"]

        # failure_items에서 quant 지표 추출
        cur.execute("""
            SELECT failure_dimension, failure_code, failure_label, severity,
                   metric_name, metric_value, threshold_value, breach_amount
            FROM failure_items
            WHERE failure_analysis_id = %s
            ORDER BY severity DESC, failure_dimension
        """, (analysis_id,))
        items = cur.fetchall()

        cur.close()
        conn.close()

        # quant 값 추출
        pd_structural = None
        lifetime_pd = None
        el_12m = None
        el_ratio = None
        for item in items:
            mn = item.get("metric_name") or ""
            mv = item.get("metric_value")
            if mn == "pd_structural_raw":
                pd_structural = mv
            elif mn == "lifetime_pd_hazard":
                lifetime_pd = mv
            elif mn == "expected_loss_12m":
                el_12m = mv
            elif mn == "el_to_exposure_ratio":
                el_ratio = mv

        # CRITICAL 게이트 이유
        gate_reasons = [
            {
                "severity": item["severity"],
                "label": item["failure_label"],
                "dimension": item["failure_dimension"],
                "metric_name": item.get("metric_name"),
                "metric_value": item.get("metric_value"),
            }
            for item in items
            if item["severity"] == "CRITICAL"
        ]

        # MOLIT collateral 항목 (severity 무관하게 항상 포함)
        collateral_item = next(
            (item for item in items if item.get("failure_code", "").startswith("MARKET_COLLATERAL_MOLIT")),
            None
        )
        collateral = None
        if collateral_item:
            collateral = {
                "flag": collateral_item["failure_code"].replace("MARKET_COLLATERAL_MOLIT_", ""),
                "label": collateral_item["failure_label"],
                "molit_ltv": float(collateral_item["metric_value"]) if collateral_item.get("metric_value") else None,
                "description": collateral_item.get("description"),
                "severity": collateral_item["severity"],
            }

        return {
            "deal_code": deal_code,
            "gate_result": analysis["gate_derived"],
            "gate_reasons": gate_reasons,
            "collateral": collateral,
            "quant": {
                "pd_structural": pd_structural,
                "lifetime_pd_hazard": lifetime_pd,
                "el_12m": el_12m,
                "el_ratio": el_ratio,
            },
            "diagnostic_summary": {
                "overall_severity": analysis["overall_severity"],
                "critical_count": analysis["critical_count"],
                "moderate_count": analysis["moderate_count"],
            },
            "calculated_at": str(analysis["created_at"]) if analysis.get("created_at") else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")


@app.post("/api/infra/dart/ingest")
def dart_ingest(days: int = 90, payload: dict = Depends(verify_token)):
    """DART 공시 이벤트 수집 트리거 — lookback_days 기본 90일."""
    try:
        import sys
        sys.path.insert(0, "/app/ingestors")
        from ingestors.dart_ingestor import run_ingestion
        result = run_ingestion(lookback_days=days)
        return {"status": "ok", "stats": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")


@app.get("/api/infra/dart/events")
def dart_events(
    limit: int = 50,
    event_type: str = "",
    payload: dict = Depends(verify_token)
):
    """최근 DART 이벤트 조회."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if event_type:
            cur.execute("""
                SELECT corp_name, report_nm, rcept_dt, event_type, deal_master_id, ingested_at
                FROM dart_disclosure_events
                WHERE event_type = %s
                ORDER BY rcept_dt DESC LIMIT %s
            """, (event_type, limit))
        else:
            cur.execute("""
                SELECT corp_name, report_nm, rcept_dt, event_type, deal_master_id, ingested_at
                FROM dart_disclosure_events
                ORDER BY rcept_dt DESC LIMIT %s
            """, (limit,))
        rows = cur.fetchall()
        return rows
    finally:
        cur.close()
        conn.close()


@app.post("/api/infra/migrate/deal-collateral")
def migrate_deal_collateral(payload: dict = Depends(verify_token)):
    """deal_collateral 테이블 생성 + ANH 딜 초기 데이터 삽입."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deal_collateral (
                id                  SERIAL PRIMARY KEY,
                deal_master_id      INTEGER REFERENCES deal_master(id),
                asset_address       TEXT,
                sido_cd             TEXT,
                sgg_cd              TEXT,
                bjdong_cd           TEXT,
                bun                 TEXT,
                ji                  TEXT,
                asset_type          TEXT DEFAULT 'COMMERCIAL_RE',
                address_confidence  TEXT DEFAULT 'MANUAL',
                molit_last_synced   DATE,
                created_at          TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_collateral_deal ON deal_collateral(deal_master_id);
            CREATE INDEX IF NOT EXISTS idx_collateral_bjdong ON deal_collateral(bjdong_cd);
        """)
        cur.execute("""
            INSERT INTO deal_collateral
                (deal_master_id, asset_address, sido_cd, sgg_cd, bjdong_cd, bun, ji, address_confidence)
            SELECT dm.id,
                '서울시 강남구 봉은사로 455',
                '11', '11680', '1168010800', '455', '0', 'MANUAL'
            FROM deal_master dm
            WHERE dm.deal_code = 'LSK-2026-7003EE'
              AND NOT EXISTS (
                SELECT 1 FROM deal_collateral dc WHERE dc.deal_master_id = dm.id
              )
        """)
        conn.commit()
        return {"status": "ok", "message": "deal_collateral 테이블 생성 + ANH 초기 데이터 삽입 완료"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.post("/api/infra/molit/ingest")
def molit_ingest(months: int = 3, payload: dict = Depends(verify_token)):
    """MOLIT 실거래가 수집 트리거."""
    try:
        from ingestors.molit_ingestor import run_ingestion
        result = run_ingestion(months_back=months)
        return {"status": "ok", "stats": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")


@app.get("/api/infra/molit/trades")
def molit_trades(
    lawd_cd: str = "",
    deal_ym: str = "",
    limit: int = 20,
    payload: dict = Depends(verify_token)
):
    """MOLIT 정규화 거래 조회."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        where = []
        args = []
        if lawd_cd:
            where.append("lawd_cd = %s")
            args.append(lawd_cd)
        if deal_ym:
            where.append("deal_ym = %s")
            args.append(deal_ym)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        args.append(limit)
        cur.execute(f"""
            SELECT lawd_cd, sgg_nm, deal_ym, deal_date, deal_amount_eok,
                   building_use, area_sqm, price_per_sqm, buyer_type
            FROM molit_trade_normalized
            {where_sql}
            ORDER BY deal_date DESC LIMIT %s
        """, args)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/api/risk-book/deals/{deal_code}/run-diagnostic")
def trigger_diagnostic(deal_code: str, payload: dict = Depends(verify_token)):
    """failure_engine 수동 재실행."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="딜 없음")
        deal_id = row["id"]
    finally:
        cur.close()
        conn.close()
    try:
        from failure_engine import run_failure_diagnostic
        result = run_failure_diagnostic(deal_id)
        return {"status": "ok", "deal_code": deal_code, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")

@app.post("/api/infra/migrate/add-collateral-area")
def migrate_collateral_area(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE deal_collateral
            ADD COLUMN IF NOT EXISTS area_sqm NUMERIC(12,2)
        """)
        cur.execute("""
            UPDATE deal_collateral SET area_sqm = 2917.0
            WHERE bjdong_cd = '1168010800' AND bun = '455'
        """)
        conn.commit()
        return {"status": "ok", "message": "area_sqm 컬럼 추가 + ANH 면적 2917㎡ 세팅"}
    finally:
        cur.close()
        conn.close()

@app.post("/api/infra/migrate/cashflow-schema")
def migrate_cashflow_schema(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS deal_cashflow_assumptions (
            id SERIAL PRIMARY KEY,
            deal_master_id INTEGER NOT NULL REFERENCES deal_master(id),
            instrument_type VARCHAR(40) NOT NULL,
            scenario_label VARCHAR(20) NOT NULL DEFAULT 'BASE',
            assumption_version INTEGER NOT NULL DEFAULT 1,
            notional_eok NUMERIC(14,4),
            currency VARCHAR(10) DEFAULT 'KRW',
            origination_date DATE,
            maturity_date DATE,
            rate_type VARCHAR(20),
            base_index VARCHAR(20),
            spread_bps NUMERIC(8,2),
            floor_rate NUMERIC(8,4),
            cap_rate NUMERIC(8,4),
            reset_frequency_months INTEGER,
            interest_payment_frequency_months INTEGER DEFAULT 3,
            day_count_convention VARCHAR(20) DEFAULT 'ACT/365',
            upfront_fee_bps NUMERIC(8,2),
            commitment_fee_bps NUMERIC(8,2),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(deal_master_id, scenario_label, assumption_version)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS deal_cashflow_cre (
            id SERIAL PRIMARY KEY,
            deal_master_id INTEGER NOT NULL REFERENCES deal_master(id),
            scenario_label VARCHAR(20) NOT NULL DEFAULT 'BASE',
            cre_collateral_type VARCHAR(30),
            loan_purpose VARCHAR(20),
            ltv_at_closing NUMERIC(6,4),
            ltc_at_closing NUMERIC(6,4),
            dscr_covenant_min NUMERIC(6,4),
            amortization_type VARCHAR(20) DEFAULT 'BULLET',
            interest_reserve_months INTEGER,
            dsra_months INTEGER,
            assumed_refi_date DATE,
            prepayment_assumption VARCHAR(20) DEFAULT 'NONE',
            extension_option_months INTEGER,
            UNIQUE(deal_master_id, scenario_label)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS deal_cashflow_pf (
            id SERIAL PRIMARY KEY,
            deal_master_id INTEGER NOT NULL REFERENCES deal_master(id),
            scenario_label VARCHAR(20) NOT NULL DEFAULT 'BASE',
            project_type VARCHAR(30),
            total_project_cost_eok NUMERIC(14,4),
            equity_contribution_eok NUMERIC(14,4),
            ltc_at_closing NUMERIC(6,4),
            construction_start_date DATE,
            construction_end_date DATE,
            expected_completion_date DATE,
            draw_schedule_type VARCHAR(20) DEFAULT 'PRO_RATA',
            interest_reserve_months INTEGER,
            dsra_months INTEGER,
            stabilized_noi_eok NUMERIC(14,4),
            exit_cap_rate NUMERIC(6,4),
            assumed_exit_date DATE,
            UNIQUE(deal_master_id, scenario_label)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS deal_cashflow_leveraged (
            id SERIAL PRIMARY KEY,
            deal_master_id INTEGER NOT NULL REFERENCES deal_master(id),
            scenario_label VARCHAR(20) NOT NULL DEFAULT 'BASE',
            tranche_type VARCHAR(20),
            has_pik_toggle BOOLEAN DEFAULT FALSE,
            pik_toggle_style VARCHAR(30),
            cash_coupon_rate NUMERIC(8,4),
            pik_coupon_rate NUMERIC(8,4),
            pik_compounding_frequency_months INTEGER DEFAULT 3,
            oid_bps NUMERIC(8,2),
            exit_fee_bps NUMERIC(8,2),
            call_protection_style VARCHAR(30),
            equity_kicker_flag BOOLEAN DEFAULT FALSE,
            amortization_type VARCHAR(20) DEFAULT 'BULLET',
            UNIQUE(deal_master_id, scenario_label)
        )""")

        conn.commit()
        return {"status": "ok", "message": "cashflow schema v1 생성 완료 (4 테이블)"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()

@app.post("/api/infra/migrate/irr-schema")
def migrate_irr_schema(payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS irr_results (
            id SERIAL PRIMARY KEY,
            deal_master_id INTEGER NOT NULL REFERENCES deal_master(id),
            scenario_label VARCHAR(20) NOT NULL DEFAULT 'BASE',
            instrument_type VARCHAR(40),
            -- 핵심 수익 지표
            lender_irr NUMERIC(8,6),
            lender_moic NUMERIC(8,4),
            npv_eok NUMERIC(14,4),
            -- DSCR
            dscr_avg NUMERIC(8,4),
            dscr_min NUMERIC(8,4),
            dscr_min_period INTEGER,
            -- Breakeven
            breakeven_occupancy NUMERIC(6,4),
            breakeven_rate NUMERIC(8,6),
            -- Refi
            refi_feasibility VARCHAR(20),
            refi_ltv_at_exit NUMERIC(6,4),
            -- 캐시플로우 요약
            total_interest_eok NUMERIC(14,4),
            total_principal_eok NUMERIC(14,4),
            total_fees_eok NUMERIC(14,4),
            total_cashflow_eok NUMERIC(14,4),
            -- 기간
            loan_term_months INTEGER,
            effective_date DATE,
            maturity_date DATE,
            -- 메타
            base_rate_used NUMERIC(8,6),
            spread_bps_used NUMERIC(8,2),
            all_in_rate NUMERIC(8,6),
            assumption_version INTEGER DEFAULT 1,
            computed_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(deal_master_id, scenario_label, assumption_version)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS irr_cashflow_schedule (
            id SERIAL PRIMARY KEY,
            irr_result_id INTEGER NOT NULL REFERENCES irr_results(id),
            period_seq INTEGER NOT NULL,
            period_date DATE NOT NULL,
            beginning_balance_eok NUMERIC(14,4),
            scheduled_interest_eok NUMERIC(14,4),
            scheduled_principal_eok NUMERIC(14,4),
            total_payment_eok NUMERIC(14,4),
            ending_balance_eok NUMERIC(14,4),
            dscr_period NUMERIC(8,4),
            is_default_period BOOLEAN DEFAULT FALSE
        )""")

        conn.commit()
        return {"status": "ok", "message": "irr_results + irr_cashflow_schedule 테이블 생성"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()

@app.post("/api/risk-book/deals/{deal_code}/run-irr")
def trigger_irr(deal_code: str, scenario: str = "BASE", payload: dict = Depends(verify_token)):
    """IRR waterfall 엔진 수동 실행."""
    from irr_engine import run_irr_for_deal, CashflowEngineError as _IRREngineError
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="딜 없음")
        deal_id = row["id"]
    finally:
        cur.close()
        conn.close()
    try:
        result = run_irr_for_deal(deal_id, scenario_label=scenario)
        if "error" in result:
            raise HTTPException(status_code=422, detail=result)
        return {"status": "ok", "deal_code": deal_code, "result": result}
    except _IRREngineError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")

@app.get("/api/risk-book/deals/{deal_code}/irr")
def get_irr(deal_code: str, scenario: str = "BASE", payload: dict = Depends(verify_token)):
    """최신 IRR 결과 조회."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="딜 없음")
        deal_id = row["id"]
        cur.execute("""
            SELECT r.*, array_agg(
                json_build_object(
                    'seq', s.period_seq, 'date', s.period_date,
                    'interest', s.scheduled_interest_eok,
                    'principal', s.scheduled_principal_eok,
                    'total', s.total_payment_eok,
                    'balance', s.ending_balance_eok,
                    'dscr', s.dscr_period
                ) ORDER BY s.period_seq
            ) AS schedule
            FROM irr_results r
            LEFT JOIN irr_cashflow_schedule s ON s.irr_result_id = r.id
            WHERE r.deal_master_id = %s AND r.scenario_label = %s
            GROUP BY r.id
            ORDER BY r.computed_at DESC LIMIT 1
        """, (deal_id, scenario))
        irr = cur.fetchone()
        if not irr:
            raise HTTPException(status_code=404, detail="IRR 결과 없음 — run-irr 먼저 실행")
        return dict(irr)
    finally:
        cur.close()
        conn.close()

@app.post("/api/ic-pack/{deal_code}/create")
def create_ic_pack(deal_code: str, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="딜 없음")
        deal_id = row["id"]

        cur.execute("""
            SELECT id, scenario_label, lender_irr, lender_moic, npv_eok,
                   dscr_avg, dscr_min, loan_term_months, all_in_rate
            FROM irr_results
            WHERE deal_master_id = %s
            ORDER BY computed_at DESC
        """, (deal_id,))
        irr_rows = cur.fetchall()
        irr_ids = {r["scenario_label"]: r["id"] for r in irr_rows}

        cur.execute("""
            INSERT INTO ic_pack (deal_master_id, pack_version, status,
                model_status, irr_result_ids, ic_date)
            VALUES (%s, 1, 'DRAFT', 'VALID', %s, CURRENT_DATE)
            ON CONFLICT ON CONSTRAINT ic_pack_deal_version_unique
            DO UPDATE SET irr_result_ids = EXCLUDED.irr_result_ids,
                          updated_at = NOW()
            RETURNING id
        """, (deal_id, json.dumps(irr_ids)))
        pack = cur.fetchone()
        conn.commit()
        return {"status": "ok", "ic_pack_id": pack["id"], "irr_linked": irr_ids}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()

@app.get("/api/ic-pack/{deal_code}")
def get_ic_pack(deal_code: str, payload: dict = Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.*, d.deal_code, d.deal_name
            FROM ic_pack p
            JOIN deal_master d ON d.id = p.deal_master_id
            WHERE d.deal_code = %s
            ORDER BY p.pack_version DESC LIMIT 1
        """, (deal_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="IC Pack 없음 — create 먼저")
        return dict(row)
    finally:
        cur.close()
        conn.close()

@app.patch("/api/ic-pack/{deal_code}")
def patch_ic_pack(deal_code: str, body: dict, payload: dict = Depends(require_role(*EDITOR_ROLES))):
    EDITABLE_FIELDS = {
        "gate_status", "data_status", "model_status", "ic_date", "prepared_by",
        "ic_recommendation", "preliminary_view",
        "failure_summary", "top3_failure_modes",
        "counterparty_summary", "behavioral_flags",
        "valuation_notes", "valueup_status",
        "exit_scenarios", "principal_loss_band",
        "key_risks",
        "recommendation", "conditions",
        "scenario_narratives",
    }
    RECOMMENDATION_ENUM = {"APPROVE", "CONDITIONAL_APPROVE", "HOLD", "REJECT", "TABLE"}

    updates = {k: v for k, v in body.items() if k in EDITABLE_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="수정 가능한 필드 없음")

    if "recommendation" in updates and updates["recommendation"] not in RECOMMENDATION_ENUM:
        raise HTTPException(status_code=400, detail=f"recommendation은 {RECOMMENDATION_ENUM} 중 하나")

    if "conditions" in updates and isinstance(updates["conditions"], list):
        if len(updates["conditions"]) > 5:
            updates["recommendation"] = "HOLD"
            updates["_auto_downgrade"] = True

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="딜 없음")
        deal_id = row["id"]

        JSONB_FIELDS = {"top3_failure_modes", "behavioral_flags", "exit_scenarios", "key_risks", "conditions", "irr_result_ids", "scenario_narratives"}
        set_clause = ", ".join(
            f"{k} = %s::jsonb" if k in JSONB_FIELDS else f"{k} = %s"
            for k in updates if k != "_auto_downgrade"
        )
        import json as _json
        values = [
            _json.dumps(v) if k in JSONB_FIELDS else v
            for k, v in updates.items() if k != "_auto_downgrade"
        ]
        values.append(deal_id)

        cur.execute(f"""
            UPDATE ic_pack SET {set_clause}, updated_at = NOW()
            WHERE deal_master_id = %s
            RETURNING id, recommendation, updated_at
        """, values)
        updated = cur.fetchone()
        conn.commit()
        result = dict(updated)
        if updates.get("_auto_downgrade"):
            result["warning"] = "조건 5개 초과 — recommendation 자동 HOLD 격하"
        return {"status": "ok", "updated": result}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


# ── 새 체크리스트 엔드포인트 (checklist_item_master 기반) ──────────────
@app.get("/api/checklist/items/{deal_type}")
def get_checklist_items(deal_type: str, dd_level: str = None, payload: dict = Depends(verify_token)):
    """딜타입별 체크리스트 항목 조회"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if dd_level:
            cur.execute("""
                SELECT * FROM checklist_item_master
                WHERE deal_type = %s AND dd_level = %s AND is_active = TRUE
                ORDER BY section_code, item_code
            """, (deal_type, dd_level))
        else:
            cur.execute("""
                SELECT * FROM checklist_item_master
                WHERE deal_type = %s AND is_active = TRUE
                ORDER BY dd_level, section_code, item_code
            """, (deal_type,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/api/checklist/deal/{deal_code}")
def get_deal_checklist(deal_code: str, dd_level: str = None, payload: dict = Depends(verify_token)):
    """딜별 체크리스트 인스턴스 조회 (없으면 자동 생성)"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, deal_type FROM deal_master WHERE deal_code = %s", (deal_code,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="딜 없음")
        deal_id = deal["id"]
        deal_type = deal["deal_type"]

        # 인스턴스 없으면 자동 생성
        cur.execute("SELECT COUNT(*) as cnt FROM deal_checklist_instance WHERE deal_master_id = %s", (deal_id,))
        if cur.fetchone()["cnt"] == 0:
            cur.execute("""
                INSERT INTO deal_checklist_instance (deal_master_id, item_code, dd_phase, dd_level)
                SELECT %s, item_code, dd_phase, dd_level
                FROM checklist_item_master
                WHERE deal_type = %s AND is_active = TRUE
                ON CONFLICT DO NOTHING
            """, (deal_id, deal_type))
            conn.commit()

        query = """
            SELECT i.*, m.section_code, m.section_name, m.item_label,
                   m.auto_fillable, m.auto_source, m.kill_switch, m.gate_blocking
            FROM deal_checklist_instance i
            JOIN checklist_item_master m ON i.item_code = m.item_code
            WHERE i.deal_master_id = %s
        """
        params = [deal_id]
        if dd_level:
            query += " AND i.dd_level = %s"
            params.append(dd_level)
        query += " ORDER BY i.dd_level, m.section_code, m.item_code"
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.patch("/api/checklist/deal/{deal_code}/{item_code}")
def update_checklist_item(deal_code: str, item_code: str, body: dict, payload: dict = Depends(verify_token)):
    """체크리스트 항목 상태 업데이트"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM deal_master WHERE deal_code = %s", (deal_code,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="딜 없음")

        status = body.get("status")
        manual_value = body.get("manual_value")
        override_comment = body.get("override_comment")

        cur.execute("""
            UPDATE deal_checklist_instance
            SET status = COALESCE(%s, status),
                manual_value = COALESCE(%s, manual_value),
                override_comment = COALESCE(%s, override_comment),
                reviewer = %s,
                reviewed_at = NOW(),
                updated_at = NOW()
            WHERE deal_master_id = %s AND item_code = %s
            RETURNING *
        """, (status, manual_value, override_comment, payload.get("sub"), deal["id"], item_code))
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="항목 없음")
        conn.commit()
        return {"status": "ok", "updated": dict(updated)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다")
    finally:
        cur.close()
        conn.close()


@app.get("/api/checklist/deal/{deal_code}/gate")
def compute_checklist_gate(deal_code: str, dd_level: str = "SDD", payload: dict = Depends(verify_token)):
    """체크리스트 게이트 자동 계산"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, deal_type FROM deal_master WHERE deal_code = %s", (deal_code,))
        deal = cur.fetchone()
        if not deal:
            raise HTTPException(status_code=404, detail="딜 없음")

        cur.execute("""
            SELECT i.status, m.kill_switch, m.gate_blocking, m.item_label
            FROM deal_checklist_instance i
            JOIN checklist_item_master m ON i.item_code = m.item_code
            WHERE i.deal_master_id = %s AND i.dd_level = %s
        """, (deal["id"], dd_level))
        items = cur.fetchall()

        kill_triggered = [r["item_label"] for r in items if r["kill_switch"] and r["status"] == "FAIL"]
        pending_blocking = [r["item_label"] for r in items if r["gate_blocking"] and r["status"] == "PENDING"]
        total = len(items)
        done = len([r for r in items if r["status"] in ("PASS", "WAIVED")])
        completion = round(done / total * 100, 1) if total > 0 else 0

        if kill_triggered:
            gate = "FAIL"
        elif pending_blocking:
            gate = "INCOMPLETE"
        else:
            gate = "PASS"

        return {
            "deal_code": deal_code,
            "dd_level": dd_level,
            "gate": gate,
            "completion_pct": completion,
            "kill_triggered": kill_triggered,
            "pending_blocking": pending_blocking,
            "total_items": total,
            "done_items": done,
        }
    finally:
        cur.close()
        conn.close()
