import discord

from database.configuracoes import obter_configuracoes

from database.tickets import criar_ticket

from views.botoes import TicketButtons
from views.modal_calculadora import CalculadoraRobux
from views.calculadora_metodos import MetodoCompraView
from views.tutorial_gamepass import TutorialGamepassView


def criar_embed_ticket(
    usuario: discord.Member,
    categoria: str
):

    embed = discord.Embed(
        title="🎫 Ticket de Atendimento",
        description=(
            f"👤 **Cliente:** {usuario.mention}\n"
            f"📂 **Categoria:** {categoria}\n"
            f"📌 **Status:** 🟢 Aguardando atendimento\n"
            f"👮 **Atendente:** Nenhum"
        ),
        color=discord.Color.green()
    )

    if usuario.display_avatar:
        embed.set_thumbnail(
            url=usuario.display_avatar.url
        )

    embed.set_footer(
        text="Campany • Sistema de Tickets"
    )

    return embed


class AbrirTicket(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def criar_ticket(
        self,
        interaction: discord.Interaction,
        categoria_nome: str
    ):

        config = await obter_configuracoes()
        categoria_id = int(config.get("category_tickets_id", 0) or 0)
        staff_role_id = int(config.get("staff_role_id", 0) or 0)
        categoria = interaction.guild.get_channel(categoria_id)

        if categoria is None:
            return await interaction.response.send_message(
                "❌ Categoria de tickets não encontrada.",
                ephemeral=True
            )

        for canal in categoria.text_channels:

            if canal.topic == str(interaction.user.id):

                return await interaction.response.send_message(
                    f"❌ Você já possui um ticket aberto: {canal.mention}",
                    ephemeral=True
                )

        overwrites = {

            interaction.guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True
                ),

            interaction.guild.me:
                discord.PermissionOverwrite(
                    view_channel=True
                )
        }

        staff_role = interaction.guild.get_role(staff_role_id) if staff_role_id else None
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

        canal = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=categoria,
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        await criar_ticket(
            canal_id=canal.id,
            user_id=interaction.user.id,
            categoria=categoria_nome,
            robux=0,
            valor=0,
            vip=False,
            desconto=0,
            desconto_aplicado=False,
            metodo_compra="Outro",
            robux_gamepass=0,
        )

        await canal.send(
            content=interaction.user.mention,
            embed=criar_embed_ticket(
                interaction.user,
                categoria_nome
            ),
            view=TicketButtons()
        )

        await interaction.response.send_message(
            f"✅ Ticket criado com sucesso: {canal.mention}",
            ephemeral=True
        )

    # ==========================
    # COMPRAR ROBUX
    # ==========================
    @discord.ui.button(
        label="Comprar Robux",
        emoji="🛒",
        style=discord.ButtonStyle.green,
        custom_id="comprar_robux"
    )
    async def comprar_robux(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            CalculadoraRobux()
        )

    # ==========================
    # COMPRAR KORBLOX
    # ==========================
    @discord.ui.button(
        label="Comprar Korblox",
        emoji="👑",
        style=discord.ButtonStyle.blurple,
        custom_id="comprar_korblox"
    )
    async def comprar_korblox(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.criar_ticket(
            interaction,
            "👑 Comprar Korblox"
        )

    # ==========================
    # CALCULADORA
    # ==========================
    @discord.ui.button(
        label="Calcular Robux",
        emoji="🧮",
        style=discord.ButtonStyle.gray,
        custom_id="calcular_robux"
    )
    async def calcular(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Escolha como deseja comprar seus Robux:",
            view=MetodoCompraView(),
            ephemeral=True,
        )

    # ==========================
    # TUTORIAL GAMEPASS
    # ==========================
    @discord.ui.button(
        label="Tutorial Gamepass",
        emoji="📚",
        style=discord.ButtonStyle.secondary,
        custom_id="tutorial_gamepass"
    )
    async def tutorial_gamepass(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Escolha o tutorial do seu dispositivo:",
            view=TutorialGamepassView(),
            ephemeral=True,
        )

    # ==========================
    # SUPORTE
    # ==========================
    @discord.ui.button(
        label="Suporte Técnico",
        emoji="🛠️",
        style=discord.ButtonStyle.red,
        custom_id="suporte_tecnico"
    )
    async def suporte(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.criar_ticket(
            interaction,
            "🛠️ Suporte Técnico"
        )
