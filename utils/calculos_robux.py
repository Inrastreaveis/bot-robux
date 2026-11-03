"""Cálculos financeiros da loja usando Decimal para evitar erros de float."""

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

CENTAVO = Decimal("0.01")


def decimal_seguro(valor) -> Decimal:
    return Decimal(str(valor))


def dinheiro(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def calcular_grupo(quantidade: int, config: dict) -> Decimal:
    # Os pacotes definidos pelo dono têm prioridade. Para qualquer quantidade
    # personalizada, calcula proporcionalmente pelo preço por 1.000 Robux.
    pacotes = config.get("group_packages", {})
    preco_pacote = pacotes.get(str(quantidade))
    if preco_pacote is not None:
        return dinheiro(Decimal(str(preco_pacote)))
    valor = Decimal(quantidade) * Decimal(str(config["group_price_per_1000"])) / Decimal(1000)
    return dinheiro(valor)


def calcular_plus(quantidade: int, config: dict) -> Decimal:
    valor = Decimal(quantidade) * Decimal(str(config["plus_price_per_1000"])) / Decimal(1000)
    return dinheiro(valor)


def calcular_gamepass(quantidade: int, config: dict) -> Decimal:
    pacotes = config.get("gamepass_packages", {})
    preco_pacote = pacotes.get(str(quantidade))
    if preco_pacote is not None:
        return dinheiro(Decimal(str(preco_pacote)))
    valor = Decimal(quantidade) * Decimal(str(config["gamepass_price_per_1000"])) / Decimal(1000)
    return dinheiro(valor)


def calcular_quantidade_gamepass(robux_desejados: int, config: dict) -> int:
    multiplicador = Decimal(str(config["gamepass_fee_multiplier"]))
    return int((Decimal(robux_desejados) * multiplicador).to_integral_value(rounding=ROUND_CEILING))


def calcular_desconto_vip(valor: Decimal, config: dict) -> tuple[Decimal, Decimal]:
    percentual = Decimal(str(config["vip_discount_percent"])) / Decimal(100)
    desconto = dinheiro(valor * percentual)
    return desconto, dinheiro(valor - desconto)


def formatar_reais(valor) -> str:
    valor = dinheiro(Decimal(str(valor)))
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_robux(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")
