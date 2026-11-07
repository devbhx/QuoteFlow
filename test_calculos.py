from decimal import Decimal
from calculos import calcular_subtotal, calcular_desconto, calcular_total

def test_calcular_subtotal():
    resultado = calcular_subtotal(Decimal("150"), 3)
    assert resultado == Decimal("450")

def test_calcular_desconto():
    resultado = calcular_desconto(Decimal("200"), Decimal("10"))
    assert resultado == Decimal("20")


def test_calcular_total():
    resultado = calcular_total(Decimal("200"), Decimal("20"))
    assert resultado == Decimal("180")