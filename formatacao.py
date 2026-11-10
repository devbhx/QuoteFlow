
from calculos import arredondar_moeda


def formatar_moeda(valor):
    valor_formatado = f"{arredondar_moeda(valor):,.2f}"

    valor_formatado = valor_formatado.replace(",", "X")
    valor_formatado = valor_formatado.replace(".", ",")
    valor_formatado = valor_formatado.replace("X", ".")

    return f"R$ {valor_formatado}"
