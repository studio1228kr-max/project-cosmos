import psycopg2, psycopg2.extras

DB = "postgresql://postgres:kzHWAwHYzqqtwHGchrdZBDtHSVqQuiYU@thomas.proxy.rlwy.net:37556/railway"

def get_railway_conn():
    return psycopg2.connect(DB, cursor_factory=psycopg2.extras.RealDictCursor)
