"""Persistência SQLite: SQL fica aqui; cálculos continuam em orcamento.py."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3

from orcamento import calcular_orcamento, criar_item
from dados_comerciais import validar_texto, validar_condicoes


CAMINHO_BANCO = Path(__file__).resolve().parent / "quoteflow.db"


def abrir_banco(caminho=CAMINHO_BANCO):
    """Abre o banco, cria as tabelas e atualiza estruturas de versões anteriores."""
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    try:
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS orcamentos (
                id INTEGER PRIMARY KEY,
                cliente TEXT NOT NULL CHECK (length(trim(cliente)) > 0),
                cliente_id INTEGER REFERENCES clientes(id),
                percentual_desconto TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente', 'aprovado', 'recusado')),
                validade TEXT,
                condicoes_pagamento TEXT NOT NULL DEFAULT '',
                observacoes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
                contato TEXT NOT NULL DEFAULT '',
                criado_em TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS configuracao_prestador (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
                contato TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS itens_orcamento (
                id INTEGER PRIMARY KEY,
                orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id),
                nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
                quantidade INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 1000000),
                valor_unitario_centavos INTEGER NOT NULL
                    CHECK (valor_unitario_centavos BETWEEN 1 AND 99999999999999)
            );
            CREATE INDEX IF NOT EXISTS idx_itens_orcamento
                ON itens_orcamento(orcamento_id);
        """)
        atualizar_estrutura(conexao)
    except sqlite3.Error:
        conexao.close()
        raise
    return conexao


def atualizar_estrutura(conexao):
    """Adiciona colunas ausentes sem recriar tabelas ou apagar dados."""
    with conexao:
        colunas = conexao.execute("PRAGMA table_info(orcamentos)").fetchall()
        if "status" not in [coluna["name"] for coluna in colunas]:
            conexao.execute("""
                ALTER TABLE orcamentos ADD COLUMN
                    status TEXT NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente', 'aprovado', 'recusado'))
            """)

        nomes = {coluna["name"] for coluna in colunas}
        # Definições fixas do programa, nunca fornecidas pelo usuário.
        novas_colunas = {
            "cliente_id": "cliente_id INTEGER REFERENCES clientes(id)",
            "validade": "validade TEXT",
            "condicoes_pagamento": "condicoes_pagamento TEXT NOT NULL DEFAULT ''",
            "observacoes": "observacoes TEXT NOT NULL DEFAULT ''",
        }
        for nome, definicao in novas_colunas.items():
            if nome not in nomes:
                conexao.execute(f"ALTER TABLE orcamentos ADD COLUMN {definicao}")


