"""Fluxos de criação, consulta e edição de propostas no terminal."""

from decimal import Decimal, InvalidOperation
from datetime import datetime
from formatacao import formatar_moeda
from orcamento import criar_item, calcular_orcamento
from repositorio import (
    salvar_orcamento, buscar_orcamento, listar_orcamentos, buscar_cliente,
    validar_identificador, alterar_status, duplicar_orcamento, editar_orcamento,
    listar_itens_orcamento, editar_item, adicionar_item, remover_item, editar_condicoes,
)
from terminal_comum import (
    ler_nome, ler_quantidade, ler_valor_unitario, ler_desconto,
    deseja_adicionar_outro, formatar_data,
)


def criar_orcamento(conexao=None):
    # ===== ENTRADA DE DADOS =====

    print("===== BEM-VINDO AO QUOTEFLOW =====")

    cliente_id = None
    if conexao is None:
        cliente = ler_nome("Digite o nome do cliente: ")
    else:
        while True:
            entrada = ler_nome("Digite o nome do cliente ou id:NUMERO para usar um cadastro: ")
            if not entrada.lower().startswith("id:"):
                cliente_id = None
                cliente = entrada
                break
            try:
                cliente_id = int(entrada[3:].strip())
                cadastrado = buscar_cliente(conexao, cliente_id)
            except ValueError:
                print("Erro: informe um ID de cliente inteiro positivo válido.")
                continue
            if cadastrado is None:
                print("Cliente cadastrado não encontrado. Use a opção 14 para consultar IDs.")
                continue
            cliente = cadastrado["nome"]
            print(f"Cliente selecionado: #{cliente_id} | {cliente}")
            break

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


    orcamento["cliente_id"] = cliente_id
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
    if orcamento["cliente_id"] is not None:
        print("Cliente cadastrado ID:", orcamento["cliente_id"])
    if orcamento["validade"]:
        print("Validade:", datetime.strptime(orcamento["validade"], "%Y-%m-%d").strftime("%d/%m/%Y"))
    if orcamento["condicoes_pagamento"]:
        print("Condições de pagamento:", orcamento["condicoes_pagamento"])
    if orcamento["observacoes"]:
        print("Observações:", orcamento["observacoes"])
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
    if original["cliente_id"] is not None:
        print("Alterar o nome manualmente desfaz o vínculo com o cadastro do cliente.")
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


def editar_condicoes_no_terminal(conexao):
    try:
        identificador = int(input("Número do orçamento: "))
        validar_identificador(identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    original = buscar_orcamento(conexao, identificador)
    if original is None:
        print("Orçamento não encontrado.")
        return
    validade_atual = (
        datetime.strptime(original["validade"], "%Y-%m-%d").strftime("%d/%m/%Y")
        if original["validade"] else "não informada"
    )
    print(f"Validade atual: {validade_atual}")
    print(f"Pagamento atual: {original['condicoes_pagamento'] or 'não informado'}")
    print(f"Observações atuais: {original['observacoes'] or 'não informadas'}")
    print("Enter mantém cada campo; - limpa um campo opcional.")
    entrada = input("Validade (DD/MM/AAAA): ")
    pagamento = input("Condições de pagamento: ")
    observacoes = input("Observações: ")
    try:
        if entrada == "":
            validade = original["validade"]
        elif entrada.strip() == "-":
            validade = None
        else:
            validade = datetime.strptime(entrada.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        print("Erro: informe uma data válida em DD/MM/AAAA. Nenhuma alteração foi salva.")
        return
    pagamento = (original["condicoes_pagamento"] if pagamento == ""
                 else "" if pagamento.strip() == "-" else pagamento)
    observacoes = (original["observacoes"] if observacoes == ""
                  else "" if observacoes.strip() == "-" else observacoes)
    try:
        encontrado = editar_condicoes(conexao, identificador, validade, pagamento, observacoes)
    except ValueError as erro:
        print(f"Erro: {erro} Nenhuma alteração foi salva.")
        return
    if encontrado:
        print(f"Dados comerciais do orçamento #{identificador} salvos.")
    else:
        print("Orçamento não encontrado.")


def criar_e_salvar_orcamento(conexao):
    resultado = criar_orcamento(conexao)
    if resultado is not None:
        cliente, orcamento = resultado
        identificador = salvar_orcamento(
            conexao, cliente, orcamento["servicos"],
            orcamento["percentual_desconto"],
            **({"cliente_id": orcamento["cliente_id"]}
               if orcamento["cliente_id"] is not None else {}),
        )
        print(f"Orçamento salvo com o número {identificador}.")


def listar_orcamentos_no_terminal(conexao):
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
        return
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
