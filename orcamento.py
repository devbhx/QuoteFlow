
from decimal import Decimal

from calculos import (
    calcular_subtotal,
    calcular_desconto,
    calcular_total
)


def criar_item(nome, quantidade, valor_unitario):
    if not isinstance(nome, str) or not nome.strip():
        raise ValueError("O nome do serviço não pode ficar vazio.")

    if type(quantidade) is not int or quantidade <= 0:
        raise ValueError("A quantidade deve ser um inteiro positivo.")

    if (
        not isinstance(valor_unitario, Decimal)
        or not valor_unitario.is_finite()
        or valor_unitario <= 0
    ):
        raise ValueError("O valor unitário deve ser positivo e finito.")

    subtotal = calcular_subtotal(valor_unitario, quantidade)

    return {
        "nome": nome.strip(),
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "subtotal": subtotal
    }


def calcular_orcamento(servicos, percentual_desconto):
    if not isinstance(servicos, list) or not servicos:
        raise ValueError("O orçamento precisa ter uma lista de serviços.")

    if (
        not isinstance(percentual_desconto, Decimal)
        or not percentual_desconto.is_finite()
        or not 0 <= percentual_desconto <= 100
    ):
        raise ValueError("O desconto deve estar entre 0% e 100%.")

    servicos_validados = []

    for servico in servicos:
        if not isinstance(servico, dict):
            raise ValueError("Cada serviço deve ser um dicionário.")

        try:
            item = criar_item(
                servico["nome"],
                servico["quantidade"],
                servico["valor_unitario"]
            )
        except KeyError as erro:
            raise ValueError(
                f"Campo obrigatório ausente: {erro.args[0]}"
            ) from erro

        servicos_validados.append(item)

    subtotal_geral = sum(
        (servico["subtotal"] for servico in servicos_validados),
        Decimal("0")
    )

    valor_desconto = calcular_desconto(
        subtotal_geral, percentual_desconto
    )

    total = calcular_total(subtotal_geral, valor_desconto)

    return {
        "servicos": servicos_validados,
        "subtotal_geral": subtotal_geral,
        "percentual_desconto": percentual_desconto,
        "valor_desconto": valor_desconto,
        "total": total
    }
