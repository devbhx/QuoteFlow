"""Leitura de entradas e formatação de datas compartilhadas pelo terminal."""

from decimal import Decimal, InvalidOperation
from datetime import datetime
from orcamento import validar_quantidade, normalizar_valor_unitario


def ler_quantidade():
    while True:
        try:
            quantidade = int(input("Digite a quantidade: "))

            return validar_quantidade(quantidade)

        except ValueError as erro:
            print(f"Erro: quantidade inválida. {erro}")


def ler_valor_unitario():
    while True:
        try:
            entrada = input("Digite o valor unitário: ")
            valor_unitario = Decimal(entrada.strip().replace(",", "."))

            return normalizar_valor_unitario(valor_unitario)

        except InvalidOperation:
            print("Erro: digite um valor numérico válido.")
        except ValueError as erro:
            print(f"Erro: {erro}")


def ler_desconto():
    while True:
        try:
            entrada = input("Digite o desconto (%): ")
            percentual_desconto = Decimal(
                entrada.strip().replace(",", ".")
            )

            if (
                percentual_desconto.is_finite()
                and 0 <= percentual_desconto <= 100
            ):
                return percentual_desconto
            else:
                print("Erro: o desconto deve estar entre 0% e 100%.")

        except InvalidOperation:
            print("Erro: digite um percentual numérico válido.")


def ler_nome(mensagem):
    while True:
        nome = input(mensagem).strip()

        if nome:
            return nome

        print("Erro: o nome não pode ficar vazio.")


def deseja_adicionar_outro():
    while True:
        resposta = input(
            "\nDeseja adicionar outro serviço? (s/n): "
        ).strip().lower()

        if resposta == "s":
            return True

        if resposta == "n":
            return False

        print("Erro: digite apenas 's' ou 'n'.")


def formatar_data(data):
    # O banco guarda UTC; o terminal mostra o horário local do computador.
    return datetime.fromisoformat(data).astimezone().strftime("%d/%m/%Y %H:%M")
