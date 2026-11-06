import asyncio

import discord

from database.configuracoes import obter_configuracoes
from database.vip import obter_usos, registrar_uso
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


def criar_embed_resultado(
    metodo: str,
    quantidade: int,
    total: float,
    *,
    valor_base=None,
    desconto=0,
    desconto_aplicado=False,
    robux_gamepass=0,
    vip_uso_texto=None,
    config=None,
):
    embed = discord.Embed(title="🧮 Resultado da calculadora", color=discord.Color.blurple())
    embed.add_field(name="Modalidade", value=metodo, inline=True)
    embed.add_field(name="Robux que deseja receber", value=formatar_robux(quantidade), inline=True)

    if metodo == "Gamepass":
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
    elif metodo == "Plus":
        embed.add_field(name="Taxa aplicada", value="Preço configurado por 1.000 Robux", inline=False)
    else:
        embed.add_field(name="Taxa aplicada", value="Tabela de compra por Grupo", inline=False)

    if desconto_aplicado:
        embed.add_field(name="👑 Desconto VIP aplicado", value=f"-{formatar_reais(desconto)}", inline=True)
        embed.add_field(name="Valor sem desconto", value=formatar_reais(valor_base), inline=True)
    elif vip_uso_texto:
        embed.add_field(name="👑 Benefício VIP", value=vip_uso_texto, inline=False)

    embed.add_field(name="💰 Total do pedido", value=f"**{formatar_reais(total)}**", inline=False)
    if config is not None:
        if config.get("enabled_methods", {}).get(metodo, True):
            embed.set_footer(text="Confira os dados e confirme para abrir seu ticket de pedido.")
        else:
            embed.set_footer(text="Simulação liberada. A confirmação está temporariamente desativada para esta modalidade.")
    return embed


class MetodoCompraView(discord.ui.View):
    """Menu efêmero: somente quem clicou na calculadora vê as opções."""

    def __init__(self):
        super().__init__(timeout=180)

    async def abrir_modal(self, interaction: discord.Interaction, metodo: str):
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


class EscolherDescontoVIPView(discord.ui.View):
    """Pergunta ao VIP se deseja gastar um dos usos mensais no cálculo atual."""

    def __init__(self, user_id: int, quantidade: int, valor_base, config: dict):
        super().__init__(timeout=180)
        self.user_id = int(user_id)
        self.quantidade = int(quantidade)
        self.valor_base = valor_base
        self.config = config
        self._lock = asyncio.Lock()
        self._processado = False
        self.nao_button = next(
            (item for item in self.children if getattr(item, "label", "").startswith("NÃO")),
            None,
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Esta escolha pertence a outro cliente.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="👑 SIM, USAR DESCONTO VIP", style=discord.ButtonStyle.success)
    async def usar_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._lock:
            if self._processado:
                return await interaction.response.send_message("Esta escolha já foi processada.", ephemeral=True)
            self._processado = True
            button.disabled = True
            if self.nao_button:
                self.nao_button.disabled = True
            await interaction.response.defer()

            limite = int(self.config.get("vip_uses_per_month", 2))
            reservado = await registrar_uso(interaction.user.id, limite=limite)
            if not reservado:
                usos = await obter_usos(interaction.user.id)
                button.disabled = True
                self._processado = False
                if self.nao_button:
                    self.nao_button.disabled = False
                await interaction.edit_original_response(
                    content=f"⚠️ Você já utilizou seus **{limite} descontos VIP** deste mês ({usos}/{limite}). Você ainda pode continuar sem desconto clicando em **NÃO, PAGAR VALOR NORMAL**.",
                    view=self,
                )
                return

            desconto_dec, total_dec = calcular_desconto_vip(self.valor_base, self.config)
            desconto = float(desconto_dec)
            total = float(total_dec)
            embed = criar_embed_resultado(
                "Grupo",
                self.quantidade,
                total,
                valor_base=float(self.valor_base),
                desconto=desconto,
                desconto_aplicado=True,
                config=self.config,
            )
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=ConfirmarPedido(
                    robux=self.quantidade,
                    valor=total,
                    vip=True,
                    desconto_aplicado=True,
                    desconto=desconto,
                    metodo="Grupo",
                    robux_gamepass=0,
                    vip_use_counted=True,
                ),
            )

    @discord.ui.button(label="NÃO, PAGAR VALOR NORMAL", style=discord.ButtonStyle.secondary)
    async def nao_usar_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._lock:
            if self._processado:
                return await interaction.response.send_message("Esta escolha já foi processada.", ephemeral=True)
            self._processado = True
            embed = criar_embed_resultado(
                "Grupo",
                self.quantidade,
                float(self.valor_base),
                vip_uso_texto="Você optou por não usar um desconto nesta compra. Seus usos mensais foram preservados.",
                config=self.config,
            )
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=ConfirmarPedido(
                    robux=self.quantidade,
                    valor=float(self.valor_base),
                    vip=True,
                    desconto_aplicado=False,
                    desconto=0,
                    metodo="Grupo",
                    robux_gamepass=0,
                    vip_use_counted=False,
                ),
            )


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
        robux_gamepass = 0

        if self.metodo == "Grupo":
            valor_base = calcular_grupo(quantidade, config)
            vip_role_id = int(config.get("vip_role_id", 0) or 0)
            role = interaction.guild.get_role(vip_role_id) if interaction.guild and vip_role_id else None
            vip = bool(role and isinstance(interaction.user, discord.Member) and role in interaction.user.roles)

            if vip:
                usos = await obter_usos(interaction.user.id)
                limite = int(config.get("vip_uses_per_month", 2))
                texto = f"Você utilizou **{usos}/{limite}** descontos VIP neste mês. Deseja gastar um uso nesta compra?"
                embed = criar_embed_resultado(
                    "Grupo",
                    quantidade,
                    float(valor_base),
                    vip_uso_texto=texto,
                    config=config,
                )
                return await interaction.response.send_message(
                    embed=embed,
                    view=EscolherDescontoVIPView(interaction.user.id, quantidade, valor_base, config),
                    ephemeral=True,
                )

            embed = criar_embed_resultado("Grupo", quantidade, float(valor_base), config=config)
            return await interaction.response.send_message(
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

        if self.metodo == "Plus":
            total = float(calcular_plus(quantidade, config))
        else:
            total = float(calcular_gamepass(quantidade, config))
            robux_gamepass = calcular_quantidade_gamepass(quantidade, config)

        embed = criar_embed_resultado(
            self.metodo,
            quantidade,
            total,
            robux_gamepass=robux_gamepass,
            config=config,
        )
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmarPedido(
                robux=quantidade,
                valor=total,
                vip=False,
                desconto_aplicado=False,
                desconto=0,
                metodo=self.metodo,
                robux_gamepass=robux_gamepass,
            ),
            ephemeral=True,
        )
