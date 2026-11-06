import discord

from database.configuracoes import obter_configuracoes
from database.vip import obter_usos
from utils.calculos_robux import calcular_grupo, formatar_reais, formatar_robux
from views.calculadora_metodos import EscolherDescontoVIPView, criar_embed_resultado
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
        vip_role_id = int(config.get("vip_role_id", 0) or 0)
        vip_role = interaction.guild.get_role(vip_role_id) if interaction.guild and vip_role_id else None
        vip = bool(vip_role and isinstance(interaction.user, discord.Member) and vip_role in interaction.user.roles)

        if vip:
            usos = await obter_usos(interaction.user.id)
            limite = int(config.get("vip_uses_per_month", 2))
            embed = criar_embed_resultado(
                "Grupo",
                quantidade,
                float(valor_base),
                vip_uso_texto=f"Você utilizou **{usos}/{limite}** descontos VIP neste mês. Deseja gastar um uso nesta compra?",
                config=config,
            )
            return await interaction.response.send_message(
                embed=embed,
                view=EscolherDescontoVIPView(interaction.user.id, quantidade, valor_base, config),
                ephemeral=True,
            )

        embed = criar_embed_resultado("Grupo", quantidade, float(valor_base), config=config)
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmarPedido(
                robux=quantidade,
                valor=float(valor_base),
                vip=False,
                desconto_aplicado=False,
                desconto=0,
                metodo="Grupo",
                robux_gamepass=0,
            ),
            ephemeral=True,
        )
