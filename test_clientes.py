from decimal import Decimal
import sqlite3

import pytest

import main
import terminal_clientes
from orcamento import criar_item
from repositorio import (
    abrir_banco, cadastrar_cliente, listar_clientes, salvar_orcamento, buscar_orcamento,
    buscar_cliente, listar_orcamentos, editar_orcamento, duplicar_orcamento, editar_cliente, vincular_cliente,
)


@pytest.fixture
def conexao(tmp_path):
    banco = abrir_banco(tmp_path / "clientes.db")
    yield banco
    banco.close()


def test_cadastro_contato_opcional_e_nomes_iguais(conexao):
    assert listar_clientes(conexao) == []
    primeiro = cadastrar_cliente(conexao, " Cliente fictício ", " contato@example.com ")
    segundo = cadastrar_cliente(conexao, "Cliente fictício")
    registros = listar_clientes(conexao)
    assert [c["id"] for c in registros] == [segundo, primeiro]
    assert [c["nome"] for c in registros] == ["Cliente fictício"] * 2
    assert [c["contato"] for c in registros] == ["", "contato@example.com"]
    assert all(c["criado_em"].endswith("+00:00") for c in registros)


@pytest.mark.parametrize("nome, contato", [("", ""), ("  ", ""), (None, ""), (1, ""), ("Cliente", None)])
def test_cadastro_invalido_nao_grava(conexao, nome, contato):
    with pytest.raises(ValueError):
        cadastrar_cliente(conexao, nome, contato)
    assert listar_clientes(conexao) == []


@pytest.mark.parametrize("termo", ["bruno", "Bruno", " Henrique "])
def test_busca_parcial(conexao, termo):
    identificador = cadastrar_cliente(conexao, "Bruno Henrique (fictício)")
    cadastrar_cliente(conexao, "Ana (fictícia)")
    assert [c["id"] for c in listar_clientes(conexao, termo)] == [identificador]
    assert listar_clientes(conexao, "inexistente") == []


@pytest.mark.parametrize("termo", ["%", "_", "!", "D'Ávila", "' OR 1=1 --"])
def test_busca_literal_e_sql_parametrizado(conexao, termo):
    identificador = cadastrar_cliente(conexao, f"Cliente fictício {termo}")
    cadastrar_cliente(conexao, "Outro cliente")
    assert [c["id"] for c in listar_clientes(conexao, termo)] == [identificador]


@pytest.mark.parametrize("nome", [None, "", "  "])
def test_filtro_vazio_lista_todos(conexao, nome):
    cadastrar_cliente(conexao, "Cliente fictício")
    assert listar_clientes(conexao, nome) == listar_clientes(conexao)


def test_filtro_tipo_invalido(conexao):
    with pytest.raises(ValueError):
        listar_clientes(conexao, 1)


