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
    data
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

            data

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data
        )
    )

    await db.commit()


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
