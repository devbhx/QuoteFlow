
from decimal import Decimal
from formatacao import formatar_moeda


def test_formatar_valor_inteiro():
    resultado = formatar_moeda(Decimal("1800"))
    assert resultado == "R$ 1.800,00"


def test_formatar_valor_decimal():
    resultado = formatar_moeda(Decimal("99.90"))
    assert resultado == "R$ 99,90"


def test_formatar_valor_grande():
    resultado = formatar_moeda(Decimal("1250000.50"))
    assert resultado == "R$ 1.250.000,50"


def test_formatar_valor_zero():
    resultado = formatar_moeda(Decimal("0"))
    assert resultado == "R$ 0,00"
