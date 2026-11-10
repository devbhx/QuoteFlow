from decimal import Decimal
import sqlite3

import pytest

from dados_comerciais import validar_condicoes
from orcamento import criar_item
from repositorio import (
    abrir_banco, buscar_prestador, salvar_prestador, salvar_orcamento,
    buscar_orcamento, editar_condicoes, duplicar_orcamento, alterar_status,
)


@pytest.fixture
def conexao(tmp_path):
    banco = abrir_banco(tmp_path / "comercial.db")
    yield banco
    banco.close()


def criar(conexao):
    return salvar_orcamento(conexao, "Cliente fictício", [
        criar_item("Serviço", 2, Decimal("10"))], Decimal("10"))


def test_prestador_configuracao_unica_e_validacao(conexao):
    assert buscar_prestador(conexao) is None
    salvar_prestador(conexao, " Empresa exemplo ", " contato@example.com ")
    assert buscar_prestador(conexao) == {"nome": "Empresa exemplo", "contato": "contato@example.com"}
    salvar_prestador(conexao, "Outro nome", "")
    assert buscar_prestador(conexao) == {"nome": "Outro nome", "contato": ""}
    assert conexao.execute("SELECT COUNT(*) FROM configuracao_prestador").fetchone()[0] == 1
    with pytest.raises(ValueError):
        salvar_prestador(conexao, "  ", "novo contato")
    assert buscar_prestador(conexao) == {"nome": "Outro nome", "contato": ""}


@pytest.mark.parametrize("nome, contato", [(None, ""), ("Empresa", None)])
def test_prestador_rejeita_tipos_invalidos(conexao, nome, contato):
    with pytest.raises(ValueError):
        salvar_prestador(conexao, nome, contato)
    assert buscar_prestador(conexao) is None


def test_edicao_comercial_preserva_orcamento_e_duplicacao(conexao):
    identificador = criar(conexao)
    alterar_status(conexao, identificador, "aprovado")
    antes = buscar_orcamento(conexao, identificador)
    assert antes["validade"] is None
    assert antes["condicoes_pagamento"] == antes["observacoes"] == ""
    assert editar_condicoes(conexao, identificador, "2026-12-31", " Pix ", " Com acentos: instalação ")
    depois = buscar_orcamento(conexao, identificador)
    assert depois == {**antes, "validade": "2026-12-31", "condicoes_pagamento": "Pix",
                     "observacoes": "Com acentos: instalação"}
    copia = buscar_orcamento(conexao, duplicar_orcamento(conexao, identificador))
    for campo in ("validade", "condicoes_pagamento", "observacoes"):
        assert copia[campo] == depois[campo]
    assert copia["status"] == "pendente"
    assert editar_condicoes(conexao, identificador)
    assert buscar_orcamento(conexao, identificador)["validade"] is None
    assert buscar_orcamento(conexao, copia["id"])["validade"] == "2026-12-31"


@pytest.mark.parametrize("validade, pagamento, observacoes", [
    ("2026-02-30", "Pix", ""), ("31/12/2026", "Pix", ""),
    ("20261231", "Pix", ""), ("", "Pix", ""), (123, "Pix", ""),
    (None, None, ""), (None, "Pix", 123),
])
def test_condicoes_invalidas_preservam_dados(conexao, validade, pagamento, observacoes):
    identificador = criar(conexao)
    antes = buscar_orcamento(conexao, identificador)
    with pytest.raises(ValueError):
        editar_condicoes(conexao, identificador, validade, pagamento, observacoes)
    assert buscar_orcamento(conexao, identificador) == antes


def test_condicoes_data_passada_e_bissexta():
    assert validar_condicoes("2024-02-29", "", "")[0] == "2024-02-29"


def test_edicao_comercial_inexistente_e_id_invalido(conexao):
    assert editar_condicoes(conexao, 999) is False
    with pytest.raises(ValueError):
        editar_condicoes(conexao, True)


