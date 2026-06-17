import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
import bcrypt
import psycopg2
import psycopg2.extras
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
    cur.execute("SELECT * FROM deal_master ORDER BY created_at DESC")
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

        cur.execute(
            """
            UPDATE deal_evidence_checklist
            SET status = %s, waiver_reason = %s, waived_by = %s, waiver_expires_at = %s,
                waived_at = CASE WHEN %s = 'WAIVED' THEN now() ELSE waived_at END,
                received_at = CASE WHEN %s IN ('RECEIVED','VERIFIED') THEN now() ELSE received_at END,
                verified_at = CASE WHEN %s = 'VERIFIED' THEN now() ELSE verified_at END,
                updated_at = now()
            WHERE deal_master_id = %s AND evidence_item_code = %s
            RETURNING id
            """,
            (body.status, body.waiver_reason, body.waived_by, body.waiver_expires_at,
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

