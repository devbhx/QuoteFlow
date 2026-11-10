"""Comandos de backup e restauração com confirmação explícita no terminal."""

import sqlite3

from backup import criar_backup
from restauracao import restaurar_backup


def criar_backup_no_terminal(conexao):
    try:
        caminho = criar_backup(conexao)
    except (OSError, sqlite3.Error, ValueError) as erro:
        print(f"Erro ao criar backup: {erro}")
        return
    print(f"Backup criado: {caminho}")


def confirmar_restauracao(caminho, resumo):
    print(f"Backup validado: {caminho}")
    print(f"Conteúdo: {resumo['clientes']} clientes, {resumo['orcamentos']} orçamentos "
          f"e {resumo['itens_orcamento']} serviços.")
    print("Atenção: os dados atuais serão substituídos pelos dados deste backup.")
    print("Uma cópia de segurança do banco atual será criada antes da substituição.")
    resposta = input("Digite RESTAURAR para confirmar (Enter cancela): ").strip()
    return resposta == "RESTAURAR"


def restaurar_backup_no_terminal(conexao):
    arquivo = input("Caminho do arquivo de backup (Enter cancela): ").strip()
    if not arquivo:
        print("Restauração cancelada.")
        return
    try:
        seguranca = restaurar_backup(conexao, arquivo, confirmar=confirmar_restauracao)
    except (OSError, sqlite3.Error, ValueError) as erro:
        print(f"Erro ao restaurar backup: {erro}")
        return
    if seguranca is None:
        print("Restauração cancelada. Nenhum dado foi substituído.")
    else:
        print("Banco restaurado com sucesso.")
        print(f"Backup do estado anterior: {seguranca}")
