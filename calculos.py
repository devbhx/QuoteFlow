from decimal import Decimal


def calcular_subtotal(valor_unitario, quantidade):
    subtotal = valor_unitario * quantidade
    return subtotal


def calcular_desconto(subtotal, percentual):
    desconto = subtotal * (percentual / Decimal("100"))
    return desconto


def calcular_total(subtotal, valor_desconto):
    total = subtotal - valor_desconto
    return total