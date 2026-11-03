import asyncio
from datetime import datetime

import discord

from config import CANAL_AVALIACOES

from database.database import (
    get_db,
    registrar_avaliacao
)

from database.tickets import (
    buscar_ticket,
    fechar_ticket
)


class ComentarioModal(discord.ui.Modal):

    def __init__(self, estrelas: int):
        super().__init__(title="⭐ Avaliação do Atendimento")

        self.estrelas = estrelas

        self.comentario = discord.ui.TextInput(
            label="Comentário",
            placeholder="Conte como foi seu atendimento...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )

        self.add_item(self.comentario)

    async def on_submit(self, interaction: discord.Interaction):

        db = await get_db()

        try:

            ticket = await buscar_ticket(
                interaction.channel.id
            )

            if ticket is None:

                return await interaction.response.send_message(
                    "❌ Não foi possível localizar os dados deste ticket.",
                    ephemeral=True
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
                criado_em
            ) = ticket[:12]

            cliente = interaction.guild.get_member(cliente_id)
            atendente = interaction.guild.get_member(staff_id)
            fechou = interaction.guild.get_member(fechado_por)

            canal_avaliacoes = interaction.guild.get_channel(
                CANAL_AVALIACOES
            )

            estrelas = "⭐" * self.estrelas

            embed = discord.Embed(
                title="⭐ Nova Avaliação",
                description="Uma nova avaliação foi enviada.",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            embed.add_field(
                name="👤 Cliente",
                value=cliente.mention if cliente else f"`{cliente_id}`",
                inline=False
            )

            embed.add_field(
                name="👮 Atendente",
                value=atendente.mention if atendente else f"`{staff_id}`",
                inline=False
            )

            embed.add_field(
                name="🔒 Ticket fechado por",
                value=fechou.mention if fechou else "Não informado",
                inline=False
            )

            embed.add_field(
                name="🪙 Robux",
                value=f"{robux:,}".replace(",", "."),
                inline=True
            )

            embed.add_field(
                name="💰 Valor",
                value=f"R$ {valor:.2f}".replace(".", ","),
                inline=True
            )

            embed.add_field(
                name="⭐ Avaliação",
                value=f"{estrelas} ({self.estrelas}/5)",
                inline=False
            )

            embed.add_field(
                name="💬 Comentário",
                value=self.comentario.value or "*Nenhum comentário.*",
                inline=False
            )

            embed.set_footer(
                text="Campany • Sistema de Avaliações"
            )

            await registrar_avaliacao(
                db=db,
                canal_id=canal_id,
                cliente_id=cliente_id,
                atendente_id=staff_id,
                fechado_por=fechado_por,
                robux=robux,
                valor=valor,
                estrelas=self.estrelas,
                comentario=self.comentario.value or "",
                data=datetime.now().strftime("%d/%m/%Y %H:%M")
            )

            if canal_avaliacoes:
                await canal_avaliacoes.send(embed=embed)

            await fechar_ticket(canal_id)

            await interaction.response.send_message(
                "❤️ Obrigado pela sua avaliação!\n\n"
                "Este ticket será apagado em **10 segundos**.",
                ephemeral=False
            )

            await asyncio.sleep(10)

            await interaction.channel.delete()

        finally:

            await db.close()

class EstrelasView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def abrir_modal(
        self,
        interaction: discord.Interaction,
        estrelas: int
    ):
        await interaction.response.send_modal(
            ComentarioModal(estrelas)
        )

    @discord.ui.button(
        label="⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="estrela_1"
    )
    async def um(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.abrir_modal(interaction, 1)

    @discord.ui.button(
        label="⭐⭐",
        style=discord.ButtonStyle.secondary,
        custom_id="estrela_2"
    )
    async def dois(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.abrir_modal(interaction, 2)

    @discord.ui.button(
        label="⭐⭐⭐",
        style=discord.ButtonStyle.primary,
        custom_id="estrela_3"
    )
    async def tres(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.abrir_modal(interaction, 3)

    @discord.ui.button(
        label="⭐⭐⭐⭐",
        style=discord.ButtonStyle.success,
        custom_id="estrela_4"
    )
    async def quatro(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.abrir_modal(interaction, 4)

    @discord.ui.button(
        label="⭐⭐⭐⭐⭐",
        style=discord.ButtonStyle.success,
        custom_id="estrela_5"
    )
    async def cinco(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.abrir_modal(interaction, 5)


class AvaliacaoView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
    label="⭐ Avaliar Atendimento",
    custom_id="avaliar_atendimento",
    style=discord.ButtonStyle.success
)
    async def avaliar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = discord.Embed(
            title="⭐ Avaliação do Atendimento",
            description=(
                "Obrigado por comprar na **Campany**!\n\n"
                "Escolha uma quantidade de estrelas abaixo e deixe um comentário."
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(
            text="Sua opinião é muito importante para nós."
        )

        await interaction.response.send_message(
            embed=embed,
            view=EstrelasView(),
            ephemeral=False
        )
