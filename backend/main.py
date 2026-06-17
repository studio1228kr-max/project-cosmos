import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
import bcrypt
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Depends, Header
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
