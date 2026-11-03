import discord

from database.configuracoes import obter_configuracoes
from database.tickets import criar_ticket
from database.vip import pode_usar, registrar_uso
from utils.calculos_robux import formatar_reais, formatar_robux
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
    ):
        super().__init__(timeout=300)
        self.robux = int(robux)
        self.valor = float(valor)
        self.vip = bool(vip)
        self.desconto = float(desconto or 0)
        self.desconto_aplicado = bool(desconto_aplicado)
        self.metodo = metodo
        self.robux_gamepass = int(robux_gamepass or 0)

    @discord.ui.button(label="✅ Confirmar Pedido", style=discord.ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            config = await obter_configuracoes()
            categoria_id = int(config.get("category_tickets_id", 0) or 0)
            staff_role_id = int(config.get("staff_role_id", 0) or 0)
            if self.metodo == "Grupo" and self.desconto_aplicado:
                if not await pode_usar(interaction.user.id):
                    return await interaction.response.send_message(
                        "❌ Seu limite de desconto VIP mudou desde a simulação. Abra a calculadora novamente para atualizar o valor.",
                        ephemeral=True,
                    )

            categoria = interaction.guild.get_channel(categoria_id)
            if categoria is None:
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

            staff_role = interaction.guild.get_role(staff_role_id) if staff_role_id else None
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True,
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True,
                ),
            }
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )

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
            elif self.metodo == "Grupo":
                if self.desconto_aplicado:
                    embed.add_field(name="👑 Desconto VIP aplicado", value=f"-{formatar_reais(self.desconto)}", inline=True)
                elif self.vip:
                    embed.add_field(name="👑 VIP", value="Sem desconto disponível neste mês.", inline=True)
            else:
                embed.add_field(name="ℹ️ Desconto VIP", value="Não aplicável para esta modalidade.", inline=False)

            embed.set_footer(text="Campany • Sistema de Atendimento")
            ticket_view = TicketButtons(vip_aplicado=self.desconto_aplicado)
            if self.metodo == "Gamepass":
                ticket_view.add_item(TutorialGamepassTicketButton())

            await canal.send(content=interaction.user.mention, embed=embed, view=ticket_view)

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
            )

            # O uso VIP é contabilizado quando o pedido com desconto é confirmado.
            if self.metodo == "Grupo" and self.desconto_aplicado:
                await registrar_uso(interaction.user.id)

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
                    f"\n🎮 **Crie sua Gamepass com:** "
                    f"{formatar_robux(self.robux_gamepass)} Robux"
                    "\n📚 No ticket, clique em **Como criar a Gamepass** para abrir o tutorial em português."
                )

            await interaction.response.edit_message(
                content=mensagem_confirmacao,
                embed=None,
                view=self,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Não foi possível criar o ticket: `{e}`",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ Não foi possível criar o ticket: `{e}`",
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
