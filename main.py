import os
import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database.database import criar_banco

load_dotenv()

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN não encontrada no arquivo .env")

GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.all()


class LojaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        print("📦 Criando banco...")
        await criar_banco()

        print("📦 Carregando Cogs...")
        await self.load_all_cogs()

        from views.painel import AbrirTicket
        from views.botoes import TicketButtons, SupportTicketButtons
        from views.confirmar_pedido import ConfirmarPedido
        from views.avaliacao import AvaliacaoView, EstrelasView
        from views.pix import PixCopyView

        self.add_view(AbrirTicket())
        self.add_view(TicketButtons())
        self.add_view(SupportTicketButtons())
        self.add_view(PixCopyView())
        self.add_view(AvaliacaoView())
        self.add_view(EstrelasView())

        guild = discord.Object(id=GUILD_ID)

        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)

        print("=" * 40)
        print(f"✅ {len(synced)} comandos sincronizados.")
        print("=" * 40)

    async def load_all_cogs(self):
        if not os.path.isdir("cogs"):
            print("❌ Pasta 'cogs' não encontrada.")
            return

        for arquivo in sorted(os.listdir("cogs")):
            if not arquivo.endswith(".py") or arquivo.startswith("_"):
                continue

            extensao = f"cogs.{arquivo[:-3]}"

            try:
                await self.load_extension(extensao)
                print(f"✅ {arquivo}")
            except Exception:
                import traceback
                print(f"❌ Erro ao carregar {arquivo}")
                traceback.print_exc()

bot = LojaBot()


@bot.event
async def on_ready():
    print("=" * 40)
    print(f"🤖 Logado como: {bot.user}")
    print(f"📡 Online em {len(bot.guilds)} servidor(es)")
    print("=" * 40)





async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
