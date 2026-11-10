
from decimal import Decimal, InvalidOperation
from datetime import datetime
import sqlite3
from orcamento import (
    criar_item, calcular_orcamento, validar_quantidade, normalizar_valor_unitario
)
from formatacao import formatar_moeda
from repositorio import (
    CAMINHO_BANCO, abrir_banco, salvar_orcamento, listar_orcamentos, buscar_orcamento,
    alterar_status, validar_identificador, duplicar_orcamento, editar_orcamento,
    listar_itens_orcamento, editar_item, adicionar_item, remover_item
)


# ===== FUNÇÕES DE VALIDAÇÃO =====

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



def criar_orcamento():
    # ===== ENTRADA DE DADOS =====

    print("===== BEM-VINDO AO QUOTEFLOW =====")

    cliente = ler_nome("Digite o nome do cliente: ")

    servicos = []

    while True:
        print("\n===== NOVO SERVIÇO =====")

        nome_servico = ler_nome("Digite o serviço: ")
        valor_unitario = ler_valor_unitario()
        quantidade = ler_quantidade()

        try:
            item = criar_item(nome_servico, quantidade, valor_unitario)
        except ValueError as erro:
            print(f"Erro: {erro} Cadastre o serviço novamente.")
            continue

        servicos.append(item)

        if not deseja_adicionar_outro():
            break


    # ===== PROCESSAMENTO =====

    print("\n===== DESCONTO =====")

    percentual_desconto = ler_desconto()

    try:
        orcamento = calcular_orcamento(servicos, percentual_desconto)
    except ValueError as erro:
        print(f"Erro: {erro} O orçamento não foi gerado.")
        return


    exibir_orcamento(cliente, orcamento)
    return cliente, orcamento


def exibir_orcamento(cliente, orcamento):

    print("\n========== ORÇAMENTO ==========")
    print("Cliente:", cliente)

    for servico in orcamento["servicos"]:
        print("\nServiço:", servico["nome"])
        print("Valor unitário:", formatar_moeda(servico["valor_unitario"]))
        print("Quantidade:", servico["quantidade"])
        print("Subtotal:", formatar_moeda(servico["subtotal"]))

    print("\n-------------------------------")
    print("Subtotal geral:", formatar_moeda(orcamento["subtotal_geral"]))
    print("Desconto (%):", f'{orcamento["percentual_desconto"]}%')
    print("Valor do desconto:", formatar_moeda(orcamento["valor_desconto"]))
    print("TOTAL FINAL:", formatar_moeda(orcamento["total"]))
    print("===============================")


def formatar_data(data):
    # O banco guarda UTC; o terminal mostra o horário local do computador.
    return datetime.fromisoformat(data).astimezone().strftime("%d/%m/%Y %H:%M")


