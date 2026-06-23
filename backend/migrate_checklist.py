import psycopg2, psycopg2.extras

DB = "postgresql://postgres:kzHWAwHYzqqtwHGchrdZBDtHSVqQuiYU@thomas.proxy.rlwy.net:37556/railway"
conn = psycopg2.connect(DB, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

cur.execute("SELECT dd_level, COUNT(*) as cnt FROM checklist_item_master WHERE deal_type='DIRECT_LENDING' GROUP BY dd_level")
for r in cur.fetchall(): print(r)

cur.close()
conn.close()
