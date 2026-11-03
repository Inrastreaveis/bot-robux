"""Cálculos financeiros da loja usando Decimal para evitar erros de float."""

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

CENTAVO = Decimal("0.01")


def decimal_seguro(valor) -> Decimal:
    return Decimal(str(valor))


def dinheiro(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def calcular_grupo(quantidade: int, config: dict) -> Decimal:
    """Preserva exatamente a regra da calculadora original por Grupo.

    O código original cobrava R$ 27,00 por cada bloco completo de 1.000
    Robux e R$ 0,03 por cada Robux restante. Ex.: 650 = R$ 19,50;
    1.600 = R$ 45,00.
    """
    quantidade = int(quantidade)
    milhares = quantidade // 1000
    restante = quantidade % 1000
    preco_milhar = Decimal(str(config.get("group_price_per_1000", "27.00")))
    preco_restante = Decimal(str(config.get("group_price_per_remainder_robux", "0.03")))
    valor = (Decimal(milhares) * preco_milhar) + (Decimal(restante) * preco_restante)
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
