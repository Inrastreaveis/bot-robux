import aiosqlite
from datetime import datetime
from database.database import DATABASE
from database.configuracoes import obter_configuracoes


def mes_atual():
    return datetime.now().strftime("%m/%Y")


async def obter_usos(user_id: int):

    async with aiosqlite.connect(str(DATABASE)) as db:

        cursor = await db.execute(
            """
            SELECT usos
            FROM vip_uso
            WHERE user_id = ? AND mes = ?
            """,
            (user_id, mes_atual())
        )

        resultado = await cursor.fetchone()

        return resultado[0] if resultado else 0


async def pode_usar(user_id: int):
    config = await obter_configuracoes()
    limite = int(config.get("vip_uses_per_month", 2))
    return await obter_usos(user_id) < max(0, limite)
    

async def registrar_uso(user_id: int):

    async with aiosqlite.connect(str(DATABASE)) as db:

        usos = await obter_usos(user_id)

        if usos == 0:

            await db.execute(
                """
                INSERT INTO vip_uso(user_id, mes, usos)
                VALUES (?, ?, 1)
                """,
                (
                    user_id,
                    mes_atual()
                )
            )

        else:

            await db.execute(
                """
                UPDATE vip_uso
                SET usos = usos + 1
                WHERE user_id = ? AND mes = ?
                """,
                (
                    user_id,
                    mes_atual()
                )
            )

        await db.commit()
