"""Configurações editáveis do bot, armazenadas na tabela configuracoes."""

import json
from copy import deepcopy

import aiosqlite

from database.database import DATABASE
from config import CATEGORY_TICKETS, STAFF_ROLE, VIP_ROLE

CONFIG_KEY = "loja_config_v1"
GROUP_CALCULATOR_VERSION = 2

DEFAULT_CONFIG = {
    # Regra original da calculadora por Grupo: R$27 por milheiro completo
    # e R$0,03 por cada Robux que sobrar.
    "group_price_per_1000": "27.00",
    "group_price_per_remainder_robux": "0.03",
    "plus_price_per_1000": "38.00",
    "gamepass_price_per_1000": "42.00",
    # Multiplicador conservador informado pelo dono da loja.
    "gamepass_fee_multiplier": "1.429",
    "gamepass_packages": {"500": "22.00", "1000": "42.00", "3000": "126.00", "5000": "210.00"},
    "vip_discount_percent": "7",
    "vip_uses_per_month": 2,
    "enabled_methods": {"Grupo": True, "Plus": True, "Gamepass": True, "Korblox": True},
    "panel_title": "🛒 Atendimento Campany",
    "panel_description": (
        "Seja bem-vindo à **Campany**!\n\n"
        "Escolha uma das opções abaixo para abrir um atendimento.\n\n"
        "🛒 **Comprar/Calcular Robux**\n"
        "👑 **Comprar Korblox**\n"
        "📚 **Tutorial Gamepass**\n"
        "🛠️ **Suporte Técnico**"
    ),
    "category_tickets_id": CATEGORY_TICKETS,
    "staff_role_id": STAFF_ROLE,
    "vip_role_id": VIP_ROLE,
    "_group_calculator_version": GROUP_CALCULATOR_VERSION,
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
            else:
                saved = {}
        except (TypeError, json.JSONDecodeError):
            saved = {}

    # Migração única: restaura a calculadora por Grupo à regra do código
    # original enviado pelo usuário. Isso também corrige o valor 42/1.000 e
    # os pacotes fixos que foram introduzidos por engano na atualização.
    # Depois desta migração, o administrador ainda pode editar os dois
    # parâmetros pelo /configbot.
    if saved.get("_group_calculator_version") != GROUP_CALCULATOR_VERSION:
        config["group_price_per_1000"] = DEFAULT_CONFIG["group_price_per_1000"]
        config["group_price_per_remainder_robux"] = DEFAULT_CONFIG["group_price_per_remainder_robux"]
        config["_group_calculator_version"] = GROUP_CALCULATOR_VERSION
        config.pop("group_packages", None)
        await salvar_configuracoes(config)

    methods = deepcopy(DEFAULT_CONFIG["enabled_methods"])
    methods.update(config.get("enabled_methods") or {})
    config["enabled_methods"] = methods

    # A Gamepass mantém os pacotes personalizados configuráveis. Grupo não
    # usa pacotes fixos: sempre segue a fórmula original acima.
    if "gamepass_packages" not in saved or not isinstance(config.get("gamepass_packages"), dict):
        config["gamepass_packages"] = deepcopy(DEFAULT_CONFIG["gamepass_packages"])
    config.pop("group_packages", None)
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
