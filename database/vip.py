import aiosqlite
from datetime import datetime

from database.database import DATABASE
from database.configuracoes import obter_configuracoes


def mes_atual():
    # Mantém o mesmo formato já usado no banco atual para não zerar o histórico existente.
    return datetime.now().strftime("%m/%Y")


async def obter_usos(user_id: int):
    async with aiosqlite.connect(str(DATABASE)) as db:
        cursor = await db.execute(
            "SELECT usos FROM vip_uso WHERE user_id = ? AND mes = ?",
            (user_id, mes_atual()),
        )
        resultado = await cursor.fetchone()
        return int(resultado[0]) if resultado else 0


async def pode_usar(user_id: int):
    config = await obter_configuracoes()
    limite = max(0, int(config.get("vip_uses_per_month", 2)))
    return await obter_usos(user_id) < limite


async def registrar_uso(user_id: int, limite: int | None = None) -> bool:
    """Reserva um uso VIP de forma atômica; retorna False se o limite acabou."""
    if limite is None:
        config = await obter_configuracoes()
        limite = int(config.get("vip_uses_per_month", 2))
    limite = max(0, int(limite))
    mes = mes_atual()

    async with aiosqlite.connect(str(DATABASE)) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT usos FROM vip_uso WHERE user_id = ? AND mes = ?",
            (user_id, mes),
        )
        row = await cursor.fetchone()
        usos = int(row[0]) if row else 0

        if usos >= limite:
            await db.rollback()
            return False

        if row:
            await db.execute(
                "UPDATE vip_uso SET usos = usos + 1 WHERE user_id = ? AND mes = ?",
                (user_id, mes),
            )
        else:
            await db.execute(
                "INSERT INTO vip_uso(user_id, mes, usos) VALUES (?, ?, 1)",
                (user_id, mes),
            )
        await db.commit()
        return True
