import discord

from database.configuracoes import obter_configuracoes

from database.tickets import criar_ticket

from views.botoes import TicketButtons
from views.calculadora_metodos import MetodoCompraView
from views.tutorial_gamepass import TutorialGamepassView
from views.verificar_roblox import VerificarRobloxModal


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

    def __init__(self, korblox_enabled: bool = True):
        super().__init__(timeout=None)

        # Quando Korblox estiver desativado, remove o botão dos novos painéis.
        if not korblox_enabled:
            for item in tuple(self.children):
                if getattr(item, "custom_id", None) == "comprar_korblox":
                    self.remove_item(item)
                    break

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
