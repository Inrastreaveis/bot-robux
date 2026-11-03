import aiosqlite

from database.database import DATABASE


async def criar_ticket(
    canal_id: int,
    user_id: int,
    categoria: str,
    robux: int,
    valor: float,
    vip: bool,
    desconto: float,
    desconto_aplicado: bool,
    metodo_compra: str = "Outro",
    robux_gamepass: int = 0,
):
    async with aiosqlite.connect(str(DATABASE)) as db:

        await db.execute(
            """
            INSERT INTO tickets (
                canal_id,
                user_id,
                staff_id,
                fechado_por,
                categoria,
                robux,
                valor,
                vip,
                desconto,
                desconto_aplicado,
                status,
                criado_em,
                metodo_compra,
                robux_gamepass
            )
            VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'), ?, ?)
            """,
            (
                canal_id,
                user_id,
                categoria,
                robux,
                valor,
                int(vip),
                desconto,
                int(desconto_aplicado),
                "Aguardando",
                metodo_compra,
                robux_gamepass
            )
        )

        await db.commit()


async def buscar_ticket(canal_id: int):

    async with aiosqlite.connect(str(DATABASE)) as db:

        cursor = await db.execute(
            """
            SELECT
                canal_id,
                user_id,
                staff_id,
                fechado_por,
                categoria,
                robux,
                valor,
                vip,
                desconto,
                desconto_aplicado,
                status,
                criado_em,
                metodo_compra,
                robux_gamepass
            FROM tickets
            WHERE canal_id = ?
            """,
            (canal_id,)
        )

        return await cursor.fetchone()


async def assumir_ticket(
    canal_id: int,
    staff_id: int
):

    async with aiosqlite.connect(str(DATABASE)) as db:

        await db.execute(
            """
            UPDATE tickets
            SET
                staff_id = ?,
                status = 'Em Atendimento'
            WHERE canal_id = ?
            """,
            (
                staff_id,
                canal_id
            )
        )

        await db.commit()


async def registrar_fechamento(
    canal_id: int,
    staff_id: int
):

    async with aiosqlite.connect(str(DATABASE)) as db:

        await db.execute(
            """
            UPDATE tickets
            SET
                fechado_por = ?,
                status = 'Fechado'
            WHERE canal_id = ?
            """,
            (
                staff_id,
                canal_id
            )
        )

        await db.commit()


async def atualizar_valores_ticket(
    canal_id: int,
    robux: int,
    valor: float
):

    async with aiosqlite.connect(str(DATABASE)) as db:

        await db.execute(
            """
            UPDATE tickets
            SET
                robux = ?,
                valor = ?
            WHERE canal_id = ?
            """,
            (
                robux,
                valor,
                canal_id
            )
        )

        await db.commit()


async def fechar_ticket(canal_id: int):

    async with aiosqlite.connect(str(DATABASE)) as db:

        await db.execute(
            """
            DELETE FROM tickets
            WHERE canal_id = ?
            """,
            (canal_id,)
        )

        await db.commit()
        print("tickets.py carregado")
print("Funções:", dir())

async def atualizar_desconto_vip_ticket(
    canal_id: int,
    novo_valor: float,
    desconto: float,
):
    async with aiosqlite.connect(str(DATABASE)) as db:
        await db.execute(
            """
            UPDATE tickets
            SET valor = ?, desconto = ?, desconto_aplicado = 1, vip = 1
            WHERE canal_id = ?
            """,
            (novo_valor, desconto, canal_id),
        )
        await db.commit()
