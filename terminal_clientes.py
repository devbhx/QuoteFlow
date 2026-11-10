"""Cadastro, busca, edição e histórico de clientes no terminal."""

from repositorio import (
    cadastrar_cliente, listar_clientes, buscar_cliente, editar_cliente,
    buscar_orcamento, listar_orcamentos, vincular_cliente,
)
from terminal_comum import ler_nome, formatar_data


def cadastrar_cliente_no_terminal(conexao):
    nome = ler_nome("Nome do cliente: ")
    contato = input("Contato (opcional): ").strip()
    identificador = cadastrar_cliente(conexao, nome, contato)
    print(f"Cliente cadastrado com o número {identificador}.")


def listar_clientes_no_terminal(conexao):
    nome = input("Nome ou parte do nome (Enter para todos): ").strip()
    clientes = listar_clientes(conexao, nome=nome or None)
    if not clientes:
        print("Nenhum cliente encontrado." if nome else "Nenhum cliente cadastrado.")
        return
    for cliente in clientes:
        print(f"#{cliente['id']} | {cliente['nome']} | "
              f"{cliente['contato'] or 'Contato não informado'}")


def historico_cliente_no_terminal(conexao):
    try:
        identificador = int(input("ID do cliente: "))
        cliente = buscar_cliente(conexao, identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if cliente is None:
        print("Cliente cadastrado não encontrado.")
        return
    print(f"Histórico do cliente #{identificador} | {cliente['nome']}")
    registros = listar_orcamentos(conexao, cliente_id=identificador)
    if not registros:
        print("Nenhum orçamento vinculado a este cliente.")
        return
    for registro in registros:
        print(f"#{registro['id']} | {registro['cliente']} | "
              f"{formatar_data(registro['criado_em'])} | {registro['status']}")


def editar_cliente_no_terminal(conexao):
    try:
        identificador = int(input("ID do cliente a editar: "))
        atual = buscar_cliente(conexao, identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if atual is None:
        print("Cliente cadastrado não encontrado.")
        return
    print(f"Nome atual: {atual['nome']}")
    print(f"Contato atual: {atual['contato'] or 'não informado'}")
    print("Os nomes registrados nos orçamentos existentes serão preservados.")
    nome = input("Novo nome (Enter para manter): ")
    contato = input("Novo contato (Enter para manter, - para limpar): ")
    nome = atual["nome"] if nome == "" else nome
    contato = atual["contato"] if contato == "" else ("" if contato.strip() == "-" else contato)
    try:
        encontrado = editar_cliente(conexao, identificador, nome, contato)
    except ValueError as erro:
        print(f"Erro: {erro} Nenhuma alteração foi salva.")
        return
    if encontrado:
        print(f"Cliente #{identificador} atualizado.")
    else:
        print("Cliente cadastrado não encontrado.")


def vincular_cliente_no_terminal(conexao):
    try:
        orcamento_id = int(input("Número do orçamento a vincular: "))
        orcamento = buscar_orcamento(conexao, orcamento_id)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if orcamento is None:
        print("Orçamento não encontrado.")
        return
    try:
        cliente_id = int(input("ID do cliente cadastrado: "))
        cliente = buscar_cliente(conexao, cliente_id)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    if cliente is None:
        print("Cliente cadastrado não encontrado.")
        return
    print(f"Orçamento #{orcamento_id} | Nome registrado: {orcamento['cliente']}")
    print(f"Cliente escolhido: #{cliente_id} | {cliente['nome']} | "
          f"{cliente['contato'] or 'Contato não informado'}")
    if orcamento["cliente_id"] is not None:
        if orcamento["cliente_id"] == cliente_id:
            print("Este orçamento já está vinculado a este cliente.")
            return
        print(f"Atenção: o vínculo atual com o cliente #{orcamento['cliente_id']} será substituído.")
    print("O nome registrado na proposta e os demais dados serão preservados.")
    while True:
        resposta = input("Confirmar vínculo? (s/n): ").strip().lower()
        if resposta in ("s", "n"):
            break
        print("Erro: digite apenas 's' ou 'n'.")
    if resposta == "n":
        print("Associação cancelada.")
        return
    try:
        encontrado = vincular_cliente(conexao, orcamento_id, cliente_id)
    except ValueError as erro:
        print(f"Erro: {erro} Nenhuma alteração foi salva.")
        return
    if encontrado:
        print(f"Orçamento #{orcamento_id} vinculado ao cliente #{cliente_id}.")
    else:
        print("Orçamento não encontrado.")
