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

        # Imagem personalizada do painel (arquivo enviado junto ao projeto).
        image_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "campany-store.png"
        )

        if not image_path.is_file():
            return await interaction.response.send_message(
                "❌ A imagem do painel não foi encontrada em assets/campany-store.png.",
                ephemeral=True
            )

        embed.set_image(url="attachment://campany-store.png")
        embed.set_footer(
            text="Campany • Atendimento Automático"
        )

        with discord.File(image_path, filename="campany-store.png") as image_file:
            await interaction.channel.send(
                embed=embed,
                view=AbrirTicket(),
                file=image_file
            )

        await interaction.response.send_message(
            "✅ Painel enviado com sucesso.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
