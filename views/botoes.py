import asyncio
import discord
from decimal import Decimal


from utils.permissions import is_staff

from views.modal_venda import RegistrarVenda
from views.avaliacao import AvaliacaoView

from database.vip import obter_usos
from database.configuracoes import obter_configuracoes
from database.tickets import aplicar_desconto_vip_ticket_atomic
from utils.calculos_robux import calcular_desconto_vip, formatar_reais
from utils.ticket_support import enviar_pix_automatico
from database.tickets import (
    assumir_ticket,
    buscar_ticket,
    fechar_ticket,
    registrar_fechamento,
    atualizar_valores_ticket,
    atualizar_status_ticket,
)


async def _buscar_cliente(guild: discord.Guild, cliente_id: int):
    cliente = guild.get_member(cliente_id)
    if cliente is not None:
        return cliente
    try:
        return await guild.fetch_member(cliente_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def _finalizar_ticket_com_avaliacao(
    interaction: discord.Interaction,
    view: discord.ui.View,
):
    ticket = await buscar_ticket(interaction.channel.id)
    if ticket is None:
        return await interaction.response.send_message(
            "❌ Não foi possível localizar este ticket no banco de dados.",
            ephemeral=True,
        )

    await registrar_fechamento(interaction.channel.id, interaction.user.id)

    cliente_id = int(ticket[1])
    cliente = await _buscar_cliente(interaction.guild, cliente_id)
    if cliente is not None:
        await interaction.channel.set_permissions(
            cliente,
            view_channel=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True,
            add_reactions=True,
        )

    # Mantém o comportamento atual: quem encerrou não continua conversando no ticket.
    await interaction.channel.set_permissions(
        interaction.user,
        send_messages=False,
    )

    eh_suporte = "suporte" in str(ticket[4] or "").casefold()
    titulo = "⭐ Avaliação do Suporte" if eh_suporte else "⭐ Avaliação do Atendimento"
    texto = (
        "Seu atendimento de suporte foi finalizado.\n\n"
        "Conte como foi a experiência com nossa equipe.\n\n"
        "Escolha uma nota e, se desejar, deixe um comentário."
        if eh_suporte
        else "Seu atendimento foi finalizado.\n\n"
        "Clique no botão abaixo para avaliar o atendimento.\n\n"
        "Após sua avaliação, este ticket será encerrado automaticamente."
    )

    embed = discord.Embed(
        title=titulo,
        description=texto,
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Campany • Sua opinião é muito importante ❤️")

    # Atualiza o painel principal e bloqueia ações depois do encerramento.
    embed_ticket = interaction.message.embeds[0].copy() if interaction.message.embeds else None
    if embed_ticket is not None:
        linhas = (embed_ticket.description or "").splitlines()
        status_atualizado = False
        for indice, linha in enumerate(linhas):
            if linha.startswith("📌 **Status:**"):
                linhas[indice] = "📌 **Status:** 🔴 Fechado"
                status_atualizado = True
                break
        if not status_atualizado:
            linhas.append("📌 **Status:** 🔴 Fechado")
        embed_ticket.description = "\n".join(linhas)
        embed_ticket.color = discord.Color.dark_grey()

    for item in view.children:
        item.disabled = True

    await interaction.response.edit_message(
        embed=embed_ticket,
        view=view,
    )
    await interaction.followup.send(
        "✅ Ticket encerrado. Aguardando a avaliação do cliente.",
        ephemeral=True,
    )
    await interaction.channel.send(
        content=cliente.mention if cliente else f"<@{cliente_id}>",
        embed=embed,
        view=AvaliacaoView(),
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )


async def _alterar_status_suporte(
    interaction: discord.Interaction,
    view: discord.ui.View,
    status: str,
    texto_status: str,
    cor: discord.Colour,
    button: discord.ui.Button | None = None,
):
    if not await is_staff(interaction):
        return await interaction.response.send_message(
            "❌ Apenas a equipe de suporte pode alterar o status deste ticket.",
            ephemeral=True,
        )

    ticket = await buscar_ticket(interaction.channel.id)
    if ticket is None:
        return await interaction.response.send_message(
            "❌ Ticket não encontrado.",
            ephemeral=True,
        )

    if status == "Em Atendimento":
        await assumir_ticket(interaction.channel.id, interaction.user.id)
    else:
        await atualizar_status_ticket(
            interaction.channel.id,
            status,
            staff_id=interaction.user.id,
        )

    ticket_atualizado = await buscar_ticket(interaction.channel.id)
    atendente_id = (ticket_atualizado[2] if ticket_atualizado else None) or interaction.user.id
    atendente = interaction.guild.get_member(atendente_id)
    mencao_atendente = atendente.mention if atendente else f"<@{atendente_id}>"

    embed = interaction.message.embeds[0].copy() if interaction.message.embeds else discord.Embed(
        title="🎫 Ticket de Suporte"
    )
    linhas = (embed.description or "").splitlines()
    status_atualizado = False
    atendente_atualizado = False

    for indice, linha in enumerate(linhas):
        if linha.startswith("📌 **Status:**"):
            linhas[indice] = f"📌 **Status:** {texto_status}"
            status_atualizado = True
        elif linha.startswith("👮 **Atendente:**"):
            linhas[indice] = f"👮 **Atendente:** {mencao_atendente}"
            atendente_atualizado = True

    if not status_atualizado:
        linhas.append(f"📌 **Status:** {texto_status}")
    if not atendente_atualizado:
        linhas.append(f"👮 **Atendente:** {mencao_atendente}")

    embed.description = "\n".join(linhas)
    embed.color = cor
    if button is not None:
        button.disabled = True
        button.label = "✅ Atendimento assumido"

    await interaction.response.edit_message(embed=embed, view=view)
    await interaction.followup.send(
        f"✅ Status atualizado: **{status}**.",
        ephemeral=True,
    )


class TicketButtons(discord.ui.View):

    def __init__(self, vip_aplicado: bool = False):
        super().__init__(timeout=None)
        if vip_aplicado:
            for item in self.children:
                if getattr(item, "custom_id", None) == "usar_vip":
                    item.disabled = True
                    item.label = "👑 VIP Já Aplicado"

    @discord.ui.button(
        label="👮 Assumir Atendimento",
        style=discord.ButtonStyle.blurple,
        custom_id="assumir_ticket"
    )
    async def assumir(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode assumir tickets.",
                ephemeral=True
            )

        await assumir_ticket(
            interaction.channel.id,
            interaction.user.id
        )

        if interaction.message.embeds:

            embed = interaction.message.embeds[0]

            if embed.description:

                embed.description = (
                    embed.description
                    .replace(
                        "🟢 Aguardando atendimento",
                        "🟡 Em Atendimento"
                    )
                    .replace(
                        "Nenhum",
                        interaction.user.mention
                    )
                )

            button.disabled = True

            await interaction.response.edit_message(
                embed=embed,
                view=self
            )

        else:

            await interaction.response.send_message(
                "✅ Atendimento assumido.",
                ephemeral=True
            )

    @discord.ui.button(
        label="👑 Usar VIP",
        style=discord.ButtonStyle.secondary,
        custom_id="usar_vip"
    )
    async def usar_vip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode usar este botão.",
                ephemeral=True
            )

        ticket = await buscar_ticket(interaction.channel.id)

        if ticket is None:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        cliente = interaction.guild.get_member(ticket[1])
        if cliente is None:
            try:
                cliente = await interaction.guild.fetch_member(ticket[1])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                cliente = None

        if cliente is None:
            return await interaction.response.send_message(
                "❌ Cliente não encontrado.",
                ephemeral=True
            )

        config = await obter_configuracoes()
        vip_role_id = int(config.get("vip_role_id", 0) or 0)
        cargo_vip = interaction.guild.get_role(vip_role_id) if vip_role_id else None

        if cargo_vip not in cliente.roles:
            return await interaction.response.send_message(
                "❌ Este cliente não possui VIP.",
                ephemeral=True
            )

        metodo = ticket[12] if len(ticket) > 12 and ticket[12] else "Outro"
        if metodo != "Grupo":
            return await interaction.response.send_message(
                "❌ O desconto VIP é válido somente para compras por Grupo.",
                ephemeral=True
            )

        # O desconto e o uso mensal ficam vinculados ao ticket. Se a calculadora
        # já contabilizou o uso, ou se a Staff já aplicou antes, não há nova cobrança.
        if (len(ticket) > 9 and bool(ticket[9])) or (len(ticket) > 14 and bool(ticket[14])):
            button.disabled = True
            button.label = "👑 VIP Já Aplicado"
            await interaction.response.edit_message(view=self)
            return await interaction.followup.send(
                "✅ O desconto VIP deste ticket já foi aplicado e contabilizado. Um novo uso só poderá ocorrer em outro ticket, respeitando o limite mensal.",
                ephemeral=True,
            )

        config = await obter_configuracoes()
        limite = int(config.get("vip_uses_per_month", 2))
        desconto_dec, total_dec = calcular_desconto_vip(Decimal(str(ticket[6])), config)
        novo_valor = float(total_dec)
        resultado = await aplicar_desconto_vip_ticket_atomic(
            canal_id=interaction.channel.id,
            novo_valor=novo_valor,
            desconto=float(desconto_dec),
            limite=limite,
        )

        if resultado == "limit_reached":
            usos = await obter_usos(cliente.id)
            return await interaction.response.send_message(
                f"❌ Este cliente já utilizou os {limite} descontos disponíveis neste mês ({usos}/{limite}).",
                ephemeral=True,
            )
        if resultado == "already_used":
            button.disabled = True
            button.label = "👑 VIP Já Aplicado"
            await interaction.response.edit_message(view=self)
            return await interaction.followup.send("✅ O uso VIP deste ticket já havia sido contabilizado.", ephemeral=True)
        if resultado != "applied":
            return await interaction.response.send_message("❌ Não foi possível atualizar este ticket. Atualize a página e tente novamente.", ephemeral=True)

        button.disabled = True
        button.label = "👑 VIP Utilizado"
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if embed is not None:
            for index, field in enumerate(embed.fields):
                if field.name in {"💰 Valor do pedido", "Valor do pedido", "💰 Total"}:
                    embed.set_field_at(index, name=field.name, value=formatar_reais(novo_valor), inline=field.inline)
                    break
            embed.add_field(name="👑 Desconto VIP aplicado pela Staff", value=f"-{formatar_reais(float(desconto_dec))}", inline=True)
        await interaction.response.edit_message(embed=embed, view=self)
        # O PIX original foi enviado na abertura do ticket; reenvia as instruções
        # com o novo total para que o cliente não pague o valor sem desconto.
        await enviar_pix_automatico(
            interaction.channel,
            config,
            novo_valor,
            metodo,
            atualizacao=True,
        )
        await interaction.followup.send(
            f"✅ Desconto VIP aplicado e contabilizado neste ticket.\nValor atualizado: **{formatar_reais(novo_valor)}**. As instruções PIX atualizadas foram enviadas no canal.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="✅ Cliente",
        style=discord.ButtonStyle.green,
        custom_id="cliente_ticket"
    )
    async def cliente(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode usar este botão.",
                ephemeral=True
            )

        ticket = await buscar_ticket(interaction.channel.id)

        if ticket is None:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            RegistrarVenda(
                robux=ticket[5],
                valor=ticket[6]
            )
        )

    @discord.ui.button(
        label="❌ Não Cliente",
        style=discord.ButtonStyle.red,
        custom_id="nao_cliente_ticket"
    )
    async def nao_cliente(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff.",
                ephemeral=True
            )

        await fechar_ticket(interaction.channel.id)

        await interaction.response.send_message(
            "❌ Ticket será fechado em 3 segundos...",
            ephemeral=True
        )

        await asyncio.sleep(3)

        await interaction.channel.delete()

    @discord.ui.button(
        label="🔒 Fechar Ticket",
        style=discord.ButtonStyle.gray,
        custom_id="fechar_ticket"
    )
    async def fechar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode fechar tickets.",
                ephemeral=True,
            )
        await _finalizar_ticket_com_avaliacao(interaction, self)


