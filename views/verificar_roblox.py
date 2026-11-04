import asyncio
import os
from datetime import datetime, timezone

import aiohttp
import discord

COMUNIDADES = {
    "Comunidade 1": "857720455",
    "Comunidade 2": "1049350210",
    "Comunidade 3": "481150306",
}

ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY", "").strip()


async def buscar_id_roblox(username: str):
    """Converte o nome de usuário Roblox em userId."""
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Não consegui consultar o usuário Roblox (HTTP {response.status})."
                )
            data = await response.json()

    usuarios = data.get("data", [])
    if not usuarios:
        return None, None
    return int(usuarios[0]["id"]), usuarios[0].get("name", username)


async def consultar_entrada_grupo(session, group_id: str, user_id: int):
    """Consulta a associação e a data de entrada, quando a API fornece createTime."""
    url = f"https://apis.roblox.com/cloud/v2/groups/{group_id}/memberships"
    params = {
        "filter": f"user == 'users/{user_id}'",
        "maxPageSize": "10",
    }

    async with session.get(
        url,
        params=params,
        headers={"x-api-key": ROBLOX_API_KEY},
    ) as response:
        if response.status == 401:
            raise RuntimeError("Chave Roblox inválida ou não autorizada (HTTP 401).")
        if response.status == 403:
            raise RuntimeError(
                "A Roblox negou o acesso (HTTP 403). Confira as permissões de leitura das três comunidades."
            )
        if response.status == 429:
            raise RuntimeError("Limite de consultas Roblox atingido. Tente novamente em alguns instantes.")
        if response.status != 200:
            body = (await response.text())[:250]
            raise RuntimeError(f"Erro na API Roblox (HTTP {response.status}): {body}")
        data = await response.json()

    memberships = data.get("groupMemberships", [])
    if not memberships:
        return {"membro": False, "createTime": None}
    return {
        "membro": True,
        "createTime": memberships[0].get("createTime"),
    }


def calcular_dias(create_time: str):
    entrada = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
    if entrada.tzinfo is None:
        entrada = entrada.replace(tzinfo=timezone.utc)
    agora = datetime.now(timezone.utc)
    return max(0, (agora - entrada).days), entrada


class VerificarRobloxModal(discord.ui.Modal, title="Verificar tempo nas comunidades"):
    username = discord.ui.TextInput(
        label="Seu nome de usuário do Roblox",
        placeholder="Digite seu usuário (não o nome de exibição)",
        min_length=3,
        max_length=20,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not ROBLOX_API_KEY:
            return await interaction.followup.send(
                "⚠️ O administrador precisa configurar `ROBLOX_API_KEY` no arquivo `.env` "
                "com uma chave Open Cloud autorizada a ler as três comunidades.",
                ephemeral=True,
            )

        try:
            user_id, nome_real = await buscar_id_roblox(str(self.username).strip())
            if user_id is None:
                return await interaction.followup.send(
                    "❌ Não encontrei esse nome de usuário no Roblox. Confira a escrita.",
                    ephemeral=True,
                )

            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                resultados = await asyncio.gather(
                    *[
                        consultar_entrada_grupo(session, group_id, user_id)
                        for group_id in COMUNIDADES.values()
                    ]
                )

            embed = discord.Embed(
                title="🔎 Resultado da verificação Roblox",
                description=(
                    f"**Conta:** [{discord.utils.escape_markdown(nome_real)}]"
                    f"(https://www.roblox.com/users/{user_id}/profile)\n"
                    f"**ID Roblox:** `{user_id}`"
                ),
                color=discord.Color.blurple(),
            )

            for (nome_comunidade, _), resultado in zip(COMUNIDADES.items(), resultados):
                if not resultado["membro"]:
                    valor = "❌ Não participa desta comunidade"
                elif not resultado["createTime"]:
                    valor = "⚠️ Participa, mas a data de entrada não está disponível na API"
                else:
                    dias, entrada = calcular_dias(resultado["createTime"])
                    valor = (
                        f"**{dias} dias**\n"
                        f"Entrada: {discord.utils.format_dt(entrada, style='d')}"
                    )
                embed.add_field(name=nome_comunidade, value=valor, inline=False)

            embed.set_footer(text="Resultado visível somente para você.")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except RuntimeError as erro:
            await interaction.followup.send(f"❌ {erro}", ephemeral=True)
        except (aiohttp.ClientError, TimeoutError):
            await interaction.followup.send(
                "❌ Não consegui conectar aos serviços do Roblox. Tente novamente mais tarde.",
                ephemeral=True,
            )
        except Exception:
            await interaction.followup.send(
                "❌ Ocorreu um erro inesperado durante a verificação.",
                ephemeral=True,
            )