def salvar_orcamento(conexao, cliente, servicos, percentual_desconto, *,
                     validade=None, condicoes_pagamento="", observacoes="", cliente_id=None):
    """Salva cabeçalho e itens juntos: qualquer falha desfaz toda a gravação."""
    if not isinstance(cliente, str) or not cliente.strip():
        raise ValueError("O nome do cliente não pode ficar vazio.")
    if cliente_id is not None:
        validar_identificador(cliente_id)
        if buscar_cliente(conexao, cliente_id) is None:
            raise ValueError("Cliente cadastrado não encontrado.")
    orcamento = calcular_orcamento(servicos, percentual_desconto)
    emissao = datetime.now(timezone.utc)
    validade, condicoes_pagamento, observacoes = validar_condicoes(
        validade, condicoes_pagamento, observacoes,
        data_emissao=emissao.astimezone().date(),
    )
    criado_em = emissao.isoformat(timespec="seconds")

    # Os parâmetros (?) mantêm os dados separados dos comandos SQL.
    with conexao:
        cursor = conexao.execute(
            """INSERT INTO orcamentos
               (cliente, percentual_desconto, criado_em, validade, condicoes_pagamento, observacoes, cliente_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cliente.strip(), str(percentual_desconto), criado_em,
             validade, condicoes_pagamento, observacoes, cliente_id),
        )
        identificador = cursor.lastrowid
        conexao.executemany(
            """INSERT INTO itens_orcamento
               (orcamento_id, nome, quantidade, valor_unitario_centavos)
               VALUES (?, ?, ?, ?)""",
            [
                (identificador, item["nome"], item["quantidade"],
                 int(item["valor_unitario"] * 100))
                for item in orcamento["servicos"]
            ],
        )
    return identificador


def listar_orcamentos(conexao, status=None, cliente=None, cliente_id=None):
    """Filtra por status e parte literal do nome, mantendo contagem e ordem."""
    if status is not None and status not in ("pendente", "aprovado", "recusado"):
        raise ValueError("O status deve ser pendente, aprovado ou recusado.")
    if cliente is not None and not isinstance(cliente, str):
        raise ValueError("O filtro de cliente deve ser um texto.")
    if cliente_id is not None:
        validar_identificador(cliente_id)
    termo = cliente.strip() if cliente is not None else ""
    # ! é o escape do LIKE: %, _ e ! digitados são tratados literalmente.
    termo = termo.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    padrao = f"%{termo}%" if termo else None
    registros = conexao.execute("""
        SELECT
            o.id,
            o.cliente,
            o.cliente_id,
            o.criado_em,
            o.status,
            COUNT(i.id) AS quantidade_servicos
        FROM orcamentos AS o
        LEFT JOIN itens_orcamento AS i
            ON i.orcamento_id = o.id
        WHERE (? IS NULL OR o.status = ?)
          AND (? IS NULL OR o.cliente LIKE ? ESCAPE '!')
          AND (? IS NULL OR o.cliente_id = ?)
        GROUP BY o.id, o.cliente, o.cliente_id, o.criado_em, o.status
        ORDER BY o.id DESC
    """, (status, status, padrao, padrao, cliente_id, cliente_id)).fetchall()

    return [dict(registro) for registro in registros]


def validar_identificador(identificador):
    """Valida a chave inteira usada pelo SQLite."""
    if type(identificador) is not int or not 1 <= identificador <= 2**63 - 1:
        raise ValueError("O identificador deve ser um inteiro positivo de até 9223372036854775807.")


def alterar_status(conexao, identificador, novo_status):
    """Atualiza o status; retorna False se o orçamento não existir."""
    validar_identificador(identificador)
    if novo_status not in ("pendente", "aprovado", "recusado"):
        raise ValueError("O status deve ser pendente, aprovado ou recusado.")

    with conexao:
        cursor = conexao.execute(
            "UPDATE orcamentos SET status = ? WHERE id = ?",
            (novo_status, identificador),
        )
    return cursor.rowcount == 1


def buscar_orcamento(conexao, identificador):
    """Retorna os detalhes recalculados, ou None se o identificador não existir."""
    validar_identificador(identificador)
    registro = conexao.execute(
        """SELECT id, cliente, cliente_id, percentual_desconto, criado_em, status,
                  validade, condicoes_pagamento, observacoes
           FROM orcamentos WHERE id = ?""",
        (identificador,),
    ).fetchone()
    if registro is None:
        return None

    servicos = [
        {chave: valor for chave, valor in item.items() if chave != "id"}
        for item in listar_itens_orcamento(conexao, identificador)
    ]
    orcamento = calcular_orcamento(servicos, Decimal(registro["percentual_desconto"]))
    return {
        "id": registro["id"], "cliente": registro["cliente"], "cliente_id": registro["cliente_id"],
        "criado_em": registro["criado_em"], "status": registro["status"],
        "validade": registro["validade"],
        "condicoes_pagamento": registro["condicoes_pagamento"],
        "observacoes": registro["observacoes"], **orcamento,
    }


def duplicar_orcamento(conexao, identificador):
    """Cria uma cópia pendente; retorna seu id ou None se o original não existir."""
    original = buscar_orcamento(conexao, identificador)
    if original is None:
        return None
    return salvar_orcamento(
        conexao, original["cliente"], original["servicos"],
        original["percentual_desconto"], validade=original["validade"],
        condicoes_pagamento=original["condicoes_pagamento"], observacoes=original["observacoes"],
        cliente_id=original["cliente_id"],
    )


def editar_orcamento(conexao, identificador, cliente, percentual_desconto):
    """Edita cliente e desconto; retorna False quando o orçamento não existe."""
    validar_identificador(identificador)
    if not isinstance(cliente, str) or not cliente.strip():
        raise ValueError("O nome do cliente não pode ficar vazio.")
    with conexao:
        original = buscar_orcamento(conexao, identificador)
        if original is None:
            return False
        # Reutiliza as regras atuais antes de gravar qualquer alteração.
        calcular_orcamento(original["servicos"], percentual_desconto)
        cursor = conexao.execute(
            "UPDATE orcamentos SET cliente = ?, percentual_desconto = ?, cliente_id = ? WHERE id = ?",
            (cliente.strip(), str(percentual_desconto),
             original["cliente_id"] if cliente.strip() == original["cliente"] else None,
             identificador),
        )
    return cursor.rowcount == 1


def listar_itens_orcamento(conexao, identificador):
    """Retorna itens com seus IDs para seleção e edição dentro do orçamento."""
    validar_identificador(identificador)
    registros = conexao.execute(
        """SELECT id, nome, quantidade, valor_unitario_centavos
           FROM itens_orcamento WHERE orcamento_id = ? ORDER BY id""",
        (identificador,),
    ).fetchall()
    return [
        {"id": registro["id"], **criar_item(
            registro["nome"], registro["quantidade"],
            Decimal(registro["valor_unitario_centavos"]) / 100,
        )}
        for registro in registros
    ]


def editar_item(conexao, orcamento_id, item_id, nome, quantidade, valor_unitario):
    """Edita um item pertencente ao orçamento; retorna False se não encontrado."""
    validar_identificador(orcamento_id)
    validar_identificador(item_id)
    novo_item = criar_item(nome, quantidade, valor_unitario)
    with conexao:
        original = buscar_orcamento(conexao, orcamento_id)
        if original is None:
            return False
        itens = listar_itens_orcamento(conexao, orcamento_id)
        if not any(item["id"] == item_id for item in itens):
            return False
        servicos = [novo_item if item["id"] == item_id else item for item in itens]
        calcular_orcamento(servicos, original["percentual_desconto"])
        cursor = conexao.execute(
            """UPDATE itens_orcamento
               SET nome = ?, quantidade = ?, valor_unitario_centavos = ?
               WHERE id = ? AND orcamento_id = ?""",
            (novo_item["nome"], novo_item["quantidade"],
             int(novo_item["valor_unitario"] * 100), item_id, orcamento_id),
        )
    return cursor.rowcount == 1


def adicionar_item(conexao, orcamento_id, nome, quantidade, valor_unitario):
    """Inclui um serviço; retorna seu ID ou None se o orçamento não existir."""
    validar_identificador(orcamento_id)
    novo_item = criar_item(nome, quantidade, valor_unitario)
    with conexao:
        original = buscar_orcamento(conexao, orcamento_id)
        if original is None:
            return None
        calcular_orcamento(
            [*original["servicos"], novo_item], original["percentual_desconto"]
        )
        cursor = conexao.execute(
            """INSERT INTO itens_orcamento
               (orcamento_id, nome, quantidade, valor_unitario_centavos)
               VALUES (?, ?, ?, ?)""",
            (orcamento_id, novo_item["nome"], novo_item["quantidade"],
             int(novo_item["valor_unitario"] * 100)),
        )
    return cursor.lastrowid


def remover_item(conexao, orcamento_id, item_id):
    """Remove um serviço do orçamento, preservando ao menos um item."""
    validar_identificador(orcamento_id)
    validar_identificador(item_id)
    with conexao:
        itens = listar_itens_orcamento(conexao, orcamento_id)
        if not any(item["id"] == item_id for item in itens):
            return False
        if len(itens) == 1:
            raise ValueError("Não é possível remover o último serviço do orçamento.")
        cursor = conexao.execute(
            "DELETE FROM itens_orcamento WHERE id = ? AND orcamento_id = ?",
            (item_id, orcamento_id),
        )
    return cursor.rowcount == 1


def buscar_prestador(conexao):
    """Retorna a configuração local, ou None antes do primeiro cadastro."""
    registro = conexao.execute(
        "SELECT nome, contato FROM configuracao_prestador WHERE id = 1"
    ).fetchone()
    return dict(registro) if registro is not None else None


def salvar_prestador(conexao, nome, contato=""):
    nome = validar_texto(nome, "Nome do prestador", obrigatorio=True)
    contato = validar_texto(contato, "Contato")
    with conexao:
        conexao.execute(
            """INSERT INTO configuracao_prestador (id, nome, contato) VALUES (1, ?, ?)
               ON CONFLICT(id) DO UPDATE SET nome = excluded.nome, contato = excluded.contato""",
            (nome, contato),
        )


def editar_condicoes(conexao, identificador, validade=None, condicoes_pagamento="", observacoes=""):
    """Atualiza os campos comerciais juntos; False indica orçamento inexistente."""
    validar_identificador(identificador)
    with conexao:
        registro = conexao.execute(
            "SELECT criado_em, validade FROM orcamentos WHERE id = ?", (identificador,)
        ).fetchone()
        if registro is None:
            return False
        # Datas legadas são preservadas quando somente outros campos são editados.
        emissao = (datetime.fromisoformat(registro["criado_em"]).astimezone().date()
                   if validade != registro["validade"] else None)
        validade, condicoes_pagamento, observacoes = validar_condicoes(
            validade, condicoes_pagamento, observacoes, data_emissao=emissao
        )
        cursor = conexao.execute(
            """UPDATE orcamentos SET validade = ?, condicoes_pagamento = ?, observacoes = ?
               WHERE id = ?""",
            (validade, condicoes_pagamento, observacoes, identificador),
        )
    return cursor.rowcount == 1


def cadastrar_cliente(conexao, nome, contato=""):
    """Cadastra uma pessoa/empresa; nomes iguais recebem IDs independentes."""
    nome = validar_texto(nome, "Nome do cliente", obrigatorio=True)
    contato = validar_texto(contato, "Contato")
    criado_em = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conexao:
        cursor = conexao.execute(
            "INSERT INTO clientes (nome, contato, criado_em) VALUES (?, ?, ?)",
            (nome, contato, criado_em),
        )
    return cursor.lastrowid


def listar_clientes(conexao, nome=None):
    """Lista todos ou busca por parte literal do nome, do ID mais recente ao antigo."""
    if nome is not None and not isinstance(nome, str):
        raise ValueError("O filtro de nome deve ser um texto.")
    termo = nome.strip() if nome is not None else ""
    termo = termo.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    padrao = f"%{termo}%" if termo else None
    registros = conexao.execute(
        """SELECT id, nome, contato, criado_em FROM clientes
           WHERE (? IS NULL OR nome LIKE ? ESCAPE '!') ORDER BY id DESC""",
        (padrao, padrao),
    ).fetchall()
    return [dict(registro) for registro in registros]


def buscar_cliente(conexao, identificador):
    """Busca pelo ID, sem presumir identidade a partir do nome."""
    validar_identificador(identificador)
    registro = conexao.execute(
        "SELECT id, nome, contato, criado_em FROM clientes WHERE id = ?", (identificador,)
    ).fetchone()
    return dict(registro) if registro is not None else None


def editar_cliente(conexao, identificador, nome, contato=""):
    """Edita somente o cadastro, preservando o nome histórico das propostas."""
    validar_identificador(identificador)
    nome = validar_texto(nome, "Nome do cliente", obrigatorio=True)
    contato = validar_texto(contato, "Contato")
    with conexao:
        cursor = conexao.execute(
            "UPDATE clientes SET nome = ?, contato = ? WHERE id = ?",
            (nome, contato, identificador),
        )
    return cursor.rowcount == 1


def vincular_cliente(conexao, orcamento_id, cliente_id):
    """Associa a proposta sem alterar seu nome histórico; False se não encontrada."""
    validar_identificador(orcamento_id)
    validar_identificador(cliente_id)
    with conexao:
        if buscar_cliente(conexao, cliente_id) is None:
            raise ValueError("Cliente cadastrado não encontrado.")
        cursor = conexao.execute(
            "UPDATE orcamentos SET cliente_id = ? WHERE id = ?",
            (cliente_id, orcamento_id),
        )
    return cursor.rowcount == 1
