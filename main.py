
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
    listar_itens_orcamento, editar_item, adicionar_item, remover_item,
    buscar_prestador, salvar_prestador, editar_condicoes, cadastrar_cliente, listar_clientes, buscar_cliente,
    editar_cliente, vincular_cliente
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


def configurar_prestador_no_terminal(conexao):
    atual = buscar_prestador(conexao) or {"nome": "", "contato": ""}
    print(f"Prestador atual: {atual['nome'] or 'não configurado'}")
    print(f"Contato atual: {atual['contato'] or 'não informado'}")
    nome = input("Nome do prestador (Enter para manter): ")
    contato = input("Contato (Enter para manter, - para limpar): ")
    nome = atual["nome"] if nome == "" else nome
    contato = atual["contato"] if contato == "" else ("" if contato.strip() == "-" else contato)
    try:
        salvar_prestador(conexao, nome, contato)
    except ValueError as erro:
        print(f"Erro: {erro} Nenhuma alteração foi salva.")
        return
    print("Dados do prestador salvos.")


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


def exportar_pdf_no_terminal(conexao):
    try:
        identificador = int(input("Número do orçamento a exportar: "))
        validar_identificador(identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    try:
        # Importação local mantém as outras opções disponíveis sem a dependência.
        from exportacao_pdf import exportar_orcamento
        caminho = exportar_orcamento(conexao, identificador)
    except ModuleNotFoundError:
        print("Erro: instale as dependências com python -m pip install -r requirements.txt.")
        return
    except ValueError as erro:
        print(f"Erro: {erro}")
        return
    except OSError:
        print("Erro: não foi possível gravar o PDF. Verifique a pasta de exportação.")
        return
    if caminho is None:
        print("Orçamento não encontrado.")
    else:
        print(f"PDF exportado: {caminho}")


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
            print("10 - Configurar prestador")
            print("11 - Editar validade, pagamento e observações")
            print("12 - Exportar orçamento em PDF")
            print("13 - Cadastrar cliente")
            print("14 - Listar ou buscar clientes")
            print("15 - Histórico de orçamentos do cliente")
            print("16 - Editar cadastro do cliente")
            print("17 - Vincular orçamento a cliente cadastrado")
            print("0 - Sair")
            opcao = input("Escolha uma opção: ").strip()
            try:
                if opcao == "1":
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
                elif opcao == "10":
                    configurar_prestador_no_terminal(conexao)
                elif opcao == "11":
                    editar_condicoes_no_terminal(conexao)
                elif opcao == "12":
                    exportar_pdf_no_terminal(conexao)
                elif opcao == "13":
                    cadastrar_cliente_no_terminal(conexao)
                elif opcao == "14":
                    listar_clientes_no_terminal(conexao)
                elif opcao == "15":
                    historico_cliente_no_terminal(conexao)
                elif opcao == "16":
                    editar_cliente_no_terminal(conexao)
                elif opcao == "17":
                    vincular_cliente_no_terminal(conexao)
                elif opcao == "0":
                    break
                else:
                    print("Erro: escolha uma opção entre 0 e 17.")
            except sqlite3.Error:
                print("Erro ao acessar o banco. A operação não foi concluída. "
                      "Se estava criando um orçamento, ele não foi salvo.")
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
