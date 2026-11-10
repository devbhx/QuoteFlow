from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sqlite3

import pytest

import main
import restauracao
import terminal_backup
from backup import criar_backup
from orcamento import criar_item
from repositorio import abrir_banco, cadastrar_cliente, salvar_orcamento, buscar_orcamento, salvar_prestador


@pytest.fixture
def conexao(tmp_path):
    banco = abrir_banco(tmp_path / "atual.db")
    yield banco
    banco.close()


def popular(conexao, nome):
    cliente_id = cadastrar_cliente(conexao, nome, "contato@example.com")
    salvar_prestador(conexao, "Empresa exemplo")
    return salvar_orcamento(conexao, nome, [criar_item("Serviço fictício", 2, Decimal("15"))],
                            Decimal("10"), cliente_id=cliente_id, condicoes_pagamento="Pix", observacoes="Fictício")


def estado(conexao):
    return {tabela: [tuple(r) for r in conexao.execute(f'SELECT * FROM {tabela} ORDER BY id')]
            for tabela in restauracao.COLUNAS}


def arquivo_backup(tmp_path):
    with closing(abrir_banco(tmp_path / "origem.db")) as origem:
        popular(origem, "Cliente do backup fictício")
        return criar_backup(origem, tmp_path / "originais"), estado(origem)


def confirmar(*args):
    return True


def test_restauracao_completa_e_backup_anterior(conexao, tmp_path):
    popular(conexao, "Cliente atual fictício")
    antes = estado(conexao)
    arquivo, esperado = arquivo_backup(tmp_path)
    bytes_antes = arquivo.read_bytes()
    seguranca = restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar,
                                            pasta_seguranca=tmp_path / "seguranca")
    assert estado(conexao) == esperado
    assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert arquivo.read_bytes() == bytes_antes
    with closing(sqlite3.connect(seguranca)) as anterior:
        assert estado(anterior) == antes
    identificador = cadastrar_cliente(conexao, "Novo cliente fictício")
    assert identificador > 1
    caminho = Path(conexao.execute("PRAGMA database_list").fetchone()[2])
    with closing(abrir_banco(caminho)) as reaberto:
        assert buscar_orcamento(reaberto, 1)["cliente"] == "Cliente do backup fictício"


def test_cancelamento_nao_cria_seguranca_nem_altera(conexao, tmp_path):
    popular(conexao, "Atual")
    antes = estado(conexao)
    arquivo, _ = arquivo_backup(tmp_path)
    pasta = tmp_path / "seguranca"
    assert restauracao.restaurar_backup(conexao, arquivo, confirmar=lambda *args: False,
                                       pasta_seguranca=pasta) is None
    assert estado(conexao) == antes
    assert not pasta.exists()


@pytest.mark.parametrize("tipo", ["inexistente", "texto", "vazio", "outro_sqlite", "esquema_incompleto"])
def test_arquivo_invalido_nao_confirma_nem_altera(conexao, tmp_path, tipo):
    popular(conexao, "Atual")
    antes = estado(conexao)
    arquivo = tmp_path / "invalido.db"
    if tipo == "texto":
        arquivo.write_text("não é SQLite")
    elif tipo == "vazio":
        arquivo.write_bytes(b'')
    elif tipo in ("outro_sqlite", "esquema_incompleto"):
        with closing(sqlite3.connect(arquivo)) as banco:
            banco.execute("CREATE TABLE outro (id INTEGER PRIMARY KEY)")
    def nao_confirmar(*args):
        pytest.fail("Não deve confirmar um arquivo inválido")
    with pytest.raises((OSError, sqlite3.Error, ValueError)):
        restauracao.restaurar_backup(conexao, arquivo, confirmar=nao_confirmar,
                                     pasta_seguranca=tmp_path / "seguranca")
    assert estado(conexao) == antes
    assert not (tmp_path / "seguranca").exists()


def test_proprio_banco_e_alias_sao_rejeitados(conexao, tmp_path):
    atual = Path(conexao.execute("PRAGMA database_list").fetchone()[2])
    alias = tmp_path / "alias.db"
    alias.symlink_to(atual)
    for arquivo in (atual, alias):
        with pytest.raises(ValueError, match="próprio banco"):
            restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar)


def test_falha_backup_obrigatorio_impede_restauracao(conexao, tmp_path, monkeypatch):
    popular(conexao, "Atual")
    antes = estado(conexao)
    arquivo, _ = arquivo_backup(tmp_path)
    def falhar(*args):
        raise OSError("falha na cópia de segurança")
    monkeypatch.setattr(restauracao, "criar_backup", falhar)
    with pytest.raises(OSError):
        restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar)
    assert estado(conexao) == antes


def test_falha_na_gravacao_preserva_banco_e_seguranca(tmp_path):
    atual = tmp_path / "atual.db"
    with closing(abrir_banco(atual)) as banco:
        popular(banco, "Atual")
        antes = estado(banco)
    arquivo, _ = arquivo_backup(tmp_path)
    pasta = tmp_path / "seguranca"
    with closing(sqlite3.connect(atual.resolve().as_uri() + '?mode=ro', uri=True)) as somente_leitura:
        with pytest.raises(sqlite3.DatabaseError, match="backup de segurança está em"):
            restauracao.restaurar_backup(somente_leitura, arquivo, confirmar=confirmar, pasta_seguranca=pasta)
        assert estado(somente_leitura) == antes
    with closing(sqlite3.connect(next(pasta.glob('*.db')))) as seguranca:
        assert estado(seguranca) == antes


