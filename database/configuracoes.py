"""Configurações editáveis do bot, armazenadas na tabela configuracoes."""

import json
from copy import deepcopy

import aiosqlite

from database.database import DATABASE
from config import CATEGORY_TICKETS, STAFF_ROLE, VIP_ROLE

CONFIG_KEY = "loja_config_v1"

DEFAULT_CONFIG = {
    # Tabela de Grupo informada para a loja; quantidades livres usam R$ 42/1.000.
    "group_price_per_1000": "42.00",
    "group_packages": {"500": "22.00", "1000": "42.00", "3000": "126.00", "5000": "210.00"},
    "plus_price_per_1000": "38.00",
    "gamepass_price_per_1000": "42.00",
    # Multiplicador conservador informado pelo dono da loja.
    "gamepass_fee_multiplier": "1.429",
    "gamepass_packages": {"500": "22.00", "1000": "42.00", "3000": "126.00", "5000": "210.00"},
    "vip_discount_percent": "7",
    "vip_uses_per_month": 2,
    "enabled_methods": {"Grupo": True, "Plus": True, "Gamepass": True},
    "panel_title": "🛒 Atendimento Campany",
    "panel_description": (
        "Seja bem-vindo à **Campany**!\n\n"
        "Escolha uma das opções abaixo para abrir um atendimento.\n\n"
        "🛒 **Comprar Robux**\n"
        "👑 **Comprar Korblox**\n"
        "🧮 **Calcular Robux**\n"
        "📚 **Tutorial Gamepass**\n"
        "🛠️ **Suporte Técnico**"
    ),
    "category_tickets_id": CATEGORY_TICKETS,
    "staff_role_id": STAFF_ROLE,
    "vip_role_id": VIP_ROLE,
}


async def obter_configuracoes() -> dict:
    """Retorna as configurações salvas combinadas com os padrões."""
    config = deepcopy(DEFAULT_CONFIG)
    async with aiosqlite.connect(str(DATABASE)) as db:
        cursor = await db.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?",
            (CONFIG_KEY,),
        )
        row = await cursor.fetchone()

    saved = {}
    if row and row[0]:
        try:
            saved = json.loads(row[0])
            if isinstance(saved, dict):
                config.update(saved)
        except (TypeError, json.JSONDecodeError):
            saved = {}

    # Completa apenas as opções ausentes. Dicionário vazio é uma escolha válida
    # do administrador (significa usar somente o preço proporcional).
    methods = deepcopy(DEFAULT_CONFIG["enabled_methods"])
    methods.update(config.get("enabled_methods") or {})
    config["enabled_methods"] = methods

    for key in ("gamepass_packages", "group_packages"):
        if key not in saved:
            config[key] = deepcopy(DEFAULT_CONFIG[key])
        elif isinstance(saved[key], dict):
            config[key] = saved[key]
    return config


async def salvar_configuracoes(config: dict) -> None:
    async with aiosqlite.connect(str(DATABASE)) as db:
        await db.execute(
            "INSERT INTO configuracoes(chave, valor) VALUES(?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (CONFIG_KEY, json.dumps(config, ensure_ascii=False)),
        )
        await db.commit()


async def atualizar_configuracao(chave: str, valor) -> dict:
    config = await obter_configuracoes()
    config[chave] = valor
    await salvar_configuracoes(config)
    return config
