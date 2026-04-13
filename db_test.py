import psycopg2

# Configurações de conexão
conn = psycopg2.connect(
    dbname="cupom_db",
    user="postgres",
    password="123",
    host="localhost",
    port="5432"
)

cur = conn.cursor()
cur.execute("SELECT version();")
version = cur.fetchone()
print(f"PostgreSQL version: {version[0]}")

cur.close()
conn.close()
