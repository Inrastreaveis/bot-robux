
import discord
from pathlib import Path
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

        # Confirma a interação com o Discord
        await interaction.response.defer(ephemeral=True)

        # Verifica permissão de Staff
        if not await is_staff(interaction):
            return await interaction.followup.send(
                "❌ Você não possui permissão.",
                ephemeral=True
            )

        # Carrega as configurações do bot
        config = await obter_configuracoes()

        embed = discord.Embed(
            title=config.get(
                "panel_title",
                "🛒 Atendimento Campany"
            ),
            description=config.get(
                "panel_description",
                "Escolha uma opção abaixo."
            ),
            color=discord.Color.blue()
        )

        # Localiza a imagem personalizada
        image_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "campany-store.png"
        )

        # Verifica se a imagem existe
        if not image_path.is_file():
            return await interaction.followup.send(
                "❌ Imagem não encontrada em assets/campany-store.png.",
                ephemeral=True
            )

        # Adiciona a imagem ao painel
        embed.set_image(
            url="attachment://campany-store.png"
        )

        embed.set_footer(
            text="Campany • Atendimento Automático"
        )

        # Envia o painel com a imagem e os botões originais
        with discord.File(
            str(image_path),
            filename="campany-store.png"
        ) as arquivo:

            await interaction.channel.send(
                embed=embed,
                view=AbrirTicket(),
                file=arquivo
            )

        # Confirma o envio
        await interaction.followup.send(
            "✅ Painel enviado com sucesso!",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
