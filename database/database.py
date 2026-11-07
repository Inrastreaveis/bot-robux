import aiosqlite
from pathlib import Path
from datetime import datetime

# Caminho do banco de dados
DATABASE = Path(__file__).resolve().parent.parent / "database.db"


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
    robux_gamepass INTEGER DEFAULT 0,
    vip_use_counted INTEGER DEFAULT 0
)
        """)

        # Migração compatível com bancos já existentes na hospedagem.
        cursor = await db.execute("PRAGMA table_info(tickets)")
        colunas_ticket = {linha[1] for linha in await cursor.fetchall()}
        if "metodo_compra" not in colunas_ticket:
            await db.execute("ALTER TABLE tickets ADD COLUMN metodo_compra TEXT DEFAULT 'Outro'")
        if "robux_gamepass" not in colunas_ticket:
            await db.execute("ALTER TABLE tickets ADD COLUMN robux_gamepass INTEGER DEFAULT 0")
        if "vip_use_counted" not in colunas_ticket:
            await db.execute("ALTER TABLE tickets ADD COLUMN vip_use_counted INTEGER DEFAULT 0")
        # Os tickets antigos com desconto aplicado já contabilizavam o uso na confirmação.
        await db.execute(
            "UPDATE tickets SET vip_use_counted = 1 WHERE desconto_aplicado = 1 AND vip_use_counted = 0"
        )
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
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL DEFAULT 0,
            estoque INTEGER DEFAULT 0,
            descricao TEXT
        )
        """)

        # CONFIGURAÇÕES
        await db.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
        """)

        # STAFF
        await db.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            user_id INTEGER PRIMARY KEY,
            nome TEXT,
            vendas INTEGER DEFAULT 0,
            robux INTEGER DEFAULT 0,
            total REAL DEFAULT 0
        )
        """)

        # AVALIAÇÕES
        await db.execute("""
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canal_id INTEGER,
            cliente_id INTEGER,
            atendente_id INTEGER,
            fechado_por INTEGER,
            robux INTEGER,
            valor REAL,
            estrelas INTEGER,
            comentario TEXT,
            data TEXT,
            categoria TEXT DEFAULT 'Compra'
        )
        """)

        # Migração: identifica avaliações de suporte sem afetar o histórico antigo.
        cursor = await db.execute("PRAGMA table_info(avaliacoes)")
        colunas_avaliacao = {linha[1] for linha in await cursor.fetchall()}
        if "categoria" not in colunas_avaliacao:
            await db.execute(
                "ALTER TABLE avaliacoes ADD COLUMN categoria TEXT DEFAULT 'Compra'"
            )

        await db.commit()

    print("✅ Banco de dados criado com sucesso!")


# ==========================
# CONEXÃO
# ==========================
async def get_db():
    db = await aiosqlite.connect(str(DATABASE))
    return db
# ==========================
# CLIENTES
# ==========================
async def adicionar_cliente(db, user_id: int, nome: str):
    await db.execute(
        """
        INSERT OR IGNORE INTO clientes (user_id, nome)
        VALUES (?, ?)
        """,
        (user_id, nome)
    )
    await db.commit()


async def atualizar_cliente(db, user_id, valor, robux, data):
    await db.execute(
        """
        UPDATE clientes
        SET
            total_gasto = total_gasto + ?,
            robux_comprados = robux_comprados + ?,
            compras = compras + 1,
            ultima_compra = ?,
            maior_compra = MAX(maior_compra, ?)
        WHERE user_id = ?
        """,
        (
            valor,
            robux,
            data,
            valor,
            user_id
        )
    )
    await db.commit()


async def buscar_cliente(db, user_id):
    cursor = await db.execute(
        """
        SELECT *
        FROM clientes
        WHERE user_id = ?
        """,
        (user_id,)
    )

    return await cursor.fetchone()


# ==========================
# VENDAS
# ==========================
async def registrar_venda(
    db,
    user_id,
    staff_id,
    valor,
    robux,
    pagamento,
    data,
    observacao=None
):
    cursor = await db.execute(
        """
        INSERT INTO vendas (
            user_id,
            staff_id,
            valor,
            robux,
            pagamento,
            observacao,
            data
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            staff_id,
            valor,
            robux,
            pagamento,
            observacao,
            data
        )
    )

    await db.commit()

    return cursor.lastrowid


async def buscar_venda(db, venda_id):
    cursor = await db.execute(
        """
        SELECT
            id,
            user_id,
            staff_id,
            valor,
            robux,
            pagamento,
            observacao,
            data
        FROM vendas
        WHERE id = ?
        """,
        (venda_id,)
    )

    return await cursor.fetchone()


async def listar_vendas(db, limite=10):
    cursor = await db.execute(
        """
        SELECT
            id,
            user_id,
            staff_id,
            valor,
            robux,
            pagamento,
            data
        FROM vendas
        ORDER BY id DESC
        LIMIT ?
        """,
        (limite,)
    )

    return await cursor.fetchall()

# ==========================
# RANKING
# ==========================
async def obter_ranking(db, limite=10):
    cursor = await db.execute(
        """
        SELECT
            user_id,
            nome,
            total_gasto,
            robux_comprados,
            compras
        FROM clientes
        ORDER BY total_gasto DESC
        LIMIT ?
        """,
        (limite,)
    )

    return await cursor.fetchall()


# ==========================
# ESTATÍSTICAS
# ==========================
async def obter_estatisticas(db):
    cursor = await db.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(valor), 0),
            COALESCE(SUM(robux), 0),
            COALESCE(AVG(valor), 0),
            COALESCE(MAX(valor), 0)
        FROM vendas
    """)

    total_vendas, valor_total, robux_total, ticket_medio, maior_venda = await cursor.fetchone()

    cursor = await db.execute("""
        SELECT COUNT(*)
        FROM clientes
    """)

    total_clientes = (await cursor.fetchone())[0]

    return {
        "total_vendas": total_vendas,
        "valor_total": valor_total,
        "robux_total": robux_total,
        "ticket_medio": ticket_medio,
        "clientes": total_clientes,
        "maior_venda": maior_venda
    }

