import discord
from discord import app_commands
from discord.ext import commands

from database.database import get_db, buscar_venda
from utils.permissions import is_staff
from views.confirmar_exclusao import ConfirmarExclusao


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="vendainfo",
        description="Consulta uma venda pelo ID."
    )
    @app_commands.describe(id="ID da venda")
    async def venda_info(
        self,
        interaction: discord.Interaction,
        id: int
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Você não possui permissão.",
                ephemeral=True
            )

        db = await get_db()

        venda = await buscar_venda(db, id)

        await db.close()

        if venda is None:
            return await interaction.response.send_message(
                "❌ Venda não encontrada.",
                ephemeral=True
            )

        (
            venda_id,
            user_id,
            staff_id,
            valor,
            robux,
            pagamento,
            observacao,
            data
        ) = venda

        cliente = interaction.guild.get_member(user_id)
        vendedor = interaction.guild.get_member(staff_id)

        cliente_nome = cliente.display_name if cliente else str(user_id)
        vendedor_nome = vendedor.display_name if vendedor else str(staff_id)

        embed = discord.Embed(
            title=f"🧾 Venda #{venda_id}",
            color=discord.Color.green()
        )

        embed.add_field(name="👤 Cliente", value=cliente_nome, inline=True)
        embed.add_field(name="👮 Vendedor", value=vendedor_nome, inline=True)
        embed.add_field(name="💰 Valor", value=f"R$ {valor:.2f}", inline=False)
        embed.add_field(name="💎 Robux", value=f"{robux:,}", inline=True)
        embed.add_field(name="💳 Pagamento", value=pagamento, inline=True)
        embed.add_field(name="📅 Data", value=data, inline=False)

        if observacao:
            embed.add_field(
                name="📝 Observação",
                value=observacao,
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="deletarvenda",
        description="Exclui uma venda pelo ID."
    )
    @app_commands.describe(id="ID da venda")
    async def deletar_venda(
        self,
        interaction: discord.Interaction,
        id: int
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Você não possui permissão.",
                ephemeral=True
            )

        db = await get_db()
        venda = await buscar_venda(db, id)
        await db.close()

        if venda is None:
            return await interaction.response.send_message(
                "❌ Venda não encontrada.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="⚠️ Confirmar exclusão",
            description=(
                f"Você tem certeza que deseja excluir a venda **#{id}**?\n\n"
                "Essa ação não pode ser desfeita."
            ),
            color=discord.Color.red()
        )

        await interaction.response.send_message(
            embed=embed,
            view=ConfirmarExclusao(id),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Admin(bot))
