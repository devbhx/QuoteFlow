
from decimal import Decimal, InvalidOperation
from calculos import calcular_subtotal

servicos = []
total_orcamento = Decimal("0")

print("=== QUOTEFLOW ===")
print("Cadastro de serviços\n")

while True:
    nome = input("Nome do serviço: ").strip()

    if not nome:
        print("O nome do serviço não pode ficar vazio.")
        continue

    while True:
        try:
            quantidade = int(input("Quantidade: "))

            if quantidade <= 0:
                print("A quantidade deve ser maior que zero.")
                continue

            break

        except ValueError:
            print("Digite uma quantidade inteira válida.")

    while True:
        try:
            valor_unitario = Decimal(
                input("Valor unitário: ").strip().replace(",", ".")
            )

            if not valor_unitario.is_finite() or valor_unitario <= 0:
                print("O valor deve ser um número positivo e finito.")
                continue

            break

        except InvalidOperation:
            print("Digite um valor monetário válido.")

    subtotal = calcular_subtotal(valor_unitario, quantidade)

    servico = {
        "nome": nome,
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "subtotal": subtotal
    }

    servicos.append(servico)
    total_orcamento += subtotal

    while True:
        continuar = input(
            "\nDeseja adicionar outro serviço? (s/n): "
        ).strip().lower()

        if continuar in ("s", "n"):
            break

        print("Resposta inválida! Digite apenas 's' ou 'n'.")

    if continuar == "n":
        break

    print()

print("\n=== RESUMO DO ORÇAMENTO ===")

for servico in servicos:
    print(f"\nServiço: {servico['nome']}")
    print(f"Quantidade: {servico['quantidade']}")
    print(f"Valor unitário: R$ {servico['valor_unitario']:.2f}")
    print(f"Subtotal: R$ {servico['subtotal']:.2f}")

print("\n-----------------------------")
print(f"TOTAL DO ORÇAMENTO: R$ {total_orcamento:.2f}")
