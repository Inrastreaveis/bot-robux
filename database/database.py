import aiosqlite
import os
from pathlib import Path
from datetime import datetime

# Caminho do banco de dados:
# - Railway: usa o volume persistente montado em /data.
# - Desenvolvimento local: mantém o banco na raiz do projeto.
# - DATABASE_PATH permite definir um caminho explícito, se necessário.
PROJECT_DATABASE = Path(__file__).resolve().parent.parent / "database.db"
VOLUME_DATABASE = Path("/data") / "database.db"

if os.getenv("DATABASE_PATH"):
    DATABASE = Path(os.environ["DATABASE_PATH"])
elif VOLUME_DATABASE.parent.is_dir():
    DATABASE = VOLUME_DATABASE
else:
    DATABASE = PROJECT_DATABASE

DATABASE.parent.mkdir(parents=True, exist_ok=True)


# ==========================
# CRIAR BANCO
# ==========================
async def criar_banco():
    async with aiosqlite.connect(str(DATABASE)) as db:

        # CLIENTES
        await db.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            user_id INTEGER PRIMARY KEY,
            nome TEXT,
            total_gasto REAL DEFAULT 0,
            robux_comprados INTEGER DEFAULT 0,
            compras INTEGER DEFAULT 0,
            primeira_compra TEXT,
            ultima_compra TEXT,
            maior_compra REAL DEFAULT 0,
            vip TEXT DEFAULT 'Bronze'
        )
        """)

        # VENDAS
        await db.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            staff_id INTEGER,
            valor REAL,
            robux INTEGER,
            pagamento TEXT,
            observacao TEXT,
            data TEXT
        )
        """)

        # TICKETS
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
    canal_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    staff_id INTEGER,
    fechado_por INTEGER DEFAULT NULL,
    categoria TEXT,
    robux INTEGER,
    valor REAL,
    vip INTEGER DEFAULT 0,
    desconto REAL DEFAULT 0,
    desconto_aplicado INTEGER DEFAULT 0,
    status TEXT,
    criado_em TEXT,
    metodo_compra TEXT DEFAULT 'Outro',
    robux_gamepass INTEGER DEFAULT 0
)
        """)

        # Migração compatível com bancos já existentes na hospedagem.
        cursor = await db.execute("PRAGMA table_info(tickets)")
        colunas_ticket = {linha[1] for linha in await cursor.fetchall()}
        if "metodo_compra" not in colunas_ticket:
            await db.execute("ALTER TABLE tickets ADD COLUMN metodo_compra TEXT DEFAULT 'Outro'")
        if "robux_gamepass" not in colunas_ticket:
            await db.execute("ALTER TABLE tickets ADD COLUMN robux_gamepass INTEGER DEFAULT 0")
        # VIP
        await db.execute("""
        CREATE TABLE IF NOT EXISTS vip_uso (
            user_id INTEGER,
            mes TEXT,
            usos INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, mes)
        )
        """)

        # PRODUTOS
        await db.execute("""
