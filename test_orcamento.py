
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

@pytest.mark.parametrize("quantidade", [0, True, 1.5, 1_000_001])
def test_quantidade_invalida(quantidade):
    with pytest.raises(ValueError):
        criar_item("Serviço", quantidade, Decimal("10"))


@pytest.mark.parametrize("valor", ["NaN", "sNaN", "Infinity", "0", "0.001", "1e30"])
def test_valor_unitario_invalido(valor):
    with pytest.raises(ValueError):
        criar_item("Serviço", 1, Decimal(valor))


def test_preco_normalizado_antes_do_subtotal():
    item = criar_item("Serviço", 3, Decimal("1.005"))
    assert item["valor_unitario"] == Decimal("1.01")
    assert item["subtotal"] == Decimal("3.03")


def test_limite_monetario_aceito():
    from orcamento import VALOR_MAXIMO
    resultado = calcular_orcamento(
        [criar_item("Serviço", 1, VALOR_MAXIMO)], Decimal("0")
    )
    assert resultado["total"] == VALOR_MAXIMO


def test_subtotal_acima_do_limite():
    from orcamento import VALOR_MAXIMO
    with pytest.raises(ValueError, match="subtotal"):
        criar_item("Serviço", 2, VALOR_MAXIMO)


def test_soma_acima_do_limite():
    servicos = [criar_item("Serviço", 1, Decimal("600000000000"))] * 2
    with pytest.raises(ValueError, match="subtotal geral"):
        calcular_orcamento(servicos, Decimal("0"))


@pytest.mark.parametrize("percentual", ["NaN", "sNaN", "Infinity", "-1"])
def test_percentual_invalido(percentual):
    with pytest.raises(ValueError):
        calcular_orcamento([criar_item("Serviço", 1, Decimal("10"))], Decimal(percentual))


def test_desconto_integral():
    resultado = calcular_orcamento(
        [criar_item("Serviço", 1, Decimal("10"))], Decimal("100")
    )
    assert resultado["valor_desconto"] == Decimal("10.00")
    assert resultado["total"] == Decimal("0.00")


@pytest.mark.parametrize("servico", [{"nome": "Serviço"}, "inválido"])
def test_estrutura_de_servico_invalida(servico):
    with pytest.raises(ValueError):
        calcular_orcamento([servico], Decimal("0"))
