from decimal import Decimal, InvalidOperation

import discord
from discord import app_commands
from discord.ext import commands

from database.configuracoes import obter_configuracoes, salvar_configuracoes


EDITABLE_FIELDS = {
    "group_price_per_1000": ("Grupo • preço por 1.000 completos", "27.00", "Padrão original: 27,00"),
    "group_price_per_remainder_robux": ("Grupo • preço por Robux restante", "0.03", "Padrão original: 0,03"),
    "plus_price_per_1000": ("Plus • preço por 1.000 Robux", "38.00", "Ex.: 38,00"),
    "gamepass_price_per_1000": ("Gamepass • preço por 1.000 Robux", "42.00", "Ex.: 42,00"),
    "gamepass_fee_multiplier": ("Gamepass • multiplicador da taxa", "1.429", "Padrão: 1,429"),
    "vip_discount_percent": ("Desconto VIP da compra por Grupo (%)", "7", "Ex.: 7"),
    "vip_uses_per_month": ("Quantidade de usos VIP por mês", "2", "Ex.: 2"),
}


def somente_admin(interaction: discord.Interaction) -> bool:
    return bool(
        interaction.guild
        and (
            interaction.user.id == interaction.guild.owner_id
            or interaction.user.id in {1459424313483591711, 1395249767671660584}
            or interaction.user.guild_permissions.administrator
        )
    )


def fmt(valor) -> str:
    return f"R$ {Decimal(str(valor)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def resumo_config(config: dict) -> discord.Embed:
    metodos = config.get("enabled_methods", {})
    pacotes = config.get("gamepass_packages", {})
    pacotes_texto = " • ".join(
        f"{int(q):,}".replace(",", ".") + f" = {fmt(preco)}"
        for q, preco in sorted(pacotes.items(), key=lambda item: int(item[0]))
    ) or "Nenhum pacote fixo"
    embed = discord.Embed(
        title="⚙️ Configuração do bot",
        description=(
            "Edite os preços e o comportamento da calculadora diretamente pelo Discord. "
            "As alterações ficam salvas no banco de dados e continuam depois que o bot reiniciar."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="💰 Preços atuais",
        value=(
            f"**Grupo:** R$ {config['group_price_per_1000']} por 1.000 completos + R$ {config['group_price_per_remainder_robux']} por Robux restante\n"
            f"**Plus:** R$ {config['plus_price_per_1000']} / 1.000\n"
            f"**Gamepass:** R$ {config['gamepass_price_per_1000']} / 1.000\n"
            f"**Multiplicador Gamepass:** {config['gamepass_fee_multiplier']}\n"
            f"**VIP (Grupo):** {config['vip_discount_percent']}% — {config['vip_uses_per_month']} uso(s)/mês"
        ),
        inline=False,
    )
    embed.add_field(name="🎮 Pacotes Gamepass com preço definido", value=pacotes_texto, inline=False)
    embed.add_field(
        name="🔘 Modalidades",
        value=" • ".join(f"{nome}: {'Ativada ✅' if ligado else 'Desativada ❌'}" for nome, ligado in metodos.items()),
        inline=False,
    )
    cargos_ticket = config.get("ticket_role_ids", []) or []
    cargos_texto = ", ".join(f"`{int(role_id)}`" for role_id in cargos_ticket) if cargos_ticket else "Nenhum cargo adicional"
    modo_pix = str(config.get("pix_active_mode", "ambas")).casefold()
    modo_pix_texto = {"1": "Somente chave 1", "2": "Somente chave 2", "ambas": "As duas chaves"}.get(modo_pix, "As duas chaves")
    pix_status = (
        f"Chave 1: {'Configurada' if config.get('pix_key_1') else 'Não configurada'}\n"
        f"Chave 2: {'Configurada' if config.get('pix_key_2') else 'Não configurada'}\n"
        f"Envio: {modo_pix_texto}"
    )
    embed.add_field(
        name="🛠️ Canais e cargos configurados",
        value=(
            f"Categoria de tickets: `{config.get('category_tickets_id', 0)}`\n"
            f"Cargo Staff: `{config.get('staff_role_id', 0)}`\n"
            f"Cargo VIP: `{config.get('vip_role_id', 0)}`\n"
            f"Cargos adicionais mencionados: {cargos_texto}"
        ),
        inline=False,
    )
    embed.add_field(name="💳 Configuração PIX", value=pix_status, inline=False)
    return embed


class EditarValorModal(discord.ui.Modal):
    def __init__(self, chave: str, titulo: str, atual: str, dica: str):
        super().__init__(title="Editar calculadora")
        self.chave = chave
        self.campo = discord.ui.TextInput(
            label=titulo[:45],
            placeholder=dica,
            default=str(atual),
            required=True,
            max_length=16,
        )
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas o dono ou administradores do servidor podem alterar isso.", ephemeral=True)

        texto = str(self.campo.value).strip().replace("R$", "").replace(" ", "").replace(",", ".")
        try:
            numero = Decimal(texto)
        except InvalidOperation:
            return await interaction.response.send_message("❌ Digite um número válido. Exemplo: 42,00", ephemeral=True)

        if not numero.is_finite() or numero < 0:
            return await interaction.response.send_message("❌ O valor precisa ser um número positivo.", ephemeral=True)
        if self.chave == "gamepass_fee_multiplier" and not (Decimal("1") <= numero <= Decimal("5")):
            return await interaction.response.send_message("❌ O multiplicador deve ficar entre 1 e 5. Exemplo: 1,429", ephemeral=True)
        if self.chave == "vip_discount_percent" and numero > 100:
            return await interaction.response.send_message("❌ O desconto VIP não pode passar de 100%.", ephemeral=True)
        if self.chave == "vip_uses_per_month":
            if numero != numero.to_integral_value() or numero > 20:
                return await interaction.response.send_message("❌ Informe um número inteiro entre 0 e 20.", ephemeral=True)
            valor = int(numero)
        else:
            valor = str(numero.quantize(Decimal("0.0001")).normalize())

        config = await obter_configuracoes()
        config[self.chave] = valor
        await salvar_configuracoes(config)
        await interaction.response.send_message(
            f"✅ Configuração atualizada: **{self.campo.label}** = `{valor}`.\nA alteração já está valendo na calculadora.",
            ephemeral=True,
        )


class ConfigPrecosView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=240)
        self.add_item(PrecoSelect())


class PrecoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label[:100], value=key, description=f"Atual: {default}"[:100])
            for key, (label, default, _hint) in EDITABLE_FIELDS.items()
        ]
        super().__init__(placeholder="Escolha qual valor deseja editar", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem usar este painel.", ephemeral=True)
        key = self.values[0]
        config = await obter_configuracoes()
        label, _default, hint = EDITABLE_FIELDS[key]
        await interaction.response.send_modal(EditarValorModal(key, label, str(config.get(key)), hint))


class PacotesGamepassModal(discord.ui.Modal, title="Editar pacotes Gamepass"):
    pacotes = discord.ui.TextInput(
        label="Pacotes no formato quantidade=preço",
        placeholder="500=22;1000=42;3000=126;5000=210",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem editar os pacotes.", ephemeral=True)
        novos = {}
        texto = str(self.pacotes.value).strip()
        try:
            if texto:
                for parte in texto.split(";"):
                    quantidade_txt, preco_txt = parte.split("=", 1)
                    quantidade = int(quantidade_txt.strip())
                    preco = Decimal(preco_txt.strip().replace("R$", "").replace(",", ".").strip())
                    if quantidade <= 0 or quantidade > 1_000_000 or not preco.is_finite() or preco < 0:
                        raise ValueError
                    novos[str(quantidade)] = str(preco.quantize(Decimal("0.01")))
        except (ValueError, InvalidOperation):
            return await interaction.response.send_message(
                "❌ Formato inválido. Use, por exemplo: `500=22;1000=42;3000=126;5000=210`.\n"
                "Deixe em branco para remover os preços fixos e usar somente o valor por 1.000.",
                ephemeral=True,
            )
        config = await obter_configuracoes()
        config["gamepass_packages"] = novos
        await salvar_configuracoes(config)
        await interaction.response.send_message("✅ Pacotes Gamepass atualizados e salvos.", ephemeral=True)


class TextosPainelModal(discord.ui.Modal, title="Editar textos do painel"):
    titulo = discord.ui.TextInput(label="Título do painel", max_length=100, required=True)
    descricao = discord.ui.TextInput(
        label="Descrição do painel",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem editar o painel.", ephemeral=True)
        config = await obter_configuracoes()
        config["panel_title"] = str(self.titulo.value)
        config["panel_description"] = str(self.descricao.value)
        await salvar_configuracoes(config)
        await interaction.response.send_message(
            "✅ Textos salvos. O próximo `/painel` usará o novo título e a nova descrição.",
            ephemeral=True,
        )


class ToggleMetodosView(discord.ui.View):
    def __init__(self, config: dict):
        super().__init__(timeout=240)
        methods = config.get("enabled_methods", {})
        for item, key in zip(self.children, ("Grupo", "Plus", "Gamepass", "Korblox")):
            item.label = f"{key}: {'ATIVADO' if methods.get(key, True) else 'DESATIVADO'}"
            item.style = discord.ButtonStyle.success if methods.get(key, True) else discord.ButtonStyle.secondary

    async def _toggle(self, interaction: discord.Interaction, method: str):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem alterar isso.", ephemeral=True)
        config = await obter_configuracoes()
        methods = config.get("enabled_methods", {})
        methods[method] = not methods.get(method, True)
        config["enabled_methods"] = methods
        await salvar_configuracoes(config)
        await interaction.response.edit_message(
            content="✅ Status das modalidades atualizado. Clique novamente para alternar.",
            view=ToggleMetodosView(config),
        )

    @discord.ui.button(label="Grupo", style=discord.ButtonStyle.success)
    async def grupo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Grupo")

    @discord.ui.button(label="Plus", style=discord.ButtonStyle.success)
    async def plus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Plus")

    @discord.ui.button(label="Gamepass", style=discord.ButtonStyle.success)
    async def gamepass(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Gamepass")

    @discord.ui.button(label="Korblox", style=discord.ButtonStyle.success)
    async def korblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Korblox")


class EditarIdsModal(discord.ui.Modal, title="Editar canais e cargos"):
    categoria = discord.ui.TextInput(label="ID da categoria de tickets", max_length=24, required=True)
    staff = discord.ui.TextInput(label="ID do cargo Staff", max_length=24, required=True)
    vip = discord.ui.TextInput(label="ID do cargo VIP (0 para desativar)", max_length=24, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem editar isso.", ephemeral=True)
        try:
            categoria_id = int(str(self.categoria.value).strip())
            staff_id = int(str(self.staff.value).strip())
            vip_id = int(str(self.vip.value).strip())
        except ValueError:
            return await interaction.response.send_message("❌ Os IDs precisam conter apenas números.", ephemeral=True)

        categoria = interaction.guild.get_channel(categoria_id)
        cargo_staff = interaction.guild.get_role(staff_id)
        cargo_vip = interaction.guild.get_role(vip_id) if vip_id else None
        if not isinstance(categoria, discord.CategoryChannel):
            return await interaction.response.send_message("❌ Não encontrei uma categoria válida com esse ID.", ephemeral=True)
        if cargo_staff is None:
            return await interaction.response.send_message("❌ Não encontrei o cargo Staff com esse ID.", ephemeral=True)
        if vip_id and cargo_vip is None:
            return await interaction.response.send_message("❌ Não encontrei o cargo VIP com esse ID. Use 0 para desativar o VIP.", ephemeral=True)

        config = await obter_configuracoes()
        config["category_tickets_id"] = categoria_id
        config["staff_role_id"] = staff_id
        config["vip_role_id"] = vip_id
        await salvar_configuracoes(config)
        await interaction.response.send_message(
            "✅ Categoria de tickets e cargos atualizados. As próximas verificações já usarão esses IDs.",
            ephemeral=True,
        )


class EditarCargosTicketModal(discord.ui.Modal, title="Cargos mencionados nos tickets"):
    cargo1 = discord.ui.TextInput(label="ID do cargo 1 (opcional)", required=False, max_length=24)
    cargo2 = discord.ui.TextInput(label="ID do cargo 2 (opcional)", required=False, max_length=24)
    cargo3 = discord.ui.TextInput(label="ID do cargo 3 (opcional)", required=False, max_length=24)

    async def on_submit(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem editar os cargos.", ephemeral=True)

        ids = []
        for campo in (self.cargo1, self.cargo2, self.cargo3):
            texto = str(campo.value).strip()
            if not texto:
                continue
            if not texto.isdigit():
                return await interaction.response.send_message("❌ Os IDs dos cargos devem conter apenas números. Deixe vazio para não usar aquele espaço.", ephemeral=True)
            role_id = int(texto)
            role = interaction.guild.get_role(role_id) if interaction.guild else None
            if role is None:
                return await interaction.response.send_message(f"❌ Não encontrei o cargo `{role_id}` neste servidor.", ephemeral=True)
            if role.is_default():
                return await interaction.response.send_message("❌ Não use o cargo @everyone. Escolha cargos específicos para os tickets.", ephemeral=True)
            if role_id not in ids:
                ids.append(role_id)

        config = await obter_configuracoes()
        config["ticket_role_ids"] = ids[:3]
        await salvar_configuracoes(config)
        descricao = ", ".join(f"<@&{role_id}>" for role_id in ids) if ids else "Nenhum cargo adicional"
        await interaction.response.send_message(
            f"✅ Cargos dos tickets atualizados: {descricao}.\nVocê pode configurar de zero a três cargos.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class ConfigurarPixModal(discord.ui.Modal, title="Configurar chaves PIX"):
    chave1 = discord.ui.TextInput(
        label="Chave PIX 1 (vazio para desativar)",
        placeholder="CPF, CNPJ, e-mail, telefone ou chave aleatória",
        required=False,
        max_length=200,
    )
    chave2 = discord.ui.TextInput(
        label="Chave PIX 2 (vazio para desativar)",
        placeholder="Opcional: deixe vazio se não for usar",
        required=False,
        max_length=200,
    )
    modo = discord.ui.TextInput(
        label="Enviar: 1, 2 ou ambas",
        placeholder="Digite 1, 2 ou ambas",
        required=True,
        max_length=10,
        default="ambas",
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem configurar o PIX.", ephemeral=True)

        chave1 = str(self.chave1.value).strip()
        chave2 = str(self.chave2.value).strip()
        modo = str(self.modo.value).strip().casefold()
        if modo not in {"1", "2", "ambas"}:
            return await interaction.response.send_message("❌ No campo de envio, digite somente `1`, `2` ou `ambas`.", ephemeral=True)
        if modo == "1" and not chave1:
            return await interaction.response.send_message("❌ Você selecionou a chave 1, mas ela está vazia.", ephemeral=True)
        if modo == "2" and not chave2:
            return await interaction.response.send_message("❌ Você selecionou a chave 2, mas ela está vazia.", ephemeral=True)
        if modo == "ambas" and not (chave1 or chave2):
            # Permite limpar/desativar as duas chaves; o bot avisará no ticket que PIX não está configurado.
            pass

        config = await obter_configuracoes()
        config["pix_key_1"] = chave1
        config["pix_key_2"] = chave2
        config["pix_active_mode"] = modo
        await salvar_configuracoes(config)

        ativas = {"1": "somente a chave 1", "2": "somente a chave 2", "ambas": "as duas chaves configuradas"}[modo]
        await interaction.response.send_message(
            f"✅ Chaves PIX salvas. O bot enviará {ativas} nos tickets de compra.",
            ephemeral=True,
        )


class ConfigBotView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Editar preços da calculadora", emoji="💰", style=discord.ButtonStyle.primary, row=0)
    async def editar_precos(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Escolha o valor que deseja alterar:",
            view=ConfigPrecosView(),
            ephemeral=True,
        )

    @discord.ui.button(label="Editar pacotes Gamepass", emoji="🎮", style=discord.ButtonStyle.primary, row=0)
    async def editar_pacotes(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_configuracoes()
        atuais = ";".join(f"{q}={p}" for q, p in sorted(config.get("gamepass_packages", {}).items(), key=lambda x: int(x[0])))
        modal = PacotesGamepassModal()
        modal.pacotes.default = atuais
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Ativar/desativar pedidos por modalidade", emoji="🔘", style=discord.ButtonStyle.secondary, row=1)
    async def metodos(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_configuracoes()
        await interaction.response.send_message(
            "Ative ou desative os pedidos por Grupo, Plus, Gamepass e o botão Comprar Korblox.\n"
            "A calculadora continuará funcionando mesmo quando uma modalidade estiver desativada:",
            view=ToggleMetodosView(config),
            ephemeral=True,
        )

    @discord.ui.button(label="Editar textos do painel", emoji="📝", style=discord.ButtonStyle.secondary, row=1)
    async def textos(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_configuracoes()
        modal = TextosPainelModal()
        modal.titulo.default = config.get("panel_title", "🛒 Atendimento Campany")
        modal.descricao.default = config.get("panel_description", "Escolha uma opção abaixo.")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Editar canais e cargos", emoji="🛠️", style=discord.ButtonStyle.secondary, row=2)
    async def ids(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_configuracoes()
        modal = EditarIdsModal()
        modal.categoria.default = str(config.get("category_tickets_id", 0))
        modal.staff.default = str(config.get("staff_role_id", 0))
        modal.vip.default = str(config.get("vip_role_id", 0))
        await interaction.response.send_modal(modal)


    @discord.ui.button(label="Configurar cargos dos tickets", emoji="🔔", style=discord.ButtonStyle.secondary, row=3)
    async def cargos_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem alterar isso.", ephemeral=True)
        config = await obter_configuracoes()
        atuais = list(config.get("ticket_role_ids", []) or [])[:3]
        modal = EditarCargosTicketModal()
        modal.cargo1.default = str(atuais[0]) if len(atuais) > 0 else ""
        modal.cargo2.default = str(atuais[1]) if len(atuais) > 1 else ""
        modal.cargo3.default = str(atuais[2]) if len(atuais) > 2 else ""
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Configurar chaves PIX", emoji="💳", style=discord.ButtonStyle.secondary, row=3)
    async def pix(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not somente_admin(interaction):
            return await interaction.response.send_message("❌ Apenas administradores podem alterar isso.", ephemeral=True)
        config = await obter_configuracoes()
        modal = ConfigurarPixModal()
        modal.chave1.default = str(config.get("pix_key_1", "") or "")
        modal.chave2.default = str(config.get("pix_key_2", "") or "")
        modal.modo.default = str(config.get("pix_active_mode", "ambas") or "ambas")
        await interaction.response.send_modal(modal)


class ConfigBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _mostrar_configuracoes(self, interaction: discord.Interaction):
        if not somente_admin(interaction):
            return await interaction.response.send_message(
                "❌ Este comando é exclusivo do dono e dos administradores do servidor.",
                ephemeral=True,
            )
        config = await obter_configuracoes()
        await interaction.response.send_message(
            embed=resumo_config(config),
            view=ConfigBotView(),
            ephemeral=True,
        )

    @app_commands.command(name="configbot", description="Abre as configurações do bot (atalho antigo).")
    async def configbot(self, interaction: discord.Interaction):
        await self._mostrar_configuracoes(interaction)


async def setup(bot):
    await bot.add_cog(ConfigBot(bot))
