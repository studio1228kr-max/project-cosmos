import psycopg2, psycopg2.extras

DB = "postgresql://postgres:kzHWAwHYzqqtwHGchrdZBDtHSVqQuiYU@thomas.proxy.rlwy.net:37556/railway"
conn = psycopg2.connect(DB, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

cur.execute("SELECT deal_code, deal_type FROM deal_master ORDER BY created_at DESC LIMIT 5")
for r in cur.fetchall(): print(r)

cur.close()
conn.close()
