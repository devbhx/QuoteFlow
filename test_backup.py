from contextlib import closing
from datetime import datetime
from decimal import Decimal
import sqlite3

import pytest

import backup
import main
import terminal_backup
from orcamento import criar_item
from repositorio import (
    abrir_banco, cadastrar_cliente, salvar_orcamento, salvar_prestador,
    alterar_status, buscar_orcamento,
)


@pytest.fixture
def conexao(tmp_path):
    banco = abrir_banco(tmp_path / "origem.db")
    yield banco
    banco.close()


def popular(conexao):
    cliente_id = cadastrar_cliente(conexao, "Cliente fictício", "contato@example.com")
    salvar_prestador(conexao, "Empresa exemplo", "empresa@example.com")
    identificador = salvar_orcamento(
        conexao, "Cliente fictício", [criar_item("Instalação", 3, Decimal("1.005"))],
        Decimal("10"), cliente_id=cliente_id, condicoes_pagamento="Pix", observacoes="Instalação agendada",
    )
    alterar_status(conexao, identificador, "aprovado")
    return identificador


def registros(conexao):
    return {tabela: [tuple(linha) for linha in conexao.execute(f'SELECT * FROM {tabela} ORDER BY id')]
            for tabela in ('clientes', 'orcamentos', 'itens_orcamento', 'configuracao_prestador')}


def ler_backup(caminho):
    return sqlite3.connect(caminho.resolve().as_uri() + '?mode=ro', uri=True)


def test_backup_completo_integro_e_independente(conexao, tmp_path):
    identificador = popular(conexao)
    antes = registros(conexao)
    caminho = backup.criar_backup(conexao, tmp_path / "backups")
    assert caminho.is_file()
    assert registros(conexao) == antes
    assert buscar_orcamento(conexao, identificador)["total"] == Decimal("2.73")
    with closing(ler_backup(caminho)) as copia:
        assert registros(copia) == antes
        assert copia.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert copia.execute("PRAGMA foreign_key_check").fetchall() == []
    cadastrar_cliente(conexao, "Cliente posterior fictício")
    with closing(ler_backup(caminho)) as copia:
        assert registros(copia) == antes
    assert not list(caminho.parent.glob("*.tmp"))


def test_backup_repetido_nao_sobrescreve(conexao, tmp_path, monkeypatch):
    class RelogioFixo(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 11, 10, 12, 0).astimezone()

    monkeypatch.setattr(backup, "datetime", RelogioFixo)
    popular(conexao)
    primeiro = backup.criar_backup(conexao, tmp_path / "backups")
    bytes_antes = primeiro.read_bytes()
    cadastrar_cliente(conexao, "Novo cliente fictício")
    segundo = backup.criar_backup(conexao, tmp_path / "backups")
    assert primeiro != segundo
    assert segundo.stem.endswith("_1")
    assert primeiro.read_bytes() == bytes_antes
    with closing(ler_backup(segundo)) as copia:
        assert len(copia.execute("SELECT * FROM clientes").fetchall()) == 2


def test_backup_banco_vazio_preserva_estrutura(conexao, tmp_path):
    caminho = backup.criar_backup(conexao, tmp_path / "backups")
    with closing(ler_backup(caminho)) as copia:
        assert registros(copia) == registros(conexao)


def test_backup_inclui_dados_confirmados_no_wal(tmp_path):
    caminho = tmp_path / "origem.db"
    with closing(abrir_banco(caminho)) as conexao:
        assert conexao.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        popular(conexao)
        antes = registros(conexao)
        copia_path = backup.criar_backup(conexao, tmp_path / "backups")
        with closing(ler_backup(copia_path)) as copia:
            assert registros(copia) == antes


def test_transacao_pendente_nao_e_confirmada_pelo_backup(conexao, tmp_path):
    conexao.execute("INSERT INTO clientes (nome, contato, criado_em) VALUES ('Fictício', '', '2026-11-10')")
    pasta = tmp_path / "backups"
    with pytest.raises(ValueError, match="transação pendente"):
        backup.criar_backup(conexao, pasta)
    assert conexao.in_transaction
    assert not pasta.exists()
    conexao.rollback()
    assert conexao.execute("SELECT COUNT(*) FROM clientes").fetchone()[0] == 0


def test_falha_backup_remove_somente_temporario(tmp_path):
    class OrigemComFalha:
        in_transaction = False

        def backup(self, destino):
            raise sqlite3.DatabaseError("falha simulada")

    pasta = tmp_path / "backups"
    pasta.mkdir()
    anterior = pasta / "anterior.db"
    anterior.write_bytes(b'backup anterior preservado')
    with pytest.raises(sqlite3.DatabaseError):
        backup.criar_backup(OrigemComFalha(), pasta)
    assert anterior.read_bytes() == b'backup anterior preservado'
    assert list(pasta.iterdir()) == [anterior]


def test_backup_rejeita_vinculos_invalidos(conexao, tmp_path):
    conexao.execute("PRAGMA foreign_keys=OFF")
    with conexao:
        conexao.execute("""INSERT INTO itens_orcamento
            (orcamento_id, nome, quantidade, valor_unitario_centavos)
            VALUES (999, 'Serviço fictício', 1, 1000)""")
    pasta = tmp_path / "backups"
    with pytest.raises(ValueError, match="vínculos inválidos"):
        backup.criar_backup(conexao, pasta)
    assert list(pasta.iterdir()) == []
    assert conexao.execute("SELECT COUNT(*) FROM itens_orcamento").fetchone()[0] == 1


def test_backup_pasta_invalida_nao_altera_origem(conexao, tmp_path):
    popular(conexao)
    antes = registros(conexao)
    arquivo = tmp_path / "arquivo"
    arquivo.write_text('preservar')
    with pytest.raises(OSError):
        backup.criar_backup(conexao, arquivo)
    assert arquivo.read_text() == 'preservar'
    assert registros(conexao) == antes


def test_menu_cria_backup(monkeypatch, capsys, tmp_path):
    pasta = tmp_path / "backups"
    monkeypatch.setattr(terminal_backup, "criar_backup", lambda c: backup.criar_backup(c, pasta))
    entradas = iter(["13", "Cliente fictício", "", "18", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    main.main(tmp_path / "origem.db")
    assert "Backup criado:" in capsys.readouterr().out
    caminhos = list(pasta.glob("*.db"))
    assert len(caminhos) == 1
    with closing(ler_backup(caminhos[0])) as copia:
        assert copia.execute("SELECT nome FROM clientes").fetchone()[0] == "Cliente fictício"


@pytest.mark.parametrize("erro", [OSError("sem espaço"), sqlite3.DatabaseError("falha"), ValueError("pendência")])
def test_menu_falha_backup_nao_anuncia_sucesso(monkeypatch, capsys, conexao, erro):
    def falhar(*args):
        raise erro

    monkeypatch.setattr(terminal_backup, "criar_backup", falhar)
    terminal_backup.criar_backup_no_terminal(conexao)
    saida = capsys.readouterr().out
    assert "Erro ao criar backup:" in saida
    assert "Backup criado:" not in saida
