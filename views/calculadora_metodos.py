import discord

from database.configuracoes import obter_configuracoes
from database.vip import pode_usar, obter_usos
from utils.calculos_robux import (
    calcular_desconto_vip,
    calcular_gamepass,
    calcular_grupo,
    calcular_plus,
    calcular_quantidade_gamepass,
    formatar_reais,
    formatar_robux,
)
from views.confirmar_pedido import ConfirmarPedido


class MetodoCompraView(discord.ui.View):
    """Menu efêmero: somente quem clicou na calculadora vê as opções."""

    def __init__(self):
        super().__init__(timeout=180)

    async def abrir_modal(self, interaction: discord.Interaction, metodo: str):
        config = await obter_configuracoes()
        if not config.get("enabled_methods", {}).get(metodo, True):
            return await interaction.response.send_message(
                f"❌ A modalidade **{metodo}** está temporariamente desativada.",
                ephemeral=True,
            )
        await interaction.response.send_modal(QuantidadeRobuxModal(metodo))

    @discord.ui.button(label="Comprar por Grupo", emoji="👥", style=discord.ButtonStyle.success)
    async def grupo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, "Grupo")

    @discord.ui.button(label="Comprar via Plus", emoji="⭐", style=discord.ButtonStyle.primary)
    async def plus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, "Plus")

    @discord.ui.button(label="Comprar via Gamepass", emoji="🎮", style=discord.ButtonStyle.primary)
    async def gamepass(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.abrir_modal(interaction, "Gamepass")


class QuantidadeRobuxModal(discord.ui.Modal):
    robux = discord.ui.TextInput(
        label="Quantos Robux você deseja receber?",
        placeholder="Ex.: 650",
        min_length=1,
        max_length=9,
        required=True,
    )

    def __init__(self, metodo: str):
        super().__init__(title=f"Calculadora • {metodo}")
        self.metodo = metodo

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.robux.value).strip().replace(".", "").replace(",", "")
        try:
            quantidade = int(raw)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Digite somente a quantidade em números inteiros, por exemplo: 650.",
                ephemeral=True,
            )

        if quantidade <= 0 or quantidade > 1_000_000:
            return await interaction.response.send_message(
                "❌ Informe uma quantidade entre 1 e 1.000.000 Robux.",
                ephemeral=True,
            )

        config = await obter_configuracoes()
        if not config.get("enabled_methods", {}).get(self.metodo, True):
            return await interaction.response.send_message(
                f"❌ A modalidade **{self.metodo}** está temporariamente desativada.",
                ephemeral=True,
            )

        desconto = 0
        desconto_aplicado = False
        vip = False
        aviso_vip = None
        robux_gamepass = 0

        if self.metodo == "Grupo":
            valor_base = calcular_grupo(quantidade, config)
            vip_role_id = int(config.get("vip_role_id", 0) or 0)
            role = interaction.guild.get_role(vip_role_id) if interaction.guild and vip_role_id else None
            vip = bool(role and isinstance(interaction.user, discord.Member) and role in interaction.user.roles)
            total = valor_base

            if vip:
                if await pode_usar(interaction.user.id):
                    desconto_dec, total_dec = calcular_desconto_vip(valor_base, config)
                    desconto = float(desconto_dec)
                    total = float(total_dec)
                    desconto_aplicado = True
                else:
                    usos = await obter_usos(interaction.user.id)
                    limite = int(config.get("vip_uses_per_month", 2))
                    aviso_vip = f"Você já utilizou seus {limite} descontos VIP deste mês ({usos}/{limite})."
            else:
                total = float(valor_base)
        elif self.metodo == "Plus":
            total = float(calcular_plus(quantidade, config))
        else:
            total = float(calcular_gamepass(quantidade, config))
            robux_gamepass = calcular_quantidade_gamepass(quantidade, config)

        embed = discord.Embed(
            title="🧮 Resultado da calculadora",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Modalidade", value=self.metodo, inline=True)
        embed.add_field(name="Robux que deseja receber", value=formatar_robux(quantidade), inline=True)

        if self.metodo == "Gamepass":
            embed.add_field(
                name="🎮 Valor para criar a Gamepass",
                value=f"**{formatar_robux(robux_gamepass)} Robux**",
                inline=False,
            )
            embed.add_field(
                name="ℹ️ Taxa do Roblox considerada",
                value="O cálculo usa o multiplicador configurado para que o recebimento seja suficiente após a taxa.",
                inline=False,
            )
        elif self.metodo == "Plus":
            embed.add_field(name="Taxa aplicada", value="R$ 38,00 por 1.000 Robux", inline=False)
        else:
            embed.add_field(name="Taxa aplicada", value="Tabela antiga de Grupo", inline=False)

        if desconto_aplicado:
            embed.add_field(name="👑 Desconto VIP", value=f"-{formatar_reais(desconto)} ({config['vip_discount_percent']}% configurado)", inline=True)
            embed.add_field(name="Valor sem desconto", value=formatar_reais(float(valor_base)), inline=True)
        elif aviso_vip:
            embed.add_field(name="👑 VIP", value=aviso_vip, inline=False)

        embed.add_field(name="💰 Total do pedido", value=f"**{formatar_reais(total)}**", inline=False)
        embed.set_footer(text="Confira os dados antes de confirmar seu pedido.")

        await interaction.response.send_message(
            embed=embed,
            view=ConfirmarPedido(
                robux=quantidade,
                valor=total,
                vip=vip,
                desconto_aplicado=desconto_aplicado,
                desconto=desconto,
                metodo=self.metodo,
                robux_gamepass=robux_gamepass,
            ),
            ephemeral=True,
        )
