
import discord
import asyncio
import logging
from pathlib import Path
from discord.ext import commands
from discord import app_commands

from views.painel import AbrirTicket
from utils.permissions import is_staff
from database.configuracoes import obter_configuracoes
from database.tickets import buscar_ticket
from utils.ticket_support import PURCHASE_METHODS, eh_anexo_comprovante, mencoes_administracao


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

            enabled_methods = config.get("enabled_methods", {})
            korblox_enabled = bool(enabled_methods.get("Korblox", True))

            descricao_painel = config.get(
                "panel_description",
                "Escolha uma opção abaixo."
            )

            # Esconde a linha de Korblox da descrição quando o botão estiver desativado.
            if not korblox_enabled:
                descricao_painel = "\n".join(
                    linha
                    for linha in descricao_painel.splitlines()
                    if not (
                        "comprar" in linha.casefold()
                        and "korblox" in linha.casefold()
                    )
                ).strip()

            embed = discord.Embed(
                title=config.get(
                    "panel_title",
                    "🛒 Atendimento Campany"
                ),
                description=descricao_painel,
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

            view = AbrirTicket(korblox_enabled=korblox_enabled)

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


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Notifica os dois responsáveis quando o cliente envia comprovante no ticket de compra."""
        if message.author.bot or message.guild is None or not message.attachments:
            return

        try:
            ticket = await buscar_ticket(message.channel.id)
            if ticket is None:
                return

            cliente_id = int(ticket[1])
            metodo = ticket[12] if len(ticket) > 12 and ticket[12] else "Outro"
            status = str(ticket[10] or "")
            if message.author.id != cliente_id or metodo not in PURCHASE_METHODS or status.casefold() == "fechado":
                return

            comprovantes = [anexo for anexo in message.attachments if eh_anexo_comprovante(anexo)]
            if not comprovantes:
                return

            config = await obter_configuracoes()
            mencoes, allowed_mentions = mencoes_administracao(config)
            nomes = discord.utils.escape_mentions(", ".join(anexo.filename for anexo in comprovantes)).replace("`", "")
            texto = (
                f"📎 **Comprovante recebido!**\n"
                f"Cliente: **{discord.utils.escape_mentions(message.author.display_name)}** (`{message.author.id}`)\n"
                f"Arquivo(s): `{nomes[:500]}`\n"
                f"{mencoes}"
            ).strip()
            await message.channel.send(content=texto, allowed_mentions=allowed_mentions)
        except Exception:
            logger.exception("[TICKETS] Erro ao processar possível comprovante enviado no ticket.")



async def setup(bot):
    await bot.add_cog(Tickets(bot))
