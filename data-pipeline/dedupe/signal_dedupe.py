"""dedupe_key 기반 중복 제거 (signal_dedupe_map)."""
from __future__ import annotations

import db


def is_duplicate(dedupe_key: str) -> bool:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM signal_dedupe_map WHERE dedupe_key = %s", (dedupe_key,))
    dup = cur.fetchone() is not None
    cur.close()
    conn.close()
    return dup


def record_dedupe(dedupe_key: str) -> None:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO signal_dedupe_map (dedupe_key) VALUES (%s)
        ON CONFLICT (dedupe_key) DO UPDATE
          SET last_seen_at = NOW(), occurrence_count = signal_dedupe_map.occurrence_count + 1
        """,
        (dedupe_key,),
    )
    conn.commit()
    cur.close()
    conn.close()