# ==========================
# STAFF
# ==========================
async def adicionar_staff(db, user_id: int, nome: str):
    await db.execute(
        """
        INSERT OR IGNORE INTO staff (user_id, nome)
        VALUES (?, ?)
        """,
        (user_id, nome)
    )
    await db.commit()


async def atualizar_staff(db, user_id, valor, robux):
    await db.execute(
        """
        UPDATE staff
        SET
            vendas = vendas + 1,
            robux = robux + ?,
            total = total + ?
        WHERE user_id = ?
        """,
        (robux, valor, user_id)
    )
    await db.commit()


async def obter_ranking_staff(db):
    cursor = await db.execute(
        """
        SELECT
            user_id,
            nome,
            vendas,
            robux,
            total
        FROM staff
        ORDER BY total DESC
        """
    )

    return await cursor.fetchall()
# ==========================
# EXCLUIR VENDA
# ==========================

async def remover_venda(db, venda_id):
    cursor = await db.execute("""
        SELECT
            user_id,
            staff_id,
            valor,
            robux
        FROM vendas
        WHERE id = ?
    """, (venda_id,))

    venda = await cursor.fetchone()

    if venda is None:
        return None

    user_id, staff_id, valor, robux = venda

    await db.execute(
        "DELETE FROM vendas WHERE id = ?",
        (venda_id,)
    )

    await db.commit()

    return {
        "user_id": user_id,
        "staff_id": staff_id,
        "valor": valor,
        "robux": robux
    }


async def atualizar_cliente_remocao(db, user_id, valor, robux):
    await db.execute("""
        UPDATE clientes
        SET
            total_gasto = total_gasto - ?,
            robux_comprados = robux_comprados - ?,
            compras = CASE
                WHEN compras > 0 THEN compras - 1
                ELSE 0
            END
        WHERE user_id = ?
    """, (
        valor,
        robux,
        user_id
    ))

    await db.commit()


async def atualizar_staff_remocao(db, user_id, valor, robux):
    await db.execute("""
        UPDATE staff
        SET
            vendas = CASE
                WHEN vendas > 0 THEN vendas - 1
                ELSE 0
            END,
            robux = robux - ?,
            total = total - ?
        WHERE user_id = ?
    """, (
        robux,
        valor,
        user_id
    ))

    await db.commit()


async def registrar_uso_vip(user_id):
    async with aiosqlite.connect(str(DATABASE)) as db:
        mes = datetime.now().strftime("%m/%Y")

        await db.execute("""
        INSERT INTO vip_uso (user_id, mes, usos)
        VALUES (?, ?, 1)

        ON CONFLICT(user_id, mes)
        DO UPDATE SET usos = usos + 1
        """, (user_id, mes))

        await db.commit()


async def pegar_usos_vip(user_id):
    async with aiosqlite.connect(str(DATABASE)) as db:

        mes = datetime.now().strftime("%m/%Y")

        cursor = await db.execute("""
        SELECT usos
        FROM vip_uso
        WHERE user_id = ? AND mes = ?
        """, (user_id, mes))

        resultado = await cursor.fetchone()

        if resultado:
            return resultado[0]

        return 0
    # ==========================
# AVALIAÇÕES
# ==========================

async def registrar_avaliacao(
    db,
    canal_id,
    cliente_id,
    atendente_id,
    fechado_por,
    robux,
    valor,
    estrelas,
    comentario,
    data,
    categoria="Compra",
):
    await db.execute(
        """
        INSERT INTO avaliacoes(
            canal_id,
            cliente_id,
            atendente_id,
            fechado_por,
            robux,
            valor,
            estrelas,
            comentario,
            data,
            categoria
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            canal_id,
            cliente_id,
            atendente_id,
            fechado_por,
            robux,
            valor,
            estrelas,
            comentario,
            data,
            categoria,
        ),
    )
    await db.commit()


async def avaliacao_existe(db, canal_id):
    cursor = await db.execute(
        "SELECT 1 FROM avaliacoes WHERE canal_id = ? LIMIT 1",
        (canal_id,),
    )
    return await cursor.fetchone() is not None


async def listar_avaliacoes(db, limite=20):

    cursor = await db.execute(
        """
        SELECT *

        FROM avaliacoes

        ORDER BY id DESC

        LIMIT ?
        """,
        (limite,)
    )

    return await cursor.fetchall()


async def media_staff(db, staff_id):

    cursor = await db.execute(
        """
        SELECT
            AVG(estrelas)

        FROM avaliacoes

        WHERE atendente_id = ?
        """,
        (staff_id,)
    )

    media = await cursor.fetchone()

    if media and media[0]:

        return round(media[0], 2)

    return 0

# ==========================
# TICKETS
# ==========================

async def atualizar_ticket_venda(
    db,
    canal_id: int,
    staff_id: int,
    robux: int,
    valor: float
):
    await db.execute("""
        UPDATE tickets
        SET
            staff_id = ?,
            robux = ?,
            valor = ?,
            status = 'finalizado'
        WHERE canal_id = ?
    """, (
        staff_id,
        robux,
        valor,
        canal_id
    ))
    
    await db.commit()
