
from decimal import Decimal, ROUND_HALF_UP


def arredondar_moeda(valor):
    return valor.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def calcular_subtotal(valor_unitario, quantidade):
    subtotal = arredondar_moeda(valor_unitario) * quantidade
    return arredondar_moeda(subtotal)


def calcular_desconto(subtotal, percentual):
    desconto = subtotal * (percentual / Decimal("100"))
    return arredondar_moeda(desconto)


def calcular_total(subtotal, valor_desconto):
    total = subtotal - valor_desconto
    return arredondar_moeda(total)
