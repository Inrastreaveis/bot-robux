import discord
from discord.ext import commands
from discord import app_commands

from database.database import get_db, obter_estatisticas
from utils.permissions import is_staff


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="stats",
        description="Mostra as estatísticas da loja."
    )
    async def stats(self, interaction: discord.Interaction):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Você não possui permissão.",
                ephemeral=True
            )

        db = await get_db()

        try:
            stats = await obter_estatisticas(db)

            embed = discord.Embed(
                title="📊 Estatísticas da Loja",
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="💰 Valor Total",
                value=f"R$ {stats['valor_total']:.2f}".replace(".", ","),
                inline=True
            )

            embed.add_field(
                name="💎 Robux Vendidos",
                value=f"{stats['robux_total']:,}".replace(",", "."),
                inline=True
            )

            embed.add_field(
                name="🛒 Vendas",
                value=str(stats["total_vendas"]),
                inline=True
            )

            embed.add_field(
                name="👥 Clientes",
                value=str(stats["clientes"]),
                inline=True
            )

            embed.add_field(
                name="📈 Ticket Médio",
                value=f"R$ {stats['ticket_medio']:.2f}".replace(".", ","),
                inline=True
            )

            embed.add_field(
                name="🏆 Maior Venda",
                value=f"R$ {stats['maior_venda']:.2f}".replace(".", ","),
                inline=True
            )

            embed.set_footer(
                text="Campany • Sistema de Estatísticas"
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        finally:
            await db.close()


async def setup(bot):
    await bot.add_cog(Stats(bot))
