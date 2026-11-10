"""Restauração explícita de backups compatíveis com o esquema atual do QuoteFlow."""

from contextlib import closing
from datetime import datetime
from decimal import InvalidOperation
from pathlib import Path
import sqlite3
from time import monotonic

from backup import PASTA_BACKUPS, criar_backup
from dados_comerciais import validar_condicoes, validar_texto
from repositorio import buscar_orcamento, validar_identificador


COLUNAS = {
    "clientes": {"id", "nome", "contato", "criado_em"},
    "orcamentos": {"id", "cliente", "cliente_id", "percentual_desconto", "criado_em",
                    "status", "validade", "condicoes_pagamento", "observacoes"},
    "itens_orcamento": {"id", "orcamento_id", "nome", "quantidade", "valor_unitario_centavos"},
    "configuracao_prestador": {"id", "nome", "contato"},
}


def copiar_com_limite(origem, destino):
    """Evita esperar indefinidamente quando outro processo bloqueia o banco."""
    prazo = monotonic() + 5

    def progresso(status, restantes, total):
        if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) and monotonic() >= prazo:
            raise sqlite3.OperationalError("Banco ocupado; tente novamente sem outros acessos.")

    origem.backup(destino, pages=128, progress=progresso, sleep=0.1)


def validar_copia(conexao):
    """Verifica estrutura, integridade e dados sem migrar nem corrigir o backup."""
    if conexao.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("O backup não passou na verificação de integridade.")
    tabelas = {r[0] for r in conexao.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )}
    if tabelas != set(COLUNAS):
        raise ValueError("O arquivo não é um backup compatível com a versão atual do QuoteFlow.")
    if conexao.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view', 'trigger')").fetchone():
        raise ValueError("O backup contém views ou gatilhos não suportados.")
    for tabela, esperadas in COLUNAS.items():
        colunas = conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
        if {r[1] for r in colunas} != esperadas or not any(
            r[1] == "id" and r[2].upper() == "INTEGER" and r[5] == 1 for r in colunas
        ):
            raise ValueError("O esquema do backup não é compatível com a versão atual.")
    for tabela, coluna, destino in (("orcamentos", "cliente_id", "clientes"),
                                    ("itens_orcamento", "orcamento_id", "orcamentos")):
        chaves = conexao.execute(f"PRAGMA foreign_key_list({tabela})").fetchall()
        if not any(r[2] == destino and r[3] == coluna and r[4] == "id" for r in chaves):
            raise ValueError("O esquema do backup não possui os vínculos esperados.")
    if conexao.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("O backup contém vínculos inválidos.")
    # Checagem explícita protege também contra arquivos sem as constraints originais.
    if conexao.execute("""SELECT 1 FROM itens_orcamento AS i
        LEFT JOIN orcamentos AS o ON o.id = i.orcamento_id WHERE o.id IS NULL""").fetchone():
        raise ValueError("O backup contém serviços sem orçamento.")
    conexao.row_factory = sqlite3.Row
    for cliente in conexao.execute("SELECT * FROM clientes"):
        validar_identificador(cliente["id"])
        validar_texto(cliente["nome"], "Nome do cliente", obrigatorio=True)
        validar_texto(cliente["contato"], "Contato")
        datetime.fromisoformat(cliente["criado_em"])
    for prestador in conexao.execute("SELECT * FROM configuracao_prestador"):
        if prestador["id"] != 1:
            raise ValueError("A configuração do prestador é inválida.")
        validar_texto(prestador["nome"], "Nome do prestador", obrigatorio=True)
        validar_texto(prestador["contato"], "Contato")
    for registro in conexao.execute("SELECT * FROM orcamentos"):
        validar_identificador(registro["id"])
        validar_texto(registro["cliente"], "Nome do cliente", obrigatorio=True)
        datetime.fromisoformat(registro["criado_em"])
        if registro["status"] not in ("pendente", "aprovado", "recusado"):
            raise ValueError("O backup contém status inválido.")
        if registro["cliente_id"] is not None:
            validar_identificador(registro["cliente_id"])
            if conexao.execute("SELECT 1 FROM clientes WHERE id = ?", (registro["cliente_id"],)).fetchone() is None:
                raise ValueError("O backup contém cliente vinculado inexistente.")
        # Apenas formato: datas legadas anteriores à emissão continuam preservadas.
        validar_condicoes(registro["validade"], registro["condicoes_pagamento"], registro["observacoes"])
        buscar_orcamento(conexao, registro["id"])
    conexao.row_factory = None
    return {tabela: conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            for tabela in COLUNAS}


def restaurar_backup(conexao, arquivo, *, confirmar, pasta_seguranca=PASTA_BACKUPS):
    """Valida, pede confirmação e protege o banco atual antes da substituição.

    confirmar recebe caminho e contagens; somente True autoriza. None é cancelamento.
    O retorno de sucesso é o caminho do backup de segurança do estado anterior.
    """
    if conexao.in_transaction:
        raise ValueError("Finalize a transação pendente antes de restaurar.")
    caminho = Path(arquivo).expanduser().resolve(strict=True)
    if not caminho.is_file():
        raise ValueError("Selecione um arquivo de backup SQLite.")
    for _, nome, atual in conexao.execute("PRAGMA database_list"):
        if nome == "main" and atual and caminho.samefile(atual):
            raise ValueError("O arquivo escolhido é o próprio banco em uso.")
    # Abertura somente leitura não cria arquivos inexistentes nem executa migrações.
    with closing(sqlite3.connect(caminho.as_uri() + "?mode=ro", uri=True)) as origem:
        origem.execute("PRAGMA trusted_schema=OFF")
        with closing(sqlite3.connect(":memory:")) as copia:
            copiar_com_limite(origem, copia)
            copia.execute("PRAGMA trusted_schema=OFF")
            try:
                resumo = validar_copia(copia)
            except (TypeError, KeyError, OverflowError, InvalidOperation) as erro:
                raise ValueError("O backup contém dados incompatíveis.") from erro
            if confirmar(caminho, resumo) is not True:
                return None
            if conexao.in_transaction:
                raise ValueError("Existe uma transação pendente; restauração cancelada.")
            seguranca = criar_backup(conexao, pasta_seguranca)
            try:
                # Restaura a cópia validada em memória, não um arquivo relido após confirmar.
                copiar_com_limite(copia, conexao)
            except sqlite3.Error as erro:
                raise sqlite3.DatabaseError(
                    f"Falha na restauração. O backup de segurança está em: {seguranca}"
                ) from erro
            return seguranca
