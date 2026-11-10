"""Validações dos dados do prestador e das condições comerciais."""

from datetime import date


def validar_texto(valor, campo, obrigatorio=False):
    if not isinstance(valor, str):
        raise ValueError(f"{campo} deve ser um texto.")
    valor = valor.strip()
    if obrigatorio and not valor:
        raise ValueError(f"{campo} não pode ficar vazio.")
    return valor


def validar_condicoes(validade, condicoes_pagamento, observacoes, *, data_emissao=None):
    """Valida a data ISO e, em novas gravações, sua relação com a emissão."""
    if validade is not None:
        if not isinstance(validade, str):
            raise ValueError("A validade deve ser uma data no formato AAAA-MM-DD.")
        try:
            data = date.fromisoformat(validade)
        except ValueError as erro:
            raise ValueError("A validade deve ser uma data no formato AAAA-MM-DD.") from erro
        if data.isoformat() != validade:
            raise ValueError("A validade deve ser uma data no formato AAAA-MM-DD.")
        if data_emissao is not None and data < data_emissao:
            raise ValueError("A validade não pode ser anterior à data de emissão do orçamento.")
    return (
        validade,
        validar_texto(condicoes_pagamento, "Condições de pagamento"),
        validar_texto(observacoes, "Observações"),
    )
