import discord

from database.configuracoes import obter_configuracoes
from database.vip import pode_usar, obter_usos
from utils.calculos_robux import calcular_desconto_vip, calcular_grupo, formatar_reais, formatar_robux
from views.confirmar_pedido import ConfirmarPedido


class CalculadoraRobux(discord.ui.Modal, title="🧮 Calculadora de Robux • Grupo"):
    robux = discord.ui.TextInput(
        label="Quantidade de Robux",
        placeholder="Ex: 1600",
        required=True,
        min_length=1,
        max_length=9,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.robux.value).strip().replace(".", "").replace(",", "")
        try:
            quantidade = int(raw)
            if quantidade <= 0 or quantidade > 1_000_000:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                "❌ Informe uma quantidade válida de Robux, usando apenas números.",
                ephemeral=True,
            )

        config = await obter_configuracoes()
        if not config.get("enabled_methods", {}).get("Grupo", True):
            return await interaction.response.send_message(
                "❌ A compra por Grupo está temporariamente desativada.",
                ephemeral=True,
            )

        valor_base = calcular_grupo(quantidade, config)
        valor = valor_base
        desconto = 0
        vip_role_id = int(config.get("vip_role_id", 0) or 0)
        vip_role = interaction.guild.get_role(vip_role_id) if interaction.guild and vip_role_id else None
        vip = bool(vip_role and isinstance(interaction.user, discord.Member) and vip_role in interaction.user.roles)
        desconto_aplicado = False

        embed = discord.Embed(title="🧮 Calculadora Campany", color=0x5865F2)
        embed.add_field(name="💎 Robux", value=formatar_robux(quantidade), inline=False)

        if vip and await pode_usar(interaction.user.id):
            desconto_dec, total_dec = calcular_desconto_vip(valor_base, config)
            desconto = float(desconto_dec)
            valor = total_dec
            desconto_aplicado = True
            embed.add_field(name="👑 Cliente VIP", value="✅ Desconto VIP aplicado.", inline=False)
            embed.add_field(name="Valor original", value=formatar_reais(valor_base), inline=True)
            embed.add_field(name="Desconto", value=f"-{formatar_reais(desconto)}", inline=True)
        elif vip:
            usos = await obter_usos(interaction.user.id)
            limite = int(config.get("vip_uses_per_month", 2))
            embed.add_field(name="👑 Cliente VIP", value=f"⚠️ Você já utilizou seus {limite} descontos deste mês ({usos}/{limite}).", inline=False)

        embed.add_field(name="💰 Total", value=f"**{formatar_reais(valor)}**", inline=False)
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmarPedido(
                robux=quantidade,
                valor=float(valor),
                vip=vip,
                desconto_aplicado=desconto_aplicado,
                desconto=desconto,
                metodo="Grupo",
                robux_gamepass=0,
            ),
            ephemeral=True,
        )
