"""마이그레이션 러너 — 001~005 순차 실행.
004(CONCURRENTLY)는 autocommit·문장단위, 나머지는 파일 1트랜잭션.
"""
import os, re, sys, psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["001_foundation.sql", "002_history_table.sql", "003_validate_checks.sql",
         "004_indexes_concurrently.sql", "005_drop_old_unique_constraint.sql",
         "006_ontology_core.sql", "007_policy_rule_seed.sql",
         "008_seed_patch.sql"]


def split_statements(sql: str):
    # $$ ... $$ 블록을 보존하며 세미콜론 분리
    out, buf, in_dollar = [], [], False
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        if "$$" in line:
            in_dollar = not in_dollar if line.count("$$") % 2 else in_dollar
        buf.append(line)
        if not in_dollar and line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def main():
    dsn = os.environ["DATABASE_URL"]
    for fn in ORDER:
        path = os.path.join(HERE, fn)
        sql = open(path, encoding="utf-8").read()
        print(f"\n=== {fn} ===")
        if "CONCURRENTLY" in sql:
            conn = psycopg2.connect(dsn); conn.autocommit = True
            cur = conn.cursor()
            for stmt in split_statements(sql):
                if not stmt.strip():
                    continue
                try:
                    cur.execute(stmt); print("  ok:", stmt.split("\n")[0][:70])
                except Exception as e:
                    print("  ERR:", str(e)[:120])
            cur.close(); conn.close()
        else:
            conn = psycopg2.connect(dsn); conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute(sql); conn.commit(); print("  committed")
            except Exception as e:
                conn.rollback(); print("  ROLLBACK:", str(e)[:160]); sys.exit(1)
            finally:
                cur.close(); conn.close()
    print("\n[all migrations done]")


if __name__ == "__main__":
    main()
