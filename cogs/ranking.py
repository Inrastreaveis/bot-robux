import discord
from discord import app_commands
from discord.ext import commands

from database.database import get_db, obter_ranking
from utils.permissions import is_staff


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ranking",
        description="Mostra o ranking dos clientes."
    )
    async def ranking(self, interaction: discord.Interaction):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Você não possui permissão para usar este comando.",
                ephemeral=True
            )

        db = await get_db()
        ranking = await obter_ranking(db)
        await db.close()

        if not ranking:
            return await interaction.response.send_message(
                "📭 Nenhum cliente encontrado.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🏆 Ranking de Clientes",
            color=discord.Color.gold()
        )

        medalhas = ["🥇", "🥈", "🥉"]

        for i, cliente in enumerate(ranking):
            user_id, nome, total_gasto, robux, compras = cliente

            membro = interaction.guild.get_member(user_id)

            if membro:
                nome = membro.display_name
            else:
                nome = nome or f"Usuário {user_id}"

            medalha = medalhas[i] if i < 3 else f"**{i+1}.**"

            embed.add_field(
                name=f"{medalha} {nome}",
                value=(
                    f"💰 **Total gasto:** R$ {total_gasto:.2f}\n"
                    f"💎 **Robux:** {robux:,}\n"
                    f"🛒 **Compras:** {compras}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Ranking(bot))
