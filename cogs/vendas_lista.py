import discord
from discord.ext import commands
from discord import app_commands

from database.database import get_db, listar_vendas
from utils.permissions import is_staff


class VendasLista(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="vendas",
        description="Mostra as últimas vendas registradas."
    )
    async def vendas(self, interaction: discord.Interaction):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Você não possui permissão.",
                ephemeral=True
            )

        db = await get_db()
        vendas = await listar_vendas(db)
        await db.close()

        if not vendas:
            return await interaction.response.send_message(
                "📭 Nenhuma venda registrada.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📋 Últimas Vendas",
            color=discord.Color.blue()
        )

        for venda in vendas:

            venda_id, user_id, staff_id, valor, robux, pagamento, data = venda

            membro = interaction.guild.get_member(user_id)

            cliente = membro.display_name if membro else str(user_id)

            embed.add_field(
                name=f"🆔 Venda #{venda_id}",
                value=(
                    f"👤 **Cliente:** {cliente}\n"
                    f"💰 **Valor:** R$ {valor:.2f}\n"
                    f"💎 **Robux:** {robux:,}\n"
                    f"💳 **Pagamento:** {pagamento}\n"
                    f"📅 **Data:** {data}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(VendasLista(bot))
