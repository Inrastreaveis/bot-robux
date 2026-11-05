
import discord
import asyncio
import logging
from pathlib import Path
from discord.ext import commands
from discord import app_commands

from views.painel import AbrirTicket
from utils.permissions import is_staff
from database.configuracoes import obter_configuracoes


logger = logging.getLogger(__name__)


class Tickets(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="painel",
        description="Enviar painel de atendimento."
    )
    async def painel(self, interaction: discord.Interaction):

        etapa = "Iniciando comando"

        try:
            # Confirma a interação
            etapa = "Confirmando interação"
            await interaction.response.defer(
                ephemeral=True,
                thinking=True
            )

            # Verifica permissão
            etapa = "Verificando permissão de Staff"
            print(f"[PAINEL] {etapa}")

            permitido = await asyncio.wait_for(
                is_staff(interaction),
                timeout=15
            )

            if not permitido:
                await interaction.followup.send(
                    "❌ Você não possui permissão.",
                    ephemeral=True
                )
                return

            # Busca configurações
            etapa = "Carregando configurações"
            print(f"[PAINEL] {etapa}")

            config = await asyncio.wait_for(
                obter_configuracoes(),
                timeout=15
            )

            if not isinstance(config, dict):
                raise TypeError(
                    "obter_configuracoes() não retornou um dicionário."
                )

            # Cria embed
            etapa = "Montando embed"
            print(f"[PAINEL] {etapa}")

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

            # Localiza imagem
            etapa = "Localizando imagem"
            print(f"[PAINEL] {etapa}")

            image_path = (
                Path(__file__).resolve().parent.parent
                / "assets"
                / "campany-store.png"
            )

            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Imagem não encontrada: {image_path}"
                )

            embed.set_image(
                url="attachment://campany-store.png"
            )

            embed.set_footer(
                text="Campany • Atendimento Automático"
            )

            # Cria botões
            etapa = "Criando botões"
            print(f"[PAINEL] {etapa}")

            view = AbrirTicket()

            # Envia painel
            etapa = "Enviando painel no Discord"
            print(f"[PAINEL] {etapa}")

            if interaction.channel is None:
                raise RuntimeError(
                    "Não foi possível identificar o canal."
                )

            arquivo = discord.File(
                str(image_path),
                filename="campany-store.png"
            )

            try:
                await asyncio.wait_for(
                    interaction.channel.send(
                        embed=embed,
                        view=view,
                        file=arquivo
                    ),
                    timeout=30
                )
            finally:
                arquivo.close()

            # Confirma sucesso
            await interaction.followup.send(
                "✅ Painel enviado com sucesso!",
                ephemeral=True
            )

            print("[PAINEL] Painel enviado com sucesso!")

        except asyncio.TimeoutError:
            logger.exception(
                f"[PAINEL] Tempo esgotado na etapa: {etapa}"
            )

            mensagem = (
                f"⏳ O comando demorou demais na etapa: **{etapa}**."
            )

            try:
                await interaction.followup.send(
                    mensagem,
                    ephemeral=True
                )
            except discord.HTTPException:
                pass

        except Exception as erro:
            logger.exception(
                f"[PAINEL] Erro na etapa: {etapa}"
            )

            mensagem = (
                f"❌ Erro ao executar o painel.\n"
                f"**Etapa:** {etapa}\n"
                f"**Erro:** `{type(erro).__name__}`"
            )

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        mensagem,
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        mensagem,
                        ephemeral=True
                    )
            except discord.HTTPException:
                logger.exception(
                    "[PAINEL] Não foi possível responder ao Discord."
                )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