def test_falha_no_cadastro_nao_grava(conexao):
    conexao.execute("""CREATE TRIGGER falhar_cliente BEFORE INSERT ON clientes
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        cadastrar_cliente(conexao, "Cliente fictício")
    assert listar_clientes(conexao) == []


def test_tabela_nova_preserva_orcamentos_sem_importacao_automatica(tmp_path):
    caminho = tmp_path / "antigo.db"
    banco = abrir_banco(caminho)
    identificador = salvar_orcamento(banco, "Nome legado fictício", [
        criar_item("Serviço", 1, Decimal("10"))], Decimal("0"))
    antes = buscar_orcamento(banco, identificador)
    # Simula um banco da versão anterior, sem a nova tabela.
    banco.execute("DROP TABLE clientes")
    banco.close()
    banco = abrir_banco(caminho)
    try:
        assert listar_clientes(banco) == []
        assert buscar_orcamento(banco, identificador) == antes
        cadastrar_cliente(banco, "Nome legado fictício", "contato@example.com")
        assert buscar_orcamento(banco, identificador) == antes
    finally:
        banco.close()
    banco = abrir_banco(caminho)
    try:
        assert len(listar_clientes(banco)) == 1
        assert listar_clientes(banco)[0]["contato"] == "contato@example.com"
    finally:
        banco.close()


def test_menu_cadastra_busca_e_persiste(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    entradas = iter(["14", "", "13", " ", "Cliente fictício", "contato@example.com", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Nenhum cliente cadastrado." in saida
    assert "o nome não pode ficar vazio" in saida
    assert "Cliente cadastrado com o número 1." in saida
    entradas = iter(["14", "fictício", "14", "ausente", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "#1 | Cliente fictício | contato@example.com" in saida
    assert "Nenhum cliente encontrado." in saida


def test_menu_cliente_sem_contato(monkeypatch, capsys, tmp_path):
    entradas = iter(["13", "Cliente fictício", "", "14", "", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(tmp_path / "teste.db")
    assert "#1 | Cliente fictício | Contato não informado" in capsys.readouterr().out


def test_menu_falha_de_gravacao_nao_anuncia_sucesso(monkeypatch, capsys, tmp_path):
    def falhar(*args):
        raise sqlite3.OperationalError("falha simulada")

    monkeypatch.setattr(terminal_clientes, "cadastrar_cliente", falhar)
    entradas = iter(["13", "Cliente fictício", "", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Erro ao acessar o banco" in saida
    assert "Cliente cadastrado com" not in saida


def test_vinculo_por_id_separa_homonimos_e_preserva_nome(conexao):
    primeiro = cadastrar_cliente(conexao, "Cliente fictício")
    segundo = cadastrar_cliente(conexao, "Cliente fictício")
    servicos = [criar_item("A", 1, Decimal("10"))]
    orcamento = salvar_orcamento(conexao, "Cliente fictício", servicos, Decimal("0"), cliente_id=primeiro)
    outro = salvar_orcamento(conexao, "Cliente fictício", servicos, Decimal("0"), cliente_id=segundo)
    salvar_orcamento(conexao, "Cliente fictício", servicos, Decimal("0"))
    assert [r["id"] for r in listar_orcamentos(conexao, cliente_id=primeiro)] == [orcamento]
    assert [r["id"] for r in listar_orcamentos(conexao, cliente_id=segundo)] == [outro]
    assert buscar_orcamento(conexao, orcamento)["cliente_id"] == primeiro
    with conexao:
        conexao.execute("UPDATE clientes SET nome = ? WHERE id = ?", ("Nome atualizado fictício", primeiro))
    assert buscar_cliente(conexao, primeiro)["nome"] == "Nome atualizado fictício"
    assert buscar_orcamento(conexao, orcamento)["cliente"] == "Cliente fictício"
    copia = duplicar_orcamento(conexao, orcamento)
    assert buscar_orcamento(conexao, copia)["cliente_id"] == primeiro
    assert buscar_orcamento(conexao, copia)["cliente"] == "Cliente fictício"
    assert [r["id"] for r in listar_orcamentos(conexao, cliente_id=primeiro)] == [copia, orcamento]


def test_editar_desconto_mantem_vinculo_e_mudar_nome_desvincula(conexao):
    cliente_id = cadastrar_cliente(conexao, "Cliente fictício")
    identificador = salvar_orcamento(conexao, "Cliente fictício", [criar_item("A", 1, Decimal("10"))],
                                    Decimal("0"), cliente_id=cliente_id)
    assert editar_orcamento(conexao, identificador, " Cliente fictício ", Decimal("10"))
    assert buscar_orcamento(conexao, identificador)["cliente_id"] == cliente_id
    assert editar_orcamento(conexao, identificador, "Outro nome fictício", Decimal("10"))
    assert buscar_orcamento(conexao, identificador)["cliente_id"] is None
    assert listar_orcamentos(conexao, cliente_id=cliente_id) == []
    assert buscar_cliente(conexao, cliente_id)["nome"] == "Cliente fictício"


@pytest.mark.parametrize("identificador", [0, -1, True, "1", 2**63, 999])
def test_vinculo_invalido_nao_grava(conexao, identificador):
    with pytest.raises(ValueError):
        salvar_orcamento(conexao, "Cliente fictício", [criar_item("A", 1, Decimal("10"))],
                         Decimal("0"), cliente_id=identificador)
    assert listar_orcamentos(conexao) == []


def test_buscar_cliente_inexistente_e_id_invalido(conexao):
    assert buscar_cliente(conexao, 999) is None
    with pytest.raises(ValueError):
        buscar_cliente(conexao, True)
    with pytest.raises(ValueError):
        listar_orcamentos(conexao, cliente_id=True)


def test_chave_estrangeira_impede_vinculo_inexistente(conexao):
    identificador = salvar_orcamento(conexao, "Cliente fictício", [criar_item("A", 1, Decimal("10"))], Decimal("0"))
    with pytest.raises(sqlite3.IntegrityError):
        with conexao:
            conexao.execute("UPDATE orcamentos SET cliente_id = 999 WHERE id = ?", (identificador,))
    assert buscar_orcamento(conexao, identificador)["cliente_id"] is None


def test_migracao_cria_vinculo_nulo_sem_associar_nomes(tmp_path):
    caminho = tmp_path / "legado.db"
    banco = sqlite3.connect(caminho)
    banco.executescript("""
        CREATE TABLE orcamentos (
            id INTEGER PRIMARY KEY, cliente TEXT NOT NULL, percentual_desconto TEXT NOT NULL,
            criado_em TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pendente', validade TEXT,
            condicoes_pagamento TEXT NOT NULL DEFAULT '', observacoes TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE clientes (
            id INTEGER PRIMARY KEY, nome TEXT NOT NULL, contato TEXT NOT NULL DEFAULT '', criado_em TEXT NOT NULL
        );
        CREATE TABLE itens_orcamento (
            id INTEGER PRIMARY KEY, orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id),
            nome TEXT NOT NULL, quantidade INTEGER NOT NULL, valor_unitario_centavos INTEGER NOT NULL
        );
        INSERT INTO clientes VALUES (2, 'Cliente fictício', '', '2026-11-10T12:00:00+00:00');
        INSERT INTO orcamentos VALUES (7, 'Cliente fictício', '0', '2026-11-10T12:00:00+00:00', 'aprovado', NULL, '', 'Legado');
        INSERT INTO itens_orcamento VALUES (9, 7, 'A', 1, 1000);
    """)
    banco.close()
    banco = abrir_banco(caminho)
    try:
        resultado = buscar_orcamento(banco, 7)
        assert resultado["cliente_id"] is None
        assert resultado["cliente"] == "Cliente fictício"
        assert resultado["status"] == "aprovado"
        assert resultado["total"] == Decimal("10.00")
        assert resultado["observacoes"] == "Legado"
        assert listar_orcamentos(banco, cliente_id=2) == []
        novo_id = salvar_orcamento(banco, "Cliente fictício", resultado["servicos"], Decimal("0"), cliente_id=2)
    finally:
        banco.close()
    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, 7)["cliente_id"] is None
        assert buscar_orcamento(banco, novo_id)["cliente_id"] == 2
        assert [r["id"] for r in listar_orcamentos(banco, cliente_id=2)] == [novo_id]
    finally:
        banco.close()


def test_menu_seleciona_cliente_e_mostra_historico(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    entradas = iter([
        "13", "Cliente fictício", "contato@example.com", "1", "id:1", "A", "10", "1", "n", "0",
        "5", "1", "15", "1", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Cliente selecionado: #1 | Cliente fictício" in saida
    assert "Histórico do cliente #1 | Cliente fictício" in saida
    assert "#2 | Cliente fictício |" in saida
    assert "#1 | Cliente fictício |" in saida
    entradas = iter(["6", "1", "Outro nome fictício", "", "15", "1", "3", "1", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "desfaz o vínculo" in saida
    assert "#2 | Cliente fictício |" in saida
    assert "#1 | Cliente fictício |" not in saida
    assert "Cliente: Outro nome fictício" in saida


def test_menu_cliente_invalido_pode_voltar_para_nome_manual(monkeypatch, capsys, tmp_path):
    from test_main import fornecer_entradas

    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "1", "id:abc", "id:999", "Cliente manual fictício", "A", "10", "1", "n", "0", "0",
    ])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "ID de cliente inteiro positivo válido" in saida
    assert "Cliente cadastrado não encontrado" in saida
    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, 1)["cliente_id"] is None
    finally:
        banco.close()


def test_menu_historico_vazio_e_identificadores_invalidos(monkeypatch, capsys, tmp_path):
    entradas = iter(["13", "Cliente fictício", "", "15", "1", "15", "abc", "15", "999", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Nenhum orçamento vinculado a este cliente." in saida
    assert "identificador inteiro positivo válido" in saida
    assert "Cliente cadastrado não encontrado." in saida


def test_editar_cliente_preserva_identidade_e_propostas(conexao):
    cliente_id = cadastrar_cliente(conexao, "Nome original fictício", "original@example.com")
    outro_id = cadastrar_cliente(conexao, "Outro cliente fictício")
    antes = buscar_cliente(conexao, cliente_id)
    outro_antes = buscar_cliente(conexao, outro_id)
    orcamento_id = salvar_orcamento(conexao, antes["nome"], [criar_item("A", 1, Decimal("10"))],
                                   Decimal("0"), cliente_id=cliente_id)
    proposta_antes = buscar_orcamento(conexao, orcamento_id)
    assert editar_cliente(conexao, cliente_id, " Novo nome fictício ", " novo@example.com ") is True
    assert buscar_cliente(conexao, cliente_id) == {
        **antes, "nome": "Novo nome fictício", "contato": "novo@example.com"}
    assert buscar_cliente(conexao, outro_id) == outro_antes
    assert buscar_orcamento(conexao, orcamento_id) == proposta_antes
    assert listar_orcamentos(conexao, cliente_id=cliente_id)[0]["id"] == orcamento_id
    assert listar_clientes(conexao, "Novo nome")[0]["id"] == cliente_id
    assert listar_clientes(conexao, "Nome original") == []
    assert editar_cliente(conexao, cliente_id, "Novo nome fictício", "") is True
    assert buscar_cliente(conexao, cliente_id)["contato"] == ""


@pytest.mark.parametrize("nome, contato", [("", ""), ("  ", ""), (None, ""), ("Novo", None)])
def test_edicao_cliente_invalida_preserva_cadastro(conexao, nome, contato):
    identificador = cadastrar_cliente(conexao, "Cliente fictício", "contato@example.com")
    antes = buscar_cliente(conexao, identificador)
    with pytest.raises(ValueError):
        editar_cliente(conexao, identificador, nome, contato)
    assert buscar_cliente(conexao, identificador) == antes


@pytest.mark.parametrize("identificador", [0, True, "1", 2**63])
def test_editar_cliente_identificador_invalido(conexao, identificador):
    with pytest.raises(ValueError):
        editar_cliente(conexao, identificador, "Cliente fictício")


def test_editar_cliente_inexistente(conexao):
    assert editar_cliente(conexao, 999, "Cliente fictício") is False
    assert listar_clientes(conexao) == []


def test_falha_edicao_cliente_preserva_dados(conexao):
    identificador = cadastrar_cliente(conexao, "Cliente fictício", "contato@example.com")
    antes = buscar_cliente(conexao, identificador)
    conexao.execute("""CREATE TRIGGER falhar_edicao_cliente BEFORE UPDATE ON clientes
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        editar_cliente(conexao, identificador, "Novo nome", "novo@example.com")
    assert buscar_cliente(conexao, identificador) == antes


def test_menu_edicao_persiste_e_novos_orcamentos_usam_nome_atualizado(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    entradas = iter([
        "13", "Nome original fictício", "original@example.com",
        "1", "id:1", "A", "10", "1", "n", "0",
        "16", "1", "Nome atualizado fictício", "novo@example.com",
        "1", "id:1", "B", "20", "1", "n", "0", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(caminho)
    assert "Cliente #1 atualizado." in capsys.readouterr().out
    banco = abrir_banco(caminho)
    try:
        assert buscar_cliente(banco, 1)["nome"] == "Nome atualizado fictício"
        assert buscar_cliente(banco, 1)["contato"] == "novo@example.com"
        assert buscar_orcamento(banco, 1)["cliente"] == "Nome original fictício"
        assert buscar_orcamento(banco, 2)["cliente"] == "Nome atualizado fictício"
        assert [r["id"] for r in listar_orcamentos(banco, cliente_id=1)] == [2, 1]
    finally:
        banco.close()


def test_menu_edicao_manter_limpar_e_rejeitar_nome_vazio(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    entradas = iter([
        "13", "Cliente fictício", "contato@example.com",
        "16", "1", "", "", "16", "1", "  ", "Não gravar",
        "16", "1", "", "-", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(caminho)
    saida = capsys.readouterr().out
    assert saida.count("Cliente #1 atualizado.") == 2
    assert "Nome do cliente não pode ficar vazio" in saida
    assert "Nenhuma alteração foi salva." in saida
    banco = abrir_banco(caminho)
    try:
        assert buscar_cliente(banco, 1)["nome"] == "Cliente fictício"
        assert buscar_cliente(banco, 1)["contato"] == ""
    finally:
        banco.close()


@pytest.mark.parametrize("identificador", ["abc", "0", "999"])
def test_menu_edicao_cliente_id_invalido(monkeypatch, capsys, tmp_path, identificador):
    entradas = iter(["16", identificador, "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert ("Cliente cadastrado não encontrado" if identificador == "999" else
            "identificador inteiro positivo válido") in saida


def test_pdf_preserva_nome_da_proposta_apos_editar_cadastro(conexao, tmp_path):
    from pypdf import PdfReader
    from exportacao_pdf import exportar_orcamento
    from repositorio import salvar_prestador

    cliente_id = cadastrar_cliente(conexao, "Nome original fictício")
    orcamento_id = salvar_orcamento(conexao, "Nome original fictício", [criar_item("A", 1, Decimal("10"))],
                                   Decimal("0"), cliente_id=cliente_id)
    salvar_prestador(conexao, "Empresa exemplo")
    editar_cliente(conexao, cliente_id, "Nome atualizado fictício")
    caminho = exportar_orcamento(conexao, orcamento_id, tmp_path)
    conteudo = "\n".join(p.extract_text() for p in PdfReader(caminho).pages)
    assert "Nome original fictício" in conteudo
    assert "Nome atualizado fictício" not in conteudo


def test_associar_e_substituir_vinculo_preserva_proposta(conexao):
    primeiro = cadastrar_cliente(conexao, "Cliente fictício")
    segundo = cadastrar_cliente(conexao, "Cliente fictício")
    identificador = salvar_orcamento(conexao, "Nome histórico fictício", [criar_item("A", 1, Decimal("10"))], Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    for destino in (primeiro, primeiro, segundo):
        assert vincular_cliente(conexao, identificador, destino) is True
        assert buscar_orcamento(conexao, identificador) == {**antes, "cliente_id": destino}
        assert listar_orcamentos(conexao, cliente_id=destino)[0]["id"] == identificador
    assert listar_orcamentos(conexao, cliente_id=primeiro) == []


def test_vinculo_inexistente_preserva_dados(conexao):
    cliente_id = cadastrar_cliente(conexao, "Cliente fictício")
    assert vincular_cliente(conexao, 999, cliente_id) is False
    identificador = salvar_orcamento(conexao, "Histórico", [criar_item("A", 1, Decimal("10"))], Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    with pytest.raises(ValueError, match="Cliente cadastrado não encontrado"):
        vincular_cliente(conexao, identificador, 999)
    assert buscar_orcamento(conexao, identificador) == antes


@pytest.mark.parametrize("orcamento_id, cliente_id", [(0, 1), (1, True), (1, "1"), (2**63, 1)])
def test_associacao_identificadores_invalidos(conexao, orcamento_id, cliente_id):
    with pytest.raises(ValueError):
        vincular_cliente(conexao, orcamento_id, cliente_id)


def test_falha_associacao_nao_altera_proposta(conexao):
    cliente_id = cadastrar_cliente(conexao, "Cliente fictício")
    identificador = salvar_orcamento(conexao, "Histórico", [criar_item("A", 1, Decimal("10"))], Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    conexao.execute("""CREATE TRIGGER falhar_vinculo BEFORE UPDATE ON orcamentos
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        vincular_cliente(conexao, identificador, cliente_id)
    assert buscar_orcamento(conexao, identificador) == antes


def test_menu_associacao_confirma_substitui_e_persiste(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    entradas = iter([
        "13", "Cliente A fictício", "", "13", "Cliente B fictício", "",
        "1", "Nome histórico fictício", "A", "10", "1", "n", "0",
        "17", "1", "1", "talvez", "s", "17", "1", "2", " S ",
        "17", "1", "2", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Nome registrado: Nome histórico fictício" in saida
    assert "digite apenas 's' ou 'n'" in saida
    assert "vínculo atual com o cliente #1 será substituído" in saida
    assert "Orçamento #1 vinculado ao cliente #2." in saida
    assert "já está vinculado a este cliente" in saida
    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, 1)["cliente_id"] == 2
        assert buscar_orcamento(banco, 1)["cliente"] == "Nome histórico fictício"
        assert listar_orcamentos(banco, cliente_id=1) == []
        assert listar_orcamentos(banco, cliente_id=2)[0]["id"] == 1
    finally:
        banco.close()


def test_menu_cancela_associacao_preserva_vinculo(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    entradas = iter([
        "13", "Cliente A fictício", "", "13", "Cliente B fictício", "",
        "1", "id:1", "A", "10", "1", "n", "0",
        "17", "1", "2", "n", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(caminho)
    assert "Associação cancelada." in capsys.readouterr().out
    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, 1)["cliente_id"] == 1
    finally:
        banco.close()


@pytest.mark.parametrize("selecao, mensagem", [
    (["abc"], "identificador inteiro positivo válido"),
    (["999"], "Orçamento não encontrado"),
    (["1", "abc"], "identificador inteiro positivo válido"),
    (["1", "999"], "Cliente cadastrado não encontrado"),
])
def test_menu_associacao_invalida(monkeypatch, capsys, tmp_path, selecao, mensagem):
    entradas = iter(["1", "Histórico", "A", "10", "1", "n", "0", "17", *selecao, "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(tmp_path / "teste.db")
    assert mensagem in capsys.readouterr().out
