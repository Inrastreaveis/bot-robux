import asyncio
import discord

from utils.permissions import is_staff

from database.tickets import (
    assumir_ticket,
    buscar_ticket,
    registrar_fechamento,
    fechar_ticket
)

from views.avaliacao import AvaliacaoView


class TicketButtons(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Assumir Atendimento",
        emoji="👮",
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

    @discord.ui.button(
        label="Cliente",
        emoji="✅",
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

        ticket = await buscar_ticket(
            interaction.channel.id
        )

        if ticket is None:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        from views.modal_venda import RegistrarVenda

        await interaction.response.send_modal(
            RegistrarVenda(
                robux=ticket[5],
                valor=ticket[6]
            )
        )

    @discord.ui.button(
        label="Não Cliente",
        emoji="❌",
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
                "❌ Apenas a Staff pode usar este botão.",
                ephemeral=True
            )

        await fechar_ticket(
            interaction.channel.id
        )

        await interaction.response.send_message(
            "❌ Ticket será fechado em 3 segundos.",
            ephemeral=True
        )

        await asyncio.sleep(3)

        await interaction.channel.delete()

    @discord.ui.button(
        label="Fechar Ticket",
        emoji="🔒",
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
                ephemeral=True
            )

        await registrar_fechamento(
            interaction.channel.id,
            interaction.user.id
        )

        cliente = None

        if (
            interaction.channel.topic
            and interaction.channel.topic.isdigit()
        ):
            cliente = interaction.guild.get_member(
                int(interaction.channel.topic)
            )

        if cliente:
            await interaction.channel.set_permissions(
                cliente,
                send_messages=True,
                add_reactions=True,
                read_message_history=True
            )

        embed = discord.Embed(
            title="⭐ Avaliação do Atendimento",
            description=(
                "Seu atendimento foi encerrado.\n\n"
                "Clique no botão abaixo para avaliar o atendimento.\n\n"
                "Após enviar sua avaliação este ticket será apagado automaticamente."
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(
            text="Campany • Obrigado pela preferência ❤️"
        )

        await interaction.response.defer()

        await interaction.channel.send(
            content=cliente.mention if cliente else None,
            embed=embed,
            view=AvaliacaoView()
        )
