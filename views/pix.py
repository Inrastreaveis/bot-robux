"""Botões para disponibilizar a cópia das chaves PIX no Discord.

O Discord não permite que bots escrevam diretamente na área de transferência
do usuário. O botão responde em mensagem privada com a chave em bloco de código,
que oferece a cópia nativa no computador e a seleção/cópia por toque no celular.
"""

import re

import discord


class PixCopyView(discord.ui.View):
    def __init__(self, indices_chaves=None):
        # timeout=None + custom_id fixo permite manter os botões após reinícios.
        super().__init__(timeout=None)

        if indices_chaves is not None:
            indices_ativos = {int(indice) for indice in indices_chaves}
            for item in self.children:
                indice = 1 if item.custom_id == "campany:copiar_pix:1" else 2
                item.disabled = indice not in indices_ativos

    async def _enviar_chave(self, interaction: discord.Interaction, indice: int):
        conteudo = interaction.message.content if interaction.message else ""
        padrao = rf"\*\*Chave PIX {indice}:\*\*\s*```(.*?)```"
        resultado = re.search(padrao, conteudo or "", flags=re.DOTALL)

        if not resultado:
            return await interaction.response.send_message(
                "❌ Não consegui localizar esta chave PIX na mensagem. "
                "Peça à equipe para reenviar os dados de pagamento.",
                ephemeral=True,
            )

        chave = resultado.group(1).strip()
        if not chave:
            return await interaction.response.send_message(
                "❌ Esta chave PIX está vazia. Peça ajuda à equipe.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            f"📋 **Chave PIX {indice} — copie abaixo:**\n```{chave}```",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @discord.ui.button(
        label="Copiar PIX 1",
        emoji="📋",
        style=discord.ButtonStyle.primary,
        custom_id="campany:copiar_pix:1",
    )
    async def copiar_pix_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._enviar_chave(interaction, 1)

    @discord.ui.button(
        label="Copiar PIX 2",
        emoji="📋",
        style=discord.ButtonStyle.primary,
        custom_id="campany:copiar_pix:2",
    )
    async def copiar_pix_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._enviar_chave(interaction, 2)
