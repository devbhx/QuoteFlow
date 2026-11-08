
from decimal import Decimal, InvalidOperation
from calculos import calcular_subtotal, calcular_desconto, calcular_total
from formatacao import formatar_moeda


# ===== FUNÇÕES DE VALIDAÇÃO =====

def ler_quantidade():
    while True:
        try:
            quantidade = int(input("Digite a quantidade: "))

            if quantidade > 0:
                return quantidade
            else:
                print("Erro: a quantidade deve ser maior que zero.")

        except ValueError:
            print("Erro: digite um número inteiro.")


def ler_valor_unitario():
    while True:
        try:
            entrada = input("Digite o valor unitário: ")
            valor_unitario = Decimal(entrada.strip().replace(",", "."))

            if valor_unitario.is_finite() and valor_unitario > 0:
                return valor_unitario
            else:
                print("Erro: o valor deve ser positivo e finito.")

        except InvalidOperation:
            print("Erro: digite um valor numérico válido.")


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


# ===== ENTRADA DE DADOS =====

print("===== BEM-VINDO AO QUOTEFLOW =====")

cliente = ler_nome("Digite o nome do cliente: ")

servicos = []
subtotal_geral = Decimal("0")

while True:
    print("\n===== NOVO SERVIÇO =====")

    nome_servico = ler_nome("Digite o serviço: ")
    valor_unitario = ler_valor_unitario()
    quantidade = ler_quantidade()

    subtotal = calcular_subtotal(valor_unitario, quantidade)

    servico = {
        "nome": nome_servico,
        "valor_unitario": valor_unitario,
        "quantidade": quantidade,
        "subtotal": subtotal
    }

    servicos.append(servico)
    subtotal_geral += subtotal

    if not deseja_adicionar_outro():
        break


# ===== PROCESSAMENTO =====

print("\n===== DESCONTO =====")
percentual_desconto = ler_desconto()

valor_desconto = calcular_desconto(
    subtotal_geral, percentual_desconto
)

total = calcular_total(subtotal_geral, valor_desconto)


# ===== SAÍDA DE DADOS =====

print("\n========== ORÇAMENTO ==========")
print("Cliente:", cliente)

for servico in servicos:
    print("\nServiço:", servico["nome"])
    print("Valor unitário:", formatar_moeda(servico["valor_unitario"]))
    print("Quantidade:", servico["quantidade"])
    print("Subtotal:", formatar_moeda(servico["subtotal"]))

print("\n-------------------------------")
print("Subtotal geral:", formatar_moeda(subtotal_geral))
print("Desconto (%):", f"{percentual_desconto}%")
print("Valor do desconto:", formatar_moeda(valor_desconto))
print("TOTAL FINAL:", formatar_moeda(total))
print("===============================")
