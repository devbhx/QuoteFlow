
from decimal import Decimal, InvalidOperation
from calculos import calcular_subtotal, calcular_desconto, calcular_total

# ===== FUNÇÕES =====

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
            valor_unitario = Decimal(input("Digite o valor unitário: "))

            if valor_unitario.is_finite() and valor_unitario > 0:
                return valor_unitario
            else:
                print("Erro: o valor deve ser maior que zero.")

        except InvalidOperation:
            print("Erro: digite um valor numérico válido.")

def ler_desconto():
    while True:
        try:
            percentual_desconto = Decimal(input("Digite o desconto (%): "))

            if percentual_desconto.is_finite() and 0 <= percentual_desconto <= 100:
                return percentual_desconto
            else:
                print("Erro: o desconto deve estar entre 0% e 100%.")

        except InvalidOperation:
            print("Erro: digite um percentual numérico válido.")          


# ===== ENTRADA DE DADOS =====

print("===== BEM-VINDO AO QUOTEFLOW =====")

cliente = input("Digite o nome do cliente: ")
servico = input("Digite o serviço: ")

# ===== VALIDAÇÃO DO VALOR UNITÁRIO =====

valor_unitario = ler_valor_unitario()


# ===== VALIDAÇÃO DA QUANTIDADE =====

quantidade = ler_quantidade()

# ===== VALIDAÇÃO DO DESCONTO =====

percentual_desconto = ler_desconto()


# ===== PROCESSAMENTO =====

subtotal = calcular_subtotal(valor_unitario, quantidade)
valor_desconto = calcular_desconto(subtotal, percentual_desconto)
total = calcular_total(subtotal, valor_desconto)


# ===== SAÍDA DE DADOS =====

print("\n========== ORÇAMENTO ==========")
print("Cliente:", cliente)
print("Serviço:", servico)
print("Valor unitário: R$", f"{valor_unitario:.2f}")
print("Quantidade:", quantidade)
print("Subtotal: R$", f"{subtotal:.2f}")
print("Desconto: R$", f"{valor_desconto:.2f}")
print("Total final: R$", f"{total:.2f}")
print("===============================")
