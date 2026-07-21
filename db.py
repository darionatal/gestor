# db.py
# pyrefly: ignore [missing-import]
import os
# pyrefly: ignore [missing-import]
from urllib.parse import quote_plus
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Tenta buscar a variável DATABASE_URL diretamente do painel do Render
DATABASE_URL = os.environ.get("DATABASE_URL")

# 2. Configurações de fallback seguras do seu NOVO projeto Supabase
user = "postgres.zlxlrpejtgrqxmpixwdq"
raw_password = "Odisseia2001FIM"  # senha do banco 
password = quote_plus(raw_password)
host = "aws-1-sa-east-1.pooler.supabase.com"
port = "5432"
dbname = "postgres"

# Se a variável do Render não existir ou estiver incompleta/com erro de porta,
# o sistema força a montagem da URL limpa e imune a falhas
if not DATABASE_URL or "://supabase.com" not in DATABASE_URL or ":" not in DATABASE_URL.split("@")[-1]:
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"

# 3. Ajuste de prefixo padrão para garantir compatibilidade com SQLAlchemy 2.0
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 4. Criação do Engine de conexão com otimização para o Pooler do Supabase
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},
    pool_pre_ping=True,      # Testa a saúde da conexão antes de usá-la
    pool_size=5,             # Mantém poucas conexões abertas para não estourar o plano gratuito
    max_overflow=10,         # Permite conexões extras temporárias sob carga
    pool_recycle=1800        # Recicla as conexões a cada 30 minutos
)

# 5. Configuração da Sessão local do Banco de Dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 6. Dependência para injeção de sessão nas rotas Flask
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
