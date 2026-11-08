
from decimal import Decimal

from calculos import (
    calcular_subtotal,
    calcular_desconto,
    calcular_total
)


def criar_item(nome, quantidade, valor_unitario):
    subtotal = calcular_subtotal(valor_unitario, quantidade)

    return {
        "nome": nome,
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "subtotal": subtotal
    }


def calcular_orcamento(servicos, percentual_desconto):
    subtotal_geral = sum(
        (servico["subtotal"] for servico in servicos),
        Decimal("0")
    )

    valor_desconto = calcular_desconto(
        subtotal_geral, percentual_desconto
    )

    total = calcular_total(subtotal_geral, valor_desconto)

    return {
        "servicos": servicos,
        "subtotal_geral": subtotal_geral,
        "percentual_desconto": percentual_desconto,
        "valor_desconto": valor_desconto,
        "total": total
    }

