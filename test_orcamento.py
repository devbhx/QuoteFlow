
from decimal import Decimal
from orcamento import criar_item, calcular_orcamento
import pytest



# ===== TESTES DE VALIDAÇÃO =====

def test_servico_sem_nome():
    with pytest.raises(ValueError):
        criar_item("", 2, Decimal("100"))


def test_quantidade_negativa():
    with pytest.raises(ValueError):
        criar_item("Tomadas", -5, Decimal("80"))


def test_valor_unitario_negativo():
    with pytest.raises(ValueError):
        criar_item("Tomadas", 5, Decimal("-80"))


def test_orcamento_sem_servicos():
    with pytest.raises(ValueError):
        calcular_orcamento([], Decimal("10"))


def test_desconto_acima_de_100():
    servicos = [
        criar_item("Tomadas", 2, Decimal("80"))
    ]

    with pytest.raises(ValueError):
        calcular_orcamento(servicos, Decimal("150"))


def test_criar_item():
    item = criar_item(
        "Instalação de tomadas",
        5,
        Decimal("80.00")
    )

    assert item["nome"] == "Instalação de tomadas"
    assert item["quantidade"] == 5
    assert item["valor_unitario"] == Decimal("80.00")
    assert item["subtotal"] == Decimal("400.00")


def test_calcular_orcamento():
    servicos = [
        criar_item("Tomadas", 5, Decimal("80.00")),
        criar_item("Luminárias", 3, Decimal("120.00"))
    ]

    resultado = calcular_orcamento(
        servicos,
        Decimal("10")
    )

    assert resultado["subtotal_geral"] == Decimal("760.00")
    assert resultado["valor_desconto"] == Decimal("76.00")
    assert resultado["total"] == Decimal("684.00")


def test_orcamento_sem_desconto():
    servicos = [
        criar_item("Automação", 2, Decimal("150.00"))
    ]

    resultado = calcular_orcamento(
        servicos,
        Decimal("0")
    )

    assert resultado["subtotal_geral"] == Decimal("300.00")
    assert resultado["valor_desconto"] == Decimal("0.00")
    assert resultado["total"] == Decimal("300.00")

def test_recalcular_subtotal_adulterado():
    servicos = [
        {
            "nome": "Tomadas",
            "quantidade": 2,
            "valor_unitario": Decimal("80"),
            "subtotal": Decimal("1")
        }
    ]

    resultado = calcular_orcamento(servicos, Decimal("0"))

    assert resultado["subtotal_geral"] == Decimal("160.00")
    assert resultado["total"] == Decimal("160.00")