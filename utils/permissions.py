import discord

from database.configuracoes import obter_configuracoes


async def is_staff(interaction: discord.Interaction) -> bool:
    """Verifica administrador, dono do servidor ou cargo de Staff configurado."""
    if not interaction.guild:
        return False

    if interaction.user.guild_permissions.administrator:
        return True

    if interaction.guild.owner_id == interaction.user.id:
        return True

    config = await obter_configuracoes()
    staff_role_id = int(config.get("staff_role_id", 0) or 0)
    cargo_staff = interaction.guild.get_role(staff_role_id) if staff_role_id else None
    return bool(cargo_staff and cargo_staff in getattr(interaction.user, "roles", []))