def test_falha_comercial_nao_salva_parcialmente(conexao):
    identificador = criar(conexao)
    antes = buscar_orcamento(conexao, identificador)
    conexao.execute("""CREATE TRIGGER falhar_condicoes BEFORE UPDATE ON orcamentos
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        editar_condicoes(conexao, identificador, "2026-12-31", "Pix", "Novo")
    assert buscar_orcamento(conexao, identificador) == antes


def test_migracao_e_persistencia_dos_dados_comerciais(tmp_path):
    caminho = tmp_path / "antigo.db"
    antigo = sqlite3.connect(caminho)
    antigo.executescript("""
        CREATE TABLE orcamentos (
            id INTEGER PRIMARY KEY, cliente TEXT NOT NULL,
            percentual_desconto TEXT NOT NULL, criado_em TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente'
        );
        CREATE TABLE itens_orcamento (
            id INTEGER PRIMARY KEY, orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id),
            nome TEXT NOT NULL, quantidade INTEGER NOT NULL, valor_unitario_centavos INTEGER NOT NULL
        );
        INSERT INTO orcamentos VALUES (3, 'Cliente fictício', '10', '2026-11-10T00:00:00+00:00', 'aprovado');
        INSERT INTO itens_orcamento VALUES (7, 3, 'Serviço', 2, 1000);
    """)
    antigo.close()
    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, 3)["total"] == Decimal("18.00")
        assert buscar_orcamento(banco, 3)["status"] == "aprovado"
        assert buscar_orcamento(banco, 3)["validade"] is None
        assert buscar_prestador(banco) is None
        salvar_prestador(banco, "Empresa exemplo", "contato@example.com")
        editar_condicoes(banco, 3, "2026-12-31", "Pix", "Observação fictícia")
    finally:
        banco.close()
    banco = abrir_banco(caminho)
    try:
        assert buscar_prestador(banco)["nome"] == "Empresa exemplo"
        resultado = buscar_orcamento(banco, 3)
        assert resultado["validade"] == "2026-12-31"
        assert resultado["condicoes_pagamento"] == "Pix"
        assert resultado["observacoes"] == "Observação fictícia"
        assert resultado["total"] == Decimal("18.00")
        assert banco.execute("SELECT id FROM itens_orcamento").fetchone()[0] == 7
        assert len([r for r in banco.execute("PRAGMA table_info(orcamentos)") if r["name"] == "validade"]) == 1
    finally:
        banco.close()


@pytest.mark.parametrize("validade, permitida", [
    ("2026-11-09", False), ("2026-11-10", True), ("2026-11-11", True), (None, True),
])
def test_validade_comparada_com_emissao(validade, permitida):
    from datetime import date

    if permitida:
        assert validar_condicoes(validade, "Pix", "", data_emissao=date(2026, 11, 10))[0] == validade
    else:
        with pytest.raises(ValueError, match="anterior à data de emissão"):
            validar_condicoes(validade, "Pix", "", data_emissao=date(2026, 11, 10))


def test_criacao_rejeita_validade_anterior_sem_gravar(conexao):
    with pytest.raises(ValueError, match="anterior à data de emissão"):
        salvar_orcamento(conexao, "Cliente fictício", [criar_item("A", 1, Decimal("10"))],
                         Decimal("0"), validade="2000-01-01")
    assert conexao.execute("SELECT COUNT(*) FROM orcamentos").fetchone()[0] == 0
    assert conexao.execute("SELECT COUNT(*) FROM itens_orcamento").fetchone()[0] == 0


def test_edicao_rejeita_validade_anterior_sem_salvar_outros_campos(conexao):
    identificador = criar(conexao)
    antes = buscar_orcamento(conexao, identificador)
    with pytest.raises(ValueError, match="anterior à data de emissão"):
        editar_condicoes(conexao, identificador, "2000-01-01", "Não salvar", "Não salvar")
    assert buscar_orcamento(conexao, identificador) == antes


def test_validade_passada_pode_ser_posterior_a_emissao_antiga(conexao):
    identificador = criar(conexao)
    with conexao:
        conexao.execute("UPDATE orcamentos SET criado_em = ? WHERE id = ?",
                        ("2020-01-01T12:00:00-03:00", identificador))
    assert editar_condicoes(conexao, identificador, "2020-01-02", "Pix", "Histórico")
    assert buscar_orcamento(conexao, identificador)["validade"] == "2020-01-02"


def test_validade_usa_mesma_data_local_exibida_no_pdf(conexao):
    from datetime import datetime, timedelta

    identificador = criar(conexao)
    criado_em = "2026-11-10T00:30:00+14:00"
    emissao_local = datetime.fromisoformat(criado_em).astimezone().date()
    with conexao:
        conexao.execute("UPDATE orcamentos SET criado_em = ? WHERE id = ?", (criado_em, identificador))
    with pytest.raises(ValueError):
        editar_condicoes(conexao, identificador, (emissao_local - timedelta(days=1)).isoformat())
    assert editar_condicoes(conexao, identificador, emissao_local.isoformat())


def test_reabertura_preserva_validade_legada_e_edicao_de_outros_campos(tmp_path):
    caminho = tmp_path / "legado.db"
    banco = abrir_banco(caminho)
    try:
        identificador = criar(banco)
        with banco:
            banco.execute("""UPDATE orcamentos SET criado_em = ?, validade = ?,
                condicoes_pagamento = ?, observacoes = ? WHERE id = ?""",
                ("2026-11-10T12:00:00-03:00", "2026-11-09", "Pix", "Registro antigo", identificador))
        antes = buscar_orcamento(banco, identificador)
    finally:
        banco.close()
    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, identificador) == antes
        assert editar_condicoes(banco, identificador, antes["validade"], "Boleto", "Observação nova")
        depois = buscar_orcamento(banco, identificador)
        assert depois == {**antes, "condicoes_pagamento": "Boleto", "observacoes": "Observação nova"}
        assert editar_condicoes(banco, identificador, None, "Boleto", "Observação nova")
        assert buscar_orcamento(banco, identificador)["validade"] is None
    finally:
        banco.close()


def test_duplicacao_com_nova_emissao_nao_copia_validade_anterior(conexao):
    identificador = criar(conexao)
    with conexao:
        conexao.execute("UPDATE orcamentos SET criado_em = ?, validade = ? WHERE id = ?",
                        ("2000-01-01T12:00:00-03:00", "2000-01-02", identificador))
    antes = buscar_orcamento(conexao, identificador)
    with pytest.raises(ValueError, match="anterior à data de emissão"):
        duplicar_orcamento(conexao, identificador)
    assert buscar_orcamento(conexao, identificador) == antes
    assert conexao.execute("SELECT COUNT(*) FROM orcamentos").fetchone()[0] == 1
