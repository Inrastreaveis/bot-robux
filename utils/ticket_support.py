"""Utilitários de tickets e pagamentos PIX."""

from __future__ import annotations

import discord

from utils.calculos_robux import formatar_reais
from views.pix import PixCopyView


PURCHASE_METHODS = {"Grupo", "Plus", "Gamepass", "Korblox"}

DEFAULT_TICKET_ADMIN_IDS = [
    1459424313483591711,
    1395249767671660584
]


def _ids_cargos_mencionados(config: dict) -> list[int]:
    ids = []

    for raw_id in config.get("ticket_role_ids", []) or []:
        try:
            role_id = int(raw_id)
            if role_id and role_id not in ids:
                ids.append(role_id)
        except (TypeError, ValueError):
            continue

    return ids


def _ids_admin(config: dict) -> list[int]:
    result = []

    for user_id in (
        config.get("ticket_admin_user_ids")
        or DEFAULT_TICKET_ADMIN_IDS
    ):
        try:
            user_id = int(user_id)
            if user_id and user_id not in result:
                result.append(user_id)
        except (TypeError, ValueError):
            continue

    return result


async def _buscar_membro(guild, user_id):
    member = guild.get_member(user_id)

    if member:
        return member

    try:
        return await guild.fetch_member(user_id)
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        return None


async def montar_overwrites_ticket(
    guild,
    cliente,
    config
):
    overwrites = {
        guild.default_role:
            discord.PermissionOverwrite(view_channel=False),

        cliente:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True
            )
    }

    bot_member = guild.me

    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
            mention_everyone=True
        )

    cargos = _ids_cargos_mencionados(config)

    staff_id = int(config.get("staff_role_id", 0) or 0)

    if staff_id and staff_id not in cargos:
        cargos.append(staff_id)

    for role_id in cargos:
        role = guild.get_role(role_id)

        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True
            )

    for user_id in _ids_admin(config):
        member = await _buscar_membro(guild, user_id)

        if member:
            overwrites[member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True
            )

    return overwrites


def montar_mencoes_abertura(
    guild,
    cliente,
    config
):
    partes = [
        f"👤 Cliente: {cliente.mention}"
    ]

    admins = _ids_admin(config)

    if admins:
        partes.append(
            "👮 Administração: "
            + " ".join(f"<@{uid}>" for uid in admins)
        )

    roles = []

    for role_id in _ids_cargos_mencionados(config):
        role = guild.get_role(role_id)

        if role:
            roles.append(role)

    if roles:
        partes.append(
            "🔔 Cargos notificados: "
            + " ".join(role.mention for role in roles)
        )

    allowed = discord.AllowedMentions(
        users=True,
        roles=True,
        everyone=False,
        replied_user=False
    )

    return "\n".join(partes), allowed


def chaves_pix_ativas(config):
    """Retorna os índices e valores das chaves PIX habilitadas."""
    chave1 = str(config.get("pix_key_1", "") or "").strip()
    chave2 = str(config.get("pix_key_2", "") or "").strip()

    modo = str(
        config.get("pix_active_mode", "ambas")
    ).strip().casefold()

    if modo == "1":
        return [(1, chave1)] if chave1 else []

    if modo == "2":
        return [(2, chave2)] if chave2 else []

    selecionadas = []

    if chave1:
        selecionadas.append((1, chave1))

    if chave2:
        selecionadas.append((2, chave2))

    return selecionadas


async def enviar_pix_automatico(
    canal,
    config,
    valor,
    metodo,
    atualizacao=False
):
    if metodo not in PURCHASE_METHODS:
        return

    chaves = chaves_pix_ativas(config)

    if not chaves:
        await canal.send(
            "⚠️ **As chaves PIX ainda não foram configuradas.**\n"
            "Aguarde a equipe informar como realizar o pagamento."
        )
        return

    if valor and float(valor) > 0:
        texto_valor = (
            f"**Valor a pagar:** {formatar_reais(valor)}"
        )
    else:
        texto_valor = (
            "**Valor a pagar:** aguarde a equipe confirmar "
            "o valor neste ticket antes de pagar."
        )

    recebedor = " ".join(str(config.get("pix_receiver_name", "") or "").split())
    if recebedor:
        recebedor = discord.utils.escape_mentions(
            discord.utils.escape_markdown(recebedor)
        )
    else:
        recebedor = "Não informado — solicite confirmação à equipe."

    linhas = ["💳 **PAGAMENTO VIA PIX**"]

    if atualizacao:
        linhas.append(
            "⚠️ **VALOR ATUALIZADO:** o desconto VIP foi aplicado. "
            "Considere este novo total."
        )

    linhas.extend([
        texto_valor,
        "Efetue o pagamento para **apenas uma** das chaves abaixo.",
        f"**Nome do recebedor:** {recebedor}",
    ])

    for indice, chave in chaves:
        chave_segura = chave.replace("`", "")
        linhas.append(
            f"**Chave PIX {indice}:**\n```{chave_segura}```"
        )

    linhas.extend([
        "📎 Depois de realizar o pagamento, envie o "
        "**comprovante neste ticket** como imagem ou PDF.\n"
        "A administração será notificada automaticamente.",
        "🎮 **Depois de enviar o comprovante, informe também seu username do Roblox neste ticket.**\n"
        "Envie seu nome de usuário (username), não apenas o nome de exibição, e confira se está escrito corretamente."
    ])

    await canal.send(
        content="\n\n".join(linhas),
        view=PixCopyView(indices_chaves=[indice for indice, _ in chaves]),
        allowed_mentions=discord.AllowedMentions.none(),
    )


def eh_anexo_comprovante(attachment):
    nome = (attachment.filename or "").casefold()
    content_type = (attachment.content_type or "").casefold()

    extensoes = (
        ".png", ".jpg", ".jpeg", ".webp",
        ".gif", ".bmp", ".heic", ".pdf"
    )

    return (
        content_type.startswith("image/")
        or content_type == "application/pdf"
        or nome.endswith(extensoes)
    )


def mencoes_administracao(config):
    ids = _ids_admin(config)

    texto = " ".join(
        f"<@{user_id}>" for user_id in ids
    )

    allowed = discord.AllowedMentions(
        users=True,
        roles=False,
        everyone=False,
        replied_user=False
    )

    return texto, allowed
