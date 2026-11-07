
# FUNÇÃO PARA CALCULAR O DESCONTO
def calcular_desconto(subtotal, percentual):
    desconto = subtotal * (percentual / 100)
    return desconto


# FUNÇÃO PARA CALCULAR O TOTAL
def calcular_total(subtotal, valor_desconto):
    total = subtotal - valor_desconto
    return total


# CHAMADA DAS FUNÇÕES
subtotal = 200
percentual = 15

valor_desconto = calcular_desconto(subtotal, percentual)
valor_total = calcular_total(subtotal, valor_desconto)


# SAÍDA
print("Subtotal: R$", subtotal)
print("Desconto: R$", valor_desconto)
print("Total final: R$", valor_total)
