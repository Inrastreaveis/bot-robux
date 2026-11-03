import asyncio
import discord
from decimal import Decimal


from utils.permissions import is_staff

from views.modal_venda import RegistrarVenda
from views.avaliacao import AvaliacaoView

from database.vip import pode_usar, registrar_uso, obter_usos
from database.configuracoes import obter_configuracoes
from database.tickets import atualizar_desconto_vip_ticket
from utils.calculos_robux import calcular_desconto_vip, formatar_reais
from database.tickets import (
    assumir_ticket,
    buscar_ticket,
    fechar_ticket,
    registrar_fechamento,
    atualizar_valores_ticket
)


class TicketButtons(discord.ui.View):

    def __init__(self, vip_aplicado: bool = False):
        super().__init__(timeout=None)
        if vip_aplicado:
            for item in self.children:
                if getattr(item, "custom_id", None) == "usar_vip":
                    item.disabled = True
                    item.label = "👑 VIP Já Aplicado"

    @discord.ui.button(
        label="👮 Assumir Atendimento",
        style=discord.ButtonStyle.blurple,
        custom_id="assumir_ticket"
    )
    async def assumir(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode assumir tickets.",
                ephemeral=True
            )

        await assumir_ticket(
            interaction.channel.id,
            interaction.user.id
        )

        if interaction.message.embeds:

            embed = interaction.message.embeds[0]

            if embed.description:

                embed.description = (
                    embed.description
                    .replace(
                        "🟢 Aguardando atendimento",
                        "🟡 Em Atendimento"
                    )
                    .replace(
                        "Nenhum",
                        interaction.user.mention
                    )
                )

            button.disabled = True

            await interaction.response.edit_message(
                embed=embed,
                view=self
            )

        else:

            await interaction.response.send_message(
                "✅ Atendimento assumido.",
                ephemeral=True
            )

    @discord.ui.button(
        label="👑 Usar VIP",
        style=discord.ButtonStyle.secondary,
        custom_id="usar_vip"
    )
    async def usar_vip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode usar este botão.",
                ephemeral=True
            )

        ticket = await buscar_ticket(interaction.channel.id)

        if ticket is None:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        cliente = interaction.guild.get_member(ticket[1])

        if cliente is None:
            return await interaction.response.send_message(
                "❌ Cliente não encontrado.",
                ephemeral=True
            )

        config = await obter_configuracoes()
        vip_role_id = int(config.get("vip_role_id", 0) or 0)
        cargo_vip = interaction.guild.get_role(vip_role_id) if vip_role_id else None

        if cargo_vip not in cliente.roles:
            return await interaction.response.send_message(
                "❌ Este cliente não possui VIP.",
                ephemeral=True
            )

        metodo = ticket[12] if len(ticket) > 12 and ticket[12] else "Outro"
        if metodo != "Grupo":
            return await interaction.response.send_message(
                "❌ O desconto VIP é válido somente para compras por Grupo.",
                ephemeral=True
            )

        # Se o desconto já veio aplicado pela calculadora, o uso foi contado
        # na confirmação. Não permite aplicar nem contabilizar pela segunda vez.
        if len(ticket) > 9 and bool(ticket[9]):
            button.disabled = True
            button.label = "👑 VIP Já Aplicado"
            await interaction.response.edit_message(view=self)
            return await interaction.followup.send(
                "✅ O desconto VIP já foi aplicado na calculadora e contabilizado na confirmação do pedido.",
                ephemeral=True,
            )

        if not await pode_usar(cliente.id):
            config = await obter_configuracoes()
            limite = int(config.get("vip_uses_per_month", 2))
            usos = await obter_usos(cliente.id)
            return await interaction.response.send_message(
                f"❌ Este cliente já utilizou os {limite} descontos disponíveis neste mês ({usos}/{limite}).",
                ephemeral=True
            )

        config = await obter_configuracoes()
        desconto_dec, total_dec = calcular_desconto_vip(Decimal(str(ticket[6])), config)
        novo_valor = float(total_dec)
        await atualizar_desconto_vip_ticket(
            interaction.channel.id,
            novo_valor,
            float(desconto_dec),
        )

        await registrar_uso(cliente.id)

        button.disabled = True
        button.label = "👑 VIP Utilizado"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            f"✅ Uso do desconto VIP registrado.\nValor do pedido: **{formatar_reais(novo_valor)}**",
            ephemeral=True
        )

    @discord.ui.button(
        label="✅ Cliente",
        style=discord.ButtonStyle.green,
        custom_id="cliente_ticket"
    )
    async def cliente(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode usar este botão.",
                ephemeral=True
            )

        ticket = await buscar_ticket(interaction.channel.id)

        if ticket is None:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            RegistrarVenda(
                robux=ticket[5],
                valor=ticket[6]
            )
        )

    @discord.ui.button(
        label="❌ Não Cliente",
        style=discord.ButtonStyle.red,
        custom_id="nao_cliente_ticket"
    )
    async def nao_cliente(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff.",
                ephemeral=True
            )

        await fechar_ticket(interaction.channel.id)

        await interaction.response.send_message(
            "❌ Ticket será fechado em 3 segundos...",
            ephemeral=True
        )

        await asyncio.sleep(3)

        await interaction.channel.delete()

    @discord.ui.button(
        label="🔒 Fechar Ticket",
        style=discord.ButtonStyle.gray,
        custom_id="fechar_ticket"
    )
    async def fechar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await is_staff(interaction):
            return await interaction.response.send_message(
                "❌ Apenas a Staff pode fechar tickets.",
                ephemeral=True
            )

        await registrar_fechamento(
            interaction.channel.id,
            interaction.user.id
        )

        cliente = None

        if interaction.channel.topic and interaction.channel.topic.isdigit():
            cliente = interaction.guild.get_member(
                int(interaction.channel.topic)
            )

        if cliente:
            await interaction.channel.set_permissions(
                cliente,
                send_messages=True,
                add_reactions=True,
                view_channel=True
            )

        # Remove a permissão da Staff enviar mensagens
        await interaction.channel.set_permissions(
            interaction.user,
            send_messages=False
        )

        embed = discord.Embed(
            title="⭐ Avaliação do Atendimento",
            description=(
                f"{cliente.mention}, seu atendimento foi finalizado.\n\n"
                "Clique no botão abaixo para avaliar o atendimento.\n\n"
                "Após sua avaliação o ticket será encerrado automaticamente."
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(
            text="Campany • Obrigado pela preferência ❤️"
        )

        await interaction.response.send_message(
            "✅ Ticket encerrado. Aguardando avaliação do cliente.",
            ephemeral=True
        )

        await interaction.channel.send(
            content=cliente.mention,
            embed=embed,
            view=AvaliacaoView()
        )
