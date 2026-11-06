import aiosqlite
from datetime import datetime

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
    vip_use_counted: bool = False,
):
    async with aiosqlite.connect(str(DATABASE)) as db:
        await db.execute(
            """
            INSERT INTO tickets (
                canal_id, user_id, staff_id, fechado_por, categoria,
                robux, valor, vip, desconto, desconto_aplicado,
                status, criado_em, metodo_compra, robux_gamepass,
                vip_use_counted
            )
            VALUES (
                ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?,
                datetime('now','localtime'), ?, ?, ?
            )
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
                robux_gamepass,
                int(vip_use_counted),
            ),
        )
        await db.commit()


async def buscar_ticket(canal_id: int):
    async with aiosqlite.connect(str(DATABASE)) as db:
        cursor = await db.execute(
            """
            SELECT
                canal_id, user_id, staff_id, fechado_por,
                categoria, robux, valor, vip, desconto,
                desconto_aplicado, status, criado_em,
                metodo_compra, robux_gamepass, vip_use_counted
            FROM tickets
            WHERE canal_id = ?
            """,
            (canal_id,),
        )
        return await cursor.fetchone()


async def assumir_ticket(canal_id: int, staff_id: int):
    async with aiosqlite.connect(str(DATABASE)) as db:
        await db.execute(
            """
            UPDATE tickets
            SET staff_id = ?, status = 'Em Atendimento'
            WHERE canal_id = ?
            """,
            (staff_id, canal_id),
        )
        await db.commit()


async def registrar_fechamento(canal_id: int, staff_id: int):
    async with aiosqlite.connect(str(DATABASE)) as db:
        await db.execute(
            """
            UPDATE tickets
            SET fechado_por = ?, status = 'Fechado'
            WHERE canal_id = ?
            """,
            (staff_id, canal_id),
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
            SET robux = ?, valor = ?
            WHERE canal_id = ?
            """,
            (robux, valor, canal_id),
        )
        await db.commit()


async def fechar_ticket(canal_id: int):
    async with aiosqlite.connect(str(DATABASE)) as db:
        await db.execute(
            "DELETE FROM tickets WHERE canal_id = ?",
            (canal_id,),
        )
        await db.commit()


async def aplicar_desconto_vip_ticket_atomic(
    canal_id: int,
    novo_valor: float,
    desconto: float,
    limite: int,
):
    """Aplica e contabiliza o VIP atomicamente, sem duplicidade."""

    mes = datetime.now().strftime("%m/%Y")

    async with aiosqlite.connect(str(DATABASE)) as db:

        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            """
            SELECT user_id, desconto_aplicado, vip_use_counted
            FROM tickets
            WHERE canal_id = ?
            """,
            (canal_id,),
        )

        ticket = await cursor.fetchone()

        if ticket is None:
            await db.rollback()
            return "not_found"

        user_id, desconto_aplicado, vip_use_counted = ticket

        if bool(desconto_aplicado) or bool(vip_use_counted):
            await db.rollback()
            return "already_used"

        cursor = await db.execute(
            """
            SELECT usos
            FROM vip_uso
            WHERE user_id = ? AND mes = ?
            """,
            (user_id, mes),
        )

        row = await cursor.fetchone()

        usos = int(row[0]) if row else 0
        limite = max(0, int(limite))

        if usos >= limite:
            await db.rollback()
            return "limit_reached"

        if row:
            await db.execute(
                """
                UPDATE vip_uso
                SET usos = usos + 1
                WHERE user_id = ? AND mes = ?
                """,
                (user_id, mes),
            )
        else:
            await db.execute(
                """
                INSERT INTO vip_uso(user_id, mes, usos)
                VALUES (?, ?, 1)
                """,
                (user_id, mes),
            )

        await db.execute(
            """
            UPDATE tickets
            SET
                valor = ?,
                desconto = ?,
                desconto_aplicado = 1,
                vip = 1,
                vip_use_counted = 1
            WHERE canal_id = ?
              AND desconto_aplicado = 0
              AND vip_use_counted = 0
            """,
            (novo_valor, desconto, canal_id),
        )

        await db.commit()

        return "applied"


async def atualizar_desconto_vip_ticket(
    canal_id: int,
    novo_valor: float,
    desconto: float
):
    """Compatibilidade com chamadas antigas."""

    async with aiosqlite.connect(str(DATABASE)) as db:

        await db.execute(
            """
            UPDATE tickets
            SET
                valor = ?,
                desconto = ?,
                desconto_aplicado = 1,
                vip = 1
            WHERE canal_id = ?
            """,
            (novo_valor, desconto, canal_id),
        )

        await db.commit()
