"""Ponto de entrada: conexão SQLite e navegação do menu principal."""

import sqlite3
from repositorio import CAMINHO_BANCO, abrir_banco
# Mantém disponíveis as funções de entrada antes importadas a partir de main.
from terminal_comum import (
    ler_quantidade, ler_valor_unitario, ler_desconto, ler_nome,
    deseja_adicionar_outro, formatar_data,
)
from terminal_orcamentos import (
    criar_orcamento, criar_e_salvar_orcamento, listar_orcamentos_no_terminal,
    consultar_orcamento, alterar_status_no_terminal, duplicar_orcamento_no_terminal,
    editar_orcamento_no_terminal, editar_item_no_terminal,
    adicionar_item_no_terminal, remover_item_no_terminal, editar_condicoes_no_terminal,
)
from terminal_clientes import (
    cadastrar_cliente_no_terminal, listar_clientes_no_terminal,
    historico_cliente_no_terminal, editar_cliente_no_terminal, vincular_cliente_no_terminal,
)
from terminal_pdf import configurar_prestador_no_terminal, exportar_pdf_no_terminal
from terminal_backup import criar_backup_no_terminal, restaurar_backup_no_terminal


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
            print("18 - Criar backup do banco")
            print("19 - Restaurar backup do banco")
            print("0 - Sair")
            opcao = input("Escolha uma opção: ").strip()
            try:
                if opcao == "1":
                    criar_e_salvar_orcamento(conexao)
                elif opcao == "2":
                    listar_orcamentos_no_terminal(conexao)
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
                elif opcao == "18":
                    criar_backup_no_terminal(conexao)
                elif opcao == "19":
                    restaurar_backup_no_terminal(conexao)
                elif opcao == "0":
                    break
                else:
                    print("Erro: escolha uma opção entre 0 e 19.")
            except sqlite3.Error:
                print("Erro ao acessar o banco. A operação não foi concluída. "
                      "Se estava criando um orçamento, ele não foi salvo.")
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