class SupportTicketButtons(discord.ui.View):
    """Controles específicos para tickets da categoria Suporte Técnico."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Assumir Atendimento",
        emoji="👮",
        style=discord.ButtonStyle.primary,
        custom_id="support_assumir_ticket",
        row=0,
    )
    async def assumir(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await _alterar_status_suporte(
            interaction,
            self,
            status="Em Atendimento",
            texto_status="🟡 Em Atendimento",
            cor=discord.Color.blurple(),
            button=button,
        )

    @discord.ui.button(
        label="Aguardar Cliente",
        emoji="⏳",
        style=discord.ButtonStyle.secondary,
        custom_id="support_aguardar_cliente",
        row=0,
    )
    async def aguardar_cliente(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await _alterar_status_suporte(
            interaction,
            self,
            status="Aguardando Cliente",
            texto_status="🟠 Aguardando cliente",
            cor=discord.Color.orange(),
        )

    @discord.ui.button(
        label="Em Análise",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        custom_id="support_em_analise",
        row=0,
    )
    async def em_analise(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await _alterar_status_suporte(
            interaction,
            self,
            status="Em Análise",
            texto_status="🔵 Em análise",
            cor=discord.Color.blue(),
        )

    @discord.ui.button(
        label="Marcar como Resolvido",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="support_resolvido",
        row=1,
    )
    async def resolvido(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await _alterar_status_suporte(
            interaction,
            self,
            status="Resolvido",
            texto_status="🟢 Resolvido",
            cor=discord.Color.green(),
        )

    @discord.ui.button(
        label="Fechar Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="support_fechar_ticket",
        row=1,
    )
    async def fechar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a equipe de suporte pode fechar tickets.",
                ephemeral=True,
            )
        await _finalizar_ticket_com_avaliacao(interaction, self)