def test_transacao_pendente_impede_restauracao(conexao, tmp_path):
    arquivo, _ = arquivo_backup(tmp_path)
    conexao.execute("INSERT INTO clientes (nome, contato, criado_em) VALUES ('Pendente', '', '2026-11-10')")
    with pytest.raises(ValueError, match="transação pendente"):
        restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar)
    assert conexao.in_transaction
    conexao.rollback()


def test_backup_vinculos_invalidos_nao_altera(conexao, tmp_path):
    arquivo, _ = arquivo_backup(tmp_path)
    with closing(sqlite3.connect(arquivo)) as origem:
        with origem:
            origem.execute("UPDATE orcamentos SET cliente_id = 999")
    antes = estado(conexao)
    with pytest.raises(ValueError, match="vínculos inválidos"):
        restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar)
    assert estado(conexao) == antes


def test_backup_com_gatilho_nao_e_restaurado(conexao, tmp_path):
    arquivo, _ = arquivo_backup(tmp_path)
    with closing(sqlite3.connect(arquivo)) as origem:
        origem.execute("CREATE TRIGGER extra AFTER INSERT ON clientes BEGIN SELECT 1; END;")
    with pytest.raises(ValueError, match="gatilhos"):
        restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar)


def test_preserva_validade_legada_anterior_a_emissao(conexao, tmp_path):
    arquivo, _ = arquivo_backup(tmp_path)
    with closing(sqlite3.connect(arquivo)) as origem:
        with origem:
            origem.execute("UPDATE orcamentos SET validade = '2000-01-01'")
    restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar, pasta_seguranca=tmp_path / "seguranca")
    assert buscar_orcamento(conexao, 1)["validade"] == "2000-01-01"


def test_conteudo_restaurado_e_o_validado_antes_da_confirmacao(conexao, tmp_path):
    arquivo, esperado = arquivo_backup(tmp_path)
    def mudar_arquivo(caminho, resumo):
        with closing(sqlite3.connect(caminho)) as outra:
            with outra:
                outra.execute("UPDATE clientes SET nome = 'Alterado depois'")
        return True
    restauracao.restaurar_backup(conexao, arquivo, confirmar=mudar_arquivo,
                                 pasta_seguranca=tmp_path / "seguranca")
    assert estado(conexao) == esperado


def test_menu_restaura_e_continua_consultando(monkeypatch, capsys, tmp_path):
    arquivo, _ = arquivo_backup(tmp_path)
    restaurar = restauracao.restaurar_backup
    monkeypatch.setattr(terminal_backup, "restaurar_backup", lambda c, a, confirmar: restaurar(
        c, a, confirmar=confirmar, pasta_seguranca=tmp_path / "seguranca"))
    entradas = iter(["13", "Atual", "", "19", str(arquivo), "RESTAURAR", "3", "1", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(tmp_path / "atual.db")
    saida = capsys.readouterr().out
    assert "dados atuais serão substituídos" in saida
    assert "Banco restaurado com sucesso." in saida
    assert "Backup do estado anterior:" in saida
    assert "Cliente: Cliente do backup fictício" in saida
    assert len(list((tmp_path / "seguranca").glob('*.db'))) == 1


@pytest.mark.parametrize("resposta", ["", "s", "restaurar"])
def test_menu_exige_confirmacao_exata(monkeypatch, capsys, conexao, tmp_path, resposta):
    arquivo, _ = arquivo_backup(tmp_path)
    antes = estado(conexao)
    entradas = iter([str(arquivo), resposta])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    terminal_backup.restaurar_backup_no_terminal(conexao)
    assert "Restauração cancelada" in capsys.readouterr().out
    assert estado(conexao) == antes


def test_menu_caminho_vazio_cancela(monkeypatch, capsys, conexao):
    monkeypatch.setattr("builtins.input", lambda _: "")
    terminal_backup.restaurar_backup_no_terminal(conexao)
    assert "Restauração cancelada" in capsys.readouterr().out


def test_restauracao_em_banco_wal(conexao, tmp_path):
    assert conexao.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    popular(conexao, "Atual")
    arquivo, esperado = arquivo_backup(tmp_path)
    restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar,
                                 pasta_seguranca=tmp_path / "seguranca")
    assert estado(conexao) == esperado
    assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_backup_esquema_antigo_nao_e_migrado_automaticamente(conexao, tmp_path):
    arquivo = tmp_path / "antigo.db"
    with closing(sqlite3.connect(arquivo)) as antigo:
        antigo.execute("CREATE TABLE orcamentos (id INTEGER PRIMARY KEY, cliente TEXT)")
    antes = arquivo.read_bytes()
    with pytest.raises(ValueError, match="compatível"):
        restauracao.restaurar_backup(conexao, arquivo, confirmar=confirmar)
    assert arquivo.read_bytes() == antes


def test_menu_arquivo_invalido_nao_anuncia_sucesso(monkeypatch, capsys, conexao, tmp_path):
    monkeypatch.setattr("builtins.input", lambda _: str(tmp_path / "inexistente.db"))
    terminal_backup.restaurar_backup_no_terminal(conexao)
    saida = capsys.readouterr().out
    assert "Erro ao restaurar backup:" in saida
    assert "Banco restaurado com sucesso" not in saida
