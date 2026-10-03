# db.py
# SupaBase
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Busca a string de conexão das variáveis de ambiente ou utiliza o fallback do Supabase
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Credenciais do Supabase (Connection Pooler)
    user = "postgres.wruxchynwscgiethyjwl"
    raw_password = "Odisseia2001FIM" 
    password = quote_plus(raw_password)
    
    host = "aws-0-sa-east-1.pooler.supabase.com"
    port = "5432"       # 5432 para Session Pooler (recomendado com SQLAlchemy)
    dbname = "postgres"  # O banco no Supabase sempre se chama 'postgres'
    
    # Monta a URL para PostgreSQL
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

# 2. Ajuste de prefixo padrão para garantir compatibilidade com SQLAlchemy 2.0
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Criação do Engine de conexão com SSL e configurações otimizadas para Nuvem/Supabase
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},  # Exigido pelo Supabase para conexões seguras
    pool_pre_ping=True,                   # Verifica a conexão antes de usar (evita timeouts da nuvem)
    pool_size=5,                          # Pool reduzido adequado para conexões via pooler
    max_overflow=10,                      
    pool_recycle=300                      # Descarta conexões ociosas a cada 5 min (evita quedas do Supabase)
)

# 4. Configuração da Sessão do Banco de Dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 5. Dependência para injeção de sessão nas rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()