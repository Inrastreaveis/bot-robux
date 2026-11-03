import discord
from discord.ext import commands
from discord import app_commands

from views.painel import AbrirTicket
from utils.permissions import is_staff
from database.configuracoes import obter_configuracoes


class Tickets(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="painel",
        description="Enviar painel de atendimento."
    )
    async def painel(self, interaction: discord.Interaction):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Você não possui permissão.",
                ephemeral=True
            )

        config = await obter_configuracoes()
        embed = discord.Embed(
            title=config.get("panel_title", "🛒 Atendimento Campany"),
            description=config.get("panel_description", "Escolha uma opção abaixo."),
            color=discord.Color.blue()
        )

        embed.set_image(
            url="https://via.placeholder.com/1000x300.png?text=Campany"
        )

        embed.set_footer(
            text="Campany • Atendimento Automático"
        )

        await interaction.channel.send(
            embed=embed,
            view=AbrirTicket()
        )

        await interaction.response.send_message(
            "✅ Painel enviado com sucesso.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
