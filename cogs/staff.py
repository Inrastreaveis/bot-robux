import discord
from discord.ext import commands
from discord import app_commands

from database.database import get_db, obter_ranking_staff
from utils.permissions import is_staff


class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="staff",
        description="Mostra o ranking da equipe."
    )
    async def staff(self, interaction: discord.Interaction):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Você não possui permissão.",
                ephemeral=True
            )

        db = await get_db()

        try:
            ranking = await obter_ranking_staff(db)

            if not ranking:
                return await interaction.response.send_message(
                    "📭 Nenhum membro da staff encontrado.",
                    ephemeral=True
                )

            embed = discord.Embed(
                title="👮 Ranking da Staff",
                color=discord.Color.blue()
            )

            medalhas = ["🥇", "🥈", "🥉"]

            for i, staff in enumerate(ranking):
                user_id, nome, vendas, robux, total = staff

                membro = interaction.guild.get_member(user_id)

                if membro:
                    nome = membro.display_name

                posicao = medalhas[i] if i < 3 else f"🏅 {i + 1}º"

                embed.add_field(
                    name=f"{posicao} {nome}",
                    value=(
                        f"🛒 **Vendas:** {vendas}\n"
                        f"💎 **Robux:** {robux:,}".replace(",", ".")
                        + f"\n💰 **Total:** R$ {total:.2f}".replace(".", ",")
                    ),
                    inline=False
                )

            embed.set_footer(
                text="Campany • Ranking da Staff"
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        finally:
            await db.close()


async def setup(bot):
    await bot.add_cog(Staff(bot))
