import discord

from database.configuracoes import obter_configuracoes
from database.tickets import criar_ticket
from database.vip import registrar_uso
from utils.calculos_robux import formatar_reais, formatar_robux
from utils.ticket_support import (
    enviar_pix_automatico,
    montar_mencoes_abertura,
    montar_overwrites_ticket,
)
from views.botoes import TicketButtons
from views.tutorial_gamepass import TutorialGamepassTicketButton


class ConfirmarPedido(discord.ui.View):
    def __init__(
        self,
        robux,
        valor,
        vip,
        desconto_aplicado,
        desconto=0,
        metodo="Grupo",
        robux_gamepass=0,
        vip_use_counted=False,
    ):
        super().__init__(timeout=300)
        self.robux = int(robux)
        self.valor = float(valor)
        self.vip = bool(vip)
        self.desconto = float(desconto or 0)
        self.desconto_aplicado = bool(desconto_aplicado)
        self.metodo = metodo
        self.robux_gamepass = int(robux_gamepass or 0)
        self.vip_use_counted = bool(vip_use_counted)

    @discord.ui.button(label="✅ Confirmar Pedido", style=discord.ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.guild or not isinstance(interaction.user, discord.Member):
                return await interaction.response.send_message("❌ Este pedido precisa ser confirmado dentro do servidor.", ephemeral=True)

            config = await obter_configuracoes()

            if not config.get("enabled_methods", {}).get(self.metodo, True):
                for item in self.children:
                    item.disabled = True
                return await interaction.response.edit_message(
                    content=(
                        f"⚠️ A modalidade **{self.metodo}** está temporariamente desativada para novos pedidos.\n"
                        "Você ainda pode usar a calculadora normalmente, mas a confirmação não abrirá um ticket."
                    ),
                    embed=None,
                    view=self,
                )

            categoria_id = int(config.get("category_tickets_id", 0) or 0)
            categoria = interaction.guild.get_channel(categoria_id)
            if not isinstance(categoria, discord.CategoryChannel):
                return await interaction.response.send_message(
                    "❌ Categoria de tickets não encontrada. Avise um administrador.",
                    ephemeral=True,
                )

            for canal_existente in categoria.text_channels:
                if canal_existente.topic == str(interaction.user.id):
                    return await interaction.response.send_message(
                        f"❌ Você já possui um ticket aberto: {canal_existente.mention}",
                        ephemeral=True,
                    )

            # Compatibilidade com pedidos antigos que ainda cheguem sem a reserva.
            # No fluxo novo, o uso já foi contabilizado quando o cliente clicou em "Usar VIP".
            if self.metodo == "Grupo" and self.desconto_aplicado and not self.vip_use_counted:
                limite = int(config.get("vip_uses_per_month", 2))
                reservado = await registrar_uso(interaction.user.id, limite=limite)
                if not reservado:
                    return await interaction.response.send_message(
                        f"❌ Você já utilizou os {limite} descontos VIP deste mês. Refaça o cálculo sem desconto.",
                        ephemeral=True,
                    )
                self.vip_use_counted = True

            overwrites = await montar_overwrites_ticket(interaction.guild, interaction.user, config)
            canal = await interaction.guild.create_text_channel(
                name=f"pedido-{interaction.user.name}"[:90],
                category=categoria,
                overwrites=overwrites,
                topic=str(interaction.user.id),
            )

            embed = discord.Embed(
                title="🎫 Pedido de Robux",
                description=(
                    f"👤 **Cliente:** {interaction.user.mention}\n"
                    "📂 **Categoria:** Compra de Robux\n"
                    "📌 **Status:** 🟢 Aguardando atendimento\n"
                    "👮 **Atendente:** Nenhum"
                ),
                color=discord.Color.green(),
            )
            embed.add_field(name="🛒 Modalidade", value=self.metodo, inline=True)
            embed.add_field(name="💎 Robux desejados", value=formatar_robux(self.robux), inline=True)
            embed.add_field(name="💰 Valor do pedido", value=formatar_reais(self.valor), inline=True)

            if self.metodo == "Gamepass":
                embed.add_field(
                    name="🎮 Valor que deve colocar na Gamepass",
                    value=f"**{formatar_robux(self.robux_gamepass)} Robux**",
                    inline=False,
                )
                embed.add_field(
                    name="Importante",
                    value="Crie a Gamepass exatamente com o valor indicado acima e envie o link neste ticket.",
                    inline=False,
                )
            elif self.metodo == "Grupo" and self.desconto_aplicado:
                embed.add_field(name="👑 Desconto VIP aplicado", value=f"-{formatar_reais(self.desconto)}", inline=True)
            elif self.metodo == "Grupo" and self.vip:
                embed.add_field(name="👑 Benefício VIP", value="Você optou por não usar o desconto nesta compra.", inline=False)

            embed.set_footer(text="Campany • Sistema de Atendimento")
            ticket_view = TicketButtons(vip_aplicado=self.desconto_aplicado)
            if self.metodo == "Gamepass":
                ticket_view.add_item(TutorialGamepassTicketButton())

            await criar_ticket(
                canal_id=canal.id,
                user_id=interaction.user.id,
                categoria="🛒 Compra de Robux",
                robux=self.robux,
                valor=self.valor,
                vip=self.vip,
                desconto=self.desconto,
                desconto_aplicado=self.desconto_aplicado,
                metodo_compra=self.metodo,
                robux_gamepass=self.robux_gamepass,
                vip_use_counted=self.vip_use_counted,
            )

            mencoes, allowed_mentions = montar_mencoes_abertura(interaction.guild, interaction.user, config)
            await canal.send(content=mencoes, embed=embed, view=ticket_view, allowed_mentions=allowed_mentions)
            await enviar_pix_automatico(canal, config, self.valor, self.metodo)

            for item in self.children:
                item.disabled = True
            mensagem_confirmacao = (
                f"✅ Pedido confirmado! Seu ticket foi criado: {canal.mention}\n"
                f"🛒 **Modalidade:** {self.metodo}\n"
                f"💎 **Robux que deseja receber:** {formatar_robux(self.robux)}\n"
                f"💰 **Valor do pedido:** {formatar_reais(self.valor)}"
            )
            if self.metodo == "Gamepass":
                mensagem_confirmacao += (
                    f"\n🎮 **Crie sua Gamepass com:** {formatar_robux(self.robux_gamepass)} Robux"
                    "\n📚 No ticket, clique em **Como criar a Gamepass** para abrir o tutorial em português."
                )

            await interaction.response.edit_message(content=mensagem_confirmacao, embed=None, view=self)

        except Exception as e:
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Não foi possível criar o ticket: `{type(e).__name__}: {e}`",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ Não foi possível criar o ticket: `{type(e).__name__}: {e}`",
                    ephemeral=True,
                )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="❌ Pedido cancelado.",
            embed=None,
            view=self,
        )
