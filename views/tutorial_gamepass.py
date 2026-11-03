import discord

CREATOR_HUB_URL = "https://create.roblox.com/dashboard/creations"
GUIA_OFICIAL_URL = "https://create.roblox.com/docs/production/monetization/passes"


def embed_tutorial_pc() -> discord.Embed:
    embed = discord.Embed(
        title="🖥️ Tutorial: criar Gamepass pelo PC",
        description=(
            "Siga os passos na ordem. A experiência precisa estar publicada no Roblox antes de criar o passe.\n\n"
            "**1. Entre no Creator Hub**\n"
            f"Abra [create.roblox.com]({CREATOR_HUB_URL}) e entre na sua conta Roblox.\n\n"
            "**2. Escolha sua experiência**\n"
            "Na página **Creations (Criações)**, abra a experiência que você publicou.\n\n"
            "**3. Abra a área de Passes**\n"
            "No menu da experiência, entre em **Monetization (Monetização) → Passes** e clique em **Create Pass (Criar passe)**.\n\n"
            "**4. Preencha os dados**\n"
            "Envie uma imagem para o ícone, escreva um nome e uma descrição e selecione uma categoria. Depois clique em **Create Pass**.\n\n"
            "**5. Deixe o passe disponível para venda externa**\n"
            "Volte ao menu da experiência e abra **Monetization → Shop (Loja)**. Encontre o passe e marque **Listed (Listado)**. Clique em **Save Changes (Salvar alterações)**.\n\n"
            "**6. Confira o preço**\n"
            "Use exatamente a quantidade de Robux mostrada no seu ticket. Não coloque o valor que deseja receber; coloque o valor maior indicado pelo bot para considerar a taxa.\n\n"
            "**7. Envie o link no ticket**\n"
            "Abra a página do passe, copie o link e envie aqui para a equipe conferir."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="⚠️ Atenção",
        value=(
            "Gamepasses são compras únicas: a mesma pessoa só pode comprar um passe uma vez. "
            "Para um novo pedido, crie um passe novo. Nunca envie sua senha, código de autenticação ou cookie."
        ),
        inline=False,
    )
    embed.add_field(name="📖 Guia oficial do Roblox", value=f"[Abrir documentação]({GUIA_OFICIAL_URL})", inline=False)
    return embed


def embed_tutorial_mobile() -> discord.Embed:
    embed = discord.Embed(
        title="📱 Tutorial: criar Gamepass pelo celular",
        description=(
            "Faça o procedimento pelo navegador do celular (Chrome ou Safari), não pelo aplicativo Roblox. "
            "Algumas opções do Creator Hub podem exigir a versão para computador.\n\n"
            "**1. Abra o navegador**\n"
            f"Acesse [create.roblox.com]({CREATOR_HUB_URL}) e entre na sua conta Roblox.\n\n"
            "**2. Ative o site para computador**\n"
            "• **Android / Chrome:** toque nos três pontinhos ⋮ e marque **Site para computador**.\n"
            "• **iPhone / Safari:** toque no botão **aA** da barra de endereço e escolha **Solicitar Site para Computador**.\n\n"
            "**3. Abra sua experiência publicada**\n"
            "Entre em **Creations (Criações)** e selecione a experiência que você publicou.\n\n"
            "**4. Crie o passe**\n"
            "No menu, abra **Monetization (Monetização) → Passes → Create Pass (Criar passe)**. Se o botão não aparecer, confirme que o site para computador está ativado.\n\n"
            "**5. Preencha e crie**\n"
            "Escolha uma imagem, informe o nome e a descrição, selecione uma categoria e toque em **Create Pass**.\n\n"
            "**6. Ative a listagem**\n"
            "Volte ao menu da experiência, abra **Monetization → Shop (Loja)**, marque o passe como **Listed (Listado)** e toque em **Save Changes (Salvar alterações)**.\n\n"
            "**7. Envie o link**\n"
            "Abra o passe, copie o link e envie no ticket. Confira antes se o valor é exatamente o que o bot informou."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="⚠️ Atenção",
        value=(
            "Gamepasses são compras únicas: a mesma pessoa só pode comprar um passe uma vez. "
            "Para um novo pedido, crie um passe novo. Nunca envie sua senha, código de autenticação ou cookie."
        ),
        inline=False,
    )
    embed.add_field(name="📖 Guia oficial do Roblox", value=f"[Abrir documentação]({GUIA_OFICIAL_URL})", inline=False)
    return embed


class TutorialGamepassView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Tutorial pelo PC", emoji="🖥️", style=discord.ButtonStyle.primary)
    async def pc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_tutorial_pc(), ephemeral=True)

    @discord.ui.button(label="Tutorial pelo celular", emoji="📱", style=discord.ButtonStyle.primary)
    async def mobile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=embed_tutorial_mobile(), ephemeral=True)


class TutorialGamepassTicketButton(discord.ui.Button):
    """Botao exibido no ticket de pedidos feitos por Gamepass."""

    def __init__(self):
        super().__init__(
            label="Como criar a Gamepass",
            emoji="📚",
            style=discord.ButtonStyle.secondary,
            custom_id="tutorial_gamepass_ticket",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Escolha o tutorial em português para o seu dispositivo:",
            view=TutorialGamepassView(),
            ephemeral=True,
        )
