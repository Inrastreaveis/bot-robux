import asyncio
from datetime import datetime

import discord

from config import CANAL_AVALIACOES
from database.configuracoes import obter_configuracoes
from database.database import (
    get_db,
    registrar_avaliacao,
    avaliacao_existe,
)
from database.tickets import buscar_ticket, fechar_ticket


async def _buscar_membro(guild: discord.Guild, user_id: int | None):
    if not user_id:
        return None

    membro = guild.get_member(int(user_id))
    if membro is not None:
        return membro

    try:
        return await guild.fetch_member(int(user_id))
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def _buscar_canal_avaliacoes(
    guild: discord.Guild,
    ticket_suporte: bool,
):
    """Usa o canal configurado para suporte e mantém o canal antigo para compras."""
    canal_id = CANAL_AVALIACOES

    if ticket_suporte:
        config = await obter_configuracoes()
        canal_configurado = int(config.get("support_reviews_channel_id", 0) or 0)
        if canal_configurado:
            canal_id = canal_configurado

    canal = guild.get_channel(canal_id) if canal_id else None
    if canal is None and canal_id:
        try:
            canal = await guild.fetch_channel(canal_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            canal = None

    # Se o canal exclusivo de suporte foi removido, tenta o canal de avaliações antigo.
    if canal is None and ticket_suporte and CANAL_AVALIACOES:
        canal = guild.get_channel(CANAL_AVALIACOES)
        if canal is None:
            try:
                canal = await guild.fetch_channel(CANAL_AVALIACOES)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                canal = None

    return canal


class ComentarioModal(discord.ui.Modal):
    def __init__(self, estrelas: int):
        super().__init__(title="⭐ Avaliação do Atendimento")
        self.estrelas = estrelas

        self.comentario = discord.ui.TextInput(
            label="Comentário",
            placeholder="Conte como foi seu atendimento...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )
        self.add_item(self.comentario)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        db = await get_db()

        try:
            if interaction.guild is None or interaction.channel is None:
                return await interaction.followup.send(
                    "❌ Não foi possível identificar o servidor ou ticket.",
                    ephemeral=True,
                )

            ticket = await buscar_ticket(interaction.channel.id)
            if ticket is None:
                return await interaction.followup.send(
                    "❌ Não foi possível localizar os dados deste ticket.",
                    ephemeral=True,
                )

            (
                canal_id,
                cliente_id,
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
            ) = ticket[:12]

            if interaction.user.id != int(cliente_id):
                return await interaction.followup.send(
                    "❌ Somente o cliente que abriu este ticket pode enviar a avaliação.",
                    ephemeral=True,
                )

            if await avaliacao_existe(db, canal_id):
                return await interaction.followup.send(
                    "ℹ️ Este ticket já recebeu uma avaliação. Obrigado!",
                    ephemeral=True,
                )

            categoria_texto = str(categoria or "Atendimento")
            ticket_suporte = "suporte" in categoria_texto.casefold()
            cliente = await _buscar_membro(interaction.guild, cliente_id)
            atendente = await _buscar_membro(interaction.guild, staff_id)
            fechou = await _buscar_membro(interaction.guild, fechado_por)
            canal_avaliacoes = await _buscar_canal_avaliacoes(
                interaction.guild,
                ticket_suporte,
            )

            estrelas_texto = "⭐" * self.estrelas
            titulo = "⭐ Nova Avaliação de Suporte" if ticket_suporte else "⭐ Nova Avaliação"
            embed = discord.Embed(
                title=titulo,
                description="Uma nova avaliação foi enviada.",
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )
            embed.add_field(
                name="👤 Cliente",
                value=cliente.mention if cliente else f"`{cliente_id}`",
                inline=False,
            )
            embed.add_field(
                name="👮 Atendente",
                value=atendente.mention if atendente else "Não informado",
                inline=False,
            )
            embed.add_field(
                name="🔒 Ticket fechado por",
                value=fechou.mention if fechou else "Não informado",
                inline=False,
            )

            if ticket_suporte:
                embed.add_field(
                    name="🛠️ Tipo de atendimento",
                    value=discord.utils.escape_markdown(categoria_texto),
                    inline=False,
                )
            else:
                embed.add_field(
                    name="🪙 Robux",
                    value=f"{int(robux or 0):,}".replace(",", "."),
                    inline=True,
                )
                embed.add_field(
                    name="💰 Valor",
                    value=f"R$ {float(valor or 0):.2f}".replace(".", ","),
                    inline=True,
                )

            embed.add_field(
                name="⭐ Avaliação",
                value=f"{estrelas_texto} ({self.estrelas}/5)",
                inline=False,
            )
            embed.add_field(
                name="💬 Comentário",
                value=discord.utils.escape_mentions(
                    self.comentario.value or "*Nenhum comentário.*"
                ),
                inline=False,
            )
            embed.set_footer(text="Campany • Sistema de Avaliações")

            await registrar_avaliacao(
                db=db,
                canal_id=canal_id,
                cliente_id=cliente_id,
                atendente_id=staff_id,
                fechado_por=fechado_por,
                robux=robux or 0,
                valor=valor or 0,
                estrelas=self.estrelas,
                comentario=self.comentario.value or "",
                data=datetime.now().strftime("%d/%m/%Y %H:%M"),
                categoria="Suporte Técnico" if ticket_suporte else categoria_texto,
            )

            enviado = False
            if canal_avaliacoes is not None:
                try:
                    await canal_avaliacoes.send(embed=embed)
                    enviado = True
                except discord.HTTPException:
                    enviado = False

            await fechar_ticket(canal_id)

            if enviado:
                mensagem = "❤️ Obrigado pela sua avaliação! Seu feedback foi enviado com sucesso."
            else:
                mensagem = (
                    "❤️ Obrigado pela sua avaliação! Ela foi registrada no sistema, "
                    "mas a equipe precisa verificar a configuração do canal de avaliações."
                )

            await interaction.followup.send(
                mensagem + "\n\nEste ticket será apagado em **5 segundos**.",
                ephemeral=True,
            )
            await asyncio.sleep(5)
            await interaction.channel.delete(reason="Ticket avaliado pelo cliente")

        finally:
            await db.close()


class EstrelasView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def abrir_modal(
        self,
        interaction: discord.Interaction,
        estrelas: int,
    ):
        await interaction.response.send_modal(ComentarioModal(estrelas))

    @discord.ui.button(
        label="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="estrela_1",
    )
    async def um(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, 1)

    @discord.ui.button(
        label="⭐⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="estrela_2",
    )
    async def dois(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, 2)

    @discord.ui.button(
        label="⭐⭐⭐",
        style=discord.ButtonStyle.primary,
        custom_id="estrela_3",
    )
    async def tres(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, 3)

    @discord.ui.button(
        label="⭐⭐⭐⭐",
        style=discord.ButtonStyle.success,
        custom_id="estrela_4",
    )
    async def quatro(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, 4)

    @discord.ui.button(
        label="⭐⭐⭐⭐⭐",
        style=discord.ButtonStyle.success,
        custom_id="estrela_5",
    )
    async def cinco(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, 5)


class AvaliacaoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="⭐ Avaliar Atendimento",
        custom_id="avaliar_atendimento",
        style=discord.ButtonStyle.success,
    )
    async def avaliar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None or interaction.channel is None:
            return await interaction.response.send_message(
                "❌ Não foi possível identificar este ticket.",
                ephemeral=True,
            )

        ticket = await buscar_ticket(interaction.channel.id)
        if ticket is None:
            return await interaction.response.send_message(
                "❌ Este ticket não está mais disponível para avaliação.",
                ephemeral=True,
            )

        if interaction.user.id != int(ticket[1]):
            return await interaction.response.send_message(
                "❌ Somente o cliente que abriu o ticket pode avaliá-lo.",
                ephemeral=True,
            )

        ticket_suporte = "suporte" in str(ticket[4] or "").casefold()
        titulo = "⭐ Avaliação do Suporte" if ticket_suporte else "⭐ Avaliação do Atendimento"
        descricao = (
            "Como foi sua experiência com nossa equipe de suporte?\n\n"
            "Escolha uma nota de 1 a 5 estrelas e deixe um comentário, se desejar."
            if ticket_suporte
            else "Obrigado por comprar na **Campany**!\n\n"
            "Escolha uma quantidade de estrelas abaixo e deixe um comentário sobre seu atendimento."
        )

        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Sua opinião é muito importante para nós.")

        await interaction.response.send_message(
            embed=embed,
            view=EstrelasView(),
            ephemeral=False,
        )
