
from decimal import Decimal

from calculos import (
    calcular_subtotal,
    calcular_desconto,
    calcular_total
)


# ===== TESTES ORIGINAIS =====

def test_calcular_subtotal():
    resultado = calcular_subtotal(Decimal("150"), 3)
    assert resultado == Decimal("450")


def test_calcular_desconto():
    resultado = calcular_desconto(
        Decimal("200"), Decimal("10")
    )
    assert resultado == Decimal("20")


def test_calcular_total():
    resultado = calcular_total(
        Decimal("200"), Decimal("20")
    )
    assert resultado == Decimal("180")


# ===== TESTES DE ARREDONDAMENTO =====

def test_arredondamento_desconto():
    resultado = calcular_desconto(
        Decimal("99.90"), Decimal("15")
    )
    assert resultado == Decimal("14.99")


def test_total_com_desconto_arredondado():
    subtotal = Decimal("99.90")
    desconto = calcular_desconto(
        subtotal, Decimal("15")
    )
    resultado = calcular_total(subtotal, desconto)

    assert resultado == Decimal("84.91")