def consultar_orcamento(conexao):
    try:
        identificador = int(input("Número do orçamento: "))
        orcamento = buscar_orcamento(conexao, identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if orcamento is None:
        print("Orçamento não encontrado.")
        return
    print(f"Orçamento #{orcamento['id']} — {formatar_data(orcamento['criado_em'])}")
    print("Status:", orcamento["status"])
    exibir_orcamento(orcamento["cliente"], orcamento)


def alterar_status_no_terminal(conexao):
    try:
        identificador = int(input("Número do orçamento: "))
        validar_identificador(identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return

    print("Status disponíveis: pendente, aprovado, recusado.")
    novo_status = input("Novo status: ").strip().lower()
    try:
        encontrado = alterar_status(conexao, identificador, novo_status)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    if encontrado:
        print(f"Status do orçamento #{identificador} atualizado para {novo_status}.")
    else:
        print("Orçamento não encontrado.")


def duplicar_orcamento_no_terminal(conexao):
    try:
        identificador = int(input("Número do orçamento a duplicar: "))
        validar_identificador(identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    try:
        novo_id = duplicar_orcamento(conexao, identificador)
    except ValueError as erro:
        print(f"Erro: {erro} O orçamento não foi duplicado.")
        return
    if novo_id is None:
        print("Orçamento não encontrado.")
    else:
        print(f"Orçamento #{identificador} duplicado com o número {novo_id}. Status: pendente.")


def editar_orcamento_no_terminal(conexao):
    try:
        identificador = int(input("Número do orçamento a editar: "))
        validar_identificador(identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return

    original = buscar_orcamento(conexao, identificador)
    if original is None:
        print("Orçamento não encontrado.")
        return
    print(f"Cliente atual: {original['cliente']}")
    print(f"Desconto atual: {original['percentual_desconto']}%")
    entrada_cliente = input("Novo cliente (Enter para manter): ")
    cliente = original["cliente"] if entrada_cliente == "" else entrada_cliente.strip()
    entrada_desconto = input("Novo desconto (%) (Enter para manter): ")
    try:
        desconto = (
            original["percentual_desconto"] if entrada_desconto == ""
            else Decimal(entrada_desconto.strip().replace(",", "."))
        )
        encontrado = editar_orcamento(conexao, identificador, cliente, desconto)
    except InvalidOperation:
        print("Erro: digite um percentual numérico válido. Nenhuma alteração foi salva.")
        return
    except ValueError as erro:
        print(f"Erro: {erro} Nenhuma alteração foi salva.")
        return
    if encontrado:
        print(f"Orçamento #{identificador} atualizado.")
    else:
        print("Orçamento não encontrado.")


def editar_item_no_terminal(conexao):
    try:
        orcamento_id = int(input("Número do orçamento: "))
        validar_identificador(orcamento_id)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if buscar_orcamento(conexao, orcamento_id) is None:
        print("Orçamento não encontrado.")
        return

    itens = listar_itens_orcamento(conexao, orcamento_id)
    for item in itens:
        print(f"ID {item['id']} | {item['nome']} | Quantidade: {item['quantidade']} | "
              f"Preço: {formatar_moeda(item['valor_unitario'])}")
    try:
        item_id = int(input("ID do serviço a editar: "))
        validar_identificador(item_id)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    atual = next((item for item in itens if item["id"] == item_id), None)
    if atual is None:
        print("Serviço não encontrado neste orçamento.")
        return

    nome = input("Novo nome (Enter para manter): ")
    quantidade = input("Nova quantidade (Enter para manter): ")
    preco = input("Novo valor unitário (Enter para manter): ")
    try:
        nome = atual["nome"] if nome == "" else nome.strip()
        quantidade = atual["quantidade"] if quantidade == "" else int(quantidade)
        preco = (atual["valor_unitario"] if preco == ""
                 else Decimal(preco.strip().replace(",", ".")))
        encontrado = editar_item(conexao, orcamento_id, item_id, nome, quantidade, preco)
    except InvalidOperation:
        print("Erro: digite um valor numérico válido. Nenhuma alteração foi salva.")
        return
    except ValueError:
        print("Erro: verifique nome, quantidade, preço e os limites do orçamento. "
              "Nenhuma alteração foi salva.")
        return
    if encontrado:
        print(f"Serviço ID {item_id} atualizado no orçamento #{orcamento_id}.")
    else:
        print("Serviço não encontrado neste orçamento.")


def adicionar_item_no_terminal(conexao):
    try:
        orcamento_id = int(input("Número do orçamento: "))
        validar_identificador(orcamento_id)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if buscar_orcamento(conexao, orcamento_id) is None:
        print("Orçamento não encontrado.")
        return
    nome = ler_nome("Nome do novo serviço: ")
    preco = ler_valor_unitario()
    quantidade = ler_quantidade()
    try:
        item_id = adicionar_item(conexao, orcamento_id, nome, quantidade, preco)
    except ValueError as erro:
        print(f"Erro: {erro} Nenhum serviço foi adicionado.")
        return
    if item_id is None:
        print("Orçamento não encontrado.")
    else:
        print(f"Serviço ID {item_id} adicionado ao orçamento #{orcamento_id}.")


def remover_item_no_terminal(conexao):
    try:
        orcamento_id = int(input("Número do orçamento: "))
        validar_identificador(orcamento_id)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if buscar_orcamento(conexao, orcamento_id) is None:
        print("Orçamento não encontrado.")
        return
    itens = listar_itens_orcamento(conexao, orcamento_id)
    for item in itens:
        print(f"ID {item['id']} | {item['nome']} | Quantidade: {item['quantidade']} | "
              f"Preço: {formatar_moeda(item['valor_unitario'])}")
    try:
        item_id = int(input("ID do serviço a remover: "))
        validar_identificador(item_id)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    item = next((item for item in itens if item["id"] == item_id), None)
    if item is None:
        print("Serviço não encontrado neste orçamento.")
        return
    if len(itens) == 1:
        print("Erro: não é possível remover o último serviço do orçamento.")
        return
    while True:
        resposta = input(
            f"Remover {item['nome']} (ID {item_id}) do orçamento #{orcamento_id}? (s/n): "
        ).strip().lower()
        if resposta in ("s", "n"):
            break
        print("Erro: digite apenas 's' ou 'n'.")
    if resposta == "n":
        print("Remoção cancelada.")
        return
    try:
        removido = remover_item(conexao, orcamento_id, item_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return
    if removido:
        print(f"Serviço ID {item_id} removido do orçamento #{orcamento_id}.")
    else:
        print("Serviço não encontrado neste orçamento.")


def main(caminho_banco=CAMINHO_BANCO):
    try:
        conexao = abrir_banco(caminho_banco)
    except sqlite3.Error:
        print("Erro: não foi possível abrir o banco de dados.")
        return

    try:
        while True:
            print("\n===== QUOTEFLOW =====")
            print("1 - Criar e salvar orçamento")
            print("2 - Listar orçamentos")
            print("3 - Consultar orçamento")
            print("4 - Alterar status")
            print("5 - Duplicar orçamento")
            print("6 - Editar cliente e desconto")
            print("7 - Editar serviço")
            print("8 - Adicionar serviço")
            print("9 - Remover serviço")
            print("0 - Sair")
            opcao = input("Escolha uma opção: ").strip()
            try:
                if opcao == "1":
                    resultado = criar_orcamento()
                    if resultado is not None:
                        cliente, orcamento = resultado
                        identificador = salvar_orcamento(
                            conexao, cliente, orcamento["servicos"],
                            orcamento["percentual_desconto"],
                        )
                        print(f"Orçamento salvo com o número {identificador}.")
                elif opcao == "2":
                    filtro = input(
                        "Filtrar por status (pendente/aprovado/recusado) "
                        "ou Enter para todos: "
                    ).strip().lower()
                    cliente = input("Nome ou parte do nome do cliente (Enter para todos): ").strip()
                    try:
                        registros = listar_orcamentos(
                            conexao, status=filtro or None, cliente=cliente or None
                        )
                    except ValueError as erro:
                        print(f"Erro: {erro}")
                        continue
                    if not registros:
                        if cliente:
                            print("Nenhum orçamento encontrado para os filtros informados.")
                        elif filtro:
                            print(f"Nenhum orçamento com status {filtro}.")
                        else:
                            print("Nenhum orçamento salvo.")
                    for registro in registros:
                        quantidade = registro["quantidade_servicos"]
                        rotulo = "serviço" if quantidade == 1 else "serviços"

                        print(
                            f"#{registro['id']} | {registro['cliente']} | "
                            f"{formatar_data(registro['criado_em'])} | "
                            f"{quantidade} {rotulo} | {registro['status']}"
                        )
                elif opcao == "3":
                    consultar_orcamento(conexao)
                elif opcao == "4":
                    alterar_status_no_terminal(conexao)
                elif opcao == "5":
                    duplicar_orcamento_no_terminal(conexao)
                elif opcao == "6":
                    editar_orcamento_no_terminal(conexao)
                elif opcao == "7":
                    editar_item_no_terminal(conexao)
                elif opcao == "8":
                    adicionar_item_no_terminal(conexao)
                elif opcao == "9":
                    remover_item_no_terminal(conexao)
                elif opcao == "0":
                    break
                else:
                    print("Erro: escolha uma opção entre 0 e 9.")
            except sqlite3.Error:
                print("Erro ao acessar o banco. A operação não foi concluída. "
                      "Se estava criando um orçamento, ele não foi salvo.")
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
