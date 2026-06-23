import psycopg2, psycopg2.extras

DB = "postgresql://postgres:kzHWAwHYzqqtwHGchrdZBDtHSVqQuiYU@thomas.proxy.rlwy.net:37556/railway"
conn = psycopg2.connect(DB, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

cur.execute("SELECT email, role FROM users")
for r in cur.fetchall(): print(r)

cur.close()
conn.close()
