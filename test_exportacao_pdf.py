from datetime import datetime
from decimal import Decimal

from pypdf import PdfReader
import pytest

import exportacao_pdf
import main
from orcamento import criar_item
from repositorio import (
    abrir_banco, salvar_orcamento, salvar_prestador, buscar_orcamento,
    editar_condicoes, alterar_status,
)


@pytest.fixture
def conexao(tmp_path):
    banco = abrir_banco(tmp_path / "pdf.db")
    yield banco
    banco.close()


def criar(conexao, servicos=None):
    return salvar_orcamento(conexao, "Cliente fictício: João & Filhos", servicos or [
        criar_item("Instalação de tomadas", 3, Decimal("1.005")),
        criar_item("Revisão elétrica", 2, Decimal("10")),
    ], Decimal("10"))


def texto(caminho):
    return "\n".join(p.extract_text() for p in PdfReader(caminho).pages)


def test_pdf_contem_dados_acentos_e_valores_sem_alterar_banco(conexao, tmp_path):
    identificador = criar(conexao)
    salvar_prestador(conexao, "Empresa exemplo: José & Cia", "contato@example.com")
    editar_condicoes(conexao, identificador, "2026-12-31", "Pix em 2 parcelas", "Execução após aprovação.")
    alterar_status(conexao, identificador, "aprovado")
    antes = buscar_orcamento(conexao, identificador)
    caminho = exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path / "exports")
    leitor = PdfReader(caminho)
    assert len(leitor.pages) == 1
    assert float(leitor.pages[0].mediabox.width) == pytest.approx(595.276, abs=0.01)
    conteudo = texto(caminho)
    for trecho in ["José & Cia", "João & Filhos", "contato@example.com", "31/12/2026",
                   "Instalação de tomadas", "Revisão elétrica", "Pix em 2 parcelas",
                   "Execução após aprovação.", "R$ 1,01", "R$ 3,03", "R$ 23,03", "R$ 2,30", "R$ 20,73",
                   "Página 1", "Exportado em"]:
        assert trecho in conteudo
    assert buscar_orcamento(conexao, identificador) == antes


def test_pdf_sem_campos_opcionais(conexao, tmp_path):
    identificador = criar(conexao)
    salvar_prestador(conexao, "Empresa exemplo")
    conteudo = texto(exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path))
    assert "TOTAL" in conteudo
    assert "Válido até" not in conteudo
    assert "Observações" not in conteudo
    assert "Condições de pagamento" not in conteudo


def test_pdf_multipaginas_repete_cabecalho_e_numera(conexao, tmp_path):
    servicos = [criar_item(f"Serviço de instalação {i:03}", 1, Decimal("10")) for i in range(100)]
    identificador = criar(conexao, servicos)
    salvar_prestador(conexao, "Empresa exemplo")
    leitor = PdfReader(exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path))
    assert len(leitor.pages) >= 3
    textos = [p.extract_text() for p in leitor.pages]
    for numero, pagina in enumerate(textos, 1):
        assert f"Página {numero}" in pagina
        if "Serviço de instalação" in pagina:
            assert "Descrição" in pagina and "Preço unitário" in pagina
    conteudo = "\n".join(textos)
    assert "Serviço de instalação 099" in conteudo
    assert "R$ 900,00" in conteudo


def test_pdf_texto_literal_longo_e_quebras_de_pagina(conexao, tmp_path):
    nome = '<b>Não é marcação</b> & instalação ' + 'serviço ' * 1000
    identificador = criar(conexao, [criar_item(nome, 1, Decimal("10"))])
    salvar_prestador(conexao, "Empresa exemplo")
    editar_condicoes(conexao, identificador, observacoes="Observação\n" + "Texto longo com acentuação. " * 1000)
    caminho = exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path)
    conteudo = texto(caminho)
    assert "<b>Não é marcação</b> & instalação" in conteudo
    assert "TOTAL" in conteudo
    assert len(PdfReader(caminho).pages) > 2


def test_exportacao_exige_prestador_sem_criar_pasta(conexao, tmp_path):
    identificador = criar(conexao)
    pasta = tmp_path / "exports"
    with pytest.raises(ValueError, match="opção 10"):
        exportacao_pdf.exportar_orcamento(conexao, identificador, pasta)
    assert not pasta.exists()


def test_pdf_inexistente_nao_cria_arquivo(conexao, tmp_path):
    pasta = tmp_path / "exports"
    assert exportacao_pdf.exportar_orcamento(conexao, 999, pasta) is None
    assert not pasta.exists()


@pytest.mark.parametrize("identificador", [0, True, "1", 2**63])
def test_pdf_identificador_invalido(conexao, tmp_path, identificador):
    with pytest.raises(ValueError):
        exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path)


def test_exportar_duas_vezes_nao_sobrescreve(conexao, tmp_path, monkeypatch):
    class RelogioFixo(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 11, 10, 12, 0).astimezone()

    monkeypatch.setattr(exportacao_pdf, "datetime", RelogioFixo)
    identificador = criar(conexao)
    salvar_prestador(conexao, "Empresa exemplo")
    primeiro = exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path)
    dados = primeiro.read_bytes()
    segundo = exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path)
    assert primeiro != segundo
    assert segundo.stem.endswith("_1")
    assert primeiro.read_bytes() == dados
    assert "R$ 20,73" in texto(segundo)


def test_menu_exporta_pdf(monkeypatch, capsys, conexao, tmp_path):
    identificador = criar(conexao)
    salvar_prestador(conexao, "Empresa exemplo")
    exportar = exportacao_pdf.exportar_orcamento
    monkeypatch.setattr(exportacao_pdf, "exportar_orcamento", lambda c, i: exportar(c, i, tmp_path))
    monkeypatch.setattr("builtins.input", lambda _: str(identificador))
    main.exportar_pdf_no_terminal(conexao)
    assert "PDF exportado:" in capsys.readouterr().out
    assert len(list(tmp_path.glob("*.pdf"))) == 1


def test_menu_falha_de_escrita_nao_anuncia_sucesso(monkeypatch, capsys, conexao):
    def falhar(*args):
        raise OSError("falha simulada")

    monkeypatch.setattr(exportacao_pdf, "exportar_orcamento", falhar)
    monkeypatch.setattr("builtins.input", lambda _: "1")
    main.exportar_pdf_no_terminal(conexao)
    saida = capsys.readouterr().out
    assert "não foi possível gravar" in saida
    assert "PDF exportado:" not in saida


@pytest.mark.parametrize("status", ["pendente", "aprovado", "recusado"])
def test_pdf_nao_exibe_status_mas_sistema_preserva(conexao, tmp_path, status):
    from repositorio import listar_orcamentos

    identificador = criar(conexao)
    salvar_prestador(conexao, "Empresa exemplo")
    alterar_status(conexao, identificador, status)
    caminho = exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path)
    conteudo = texto(caminho)
    assert "Status" not in conteudo
    for valor in ("pendente", "aprovado", "recusado"):
        assert valor not in conteudo
    assert buscar_orcamento(conexao, identificador)["status"] == status
    assert listar_orcamentos(conexao, status=status)[0]["id"] == identificador


def test_pdf_exporta_validade_legada_sem_modificar_orcamento(conexao, tmp_path):
    identificador = criar(conexao)
    salvar_prestador(conexao, "Empresa exemplo")
    with conexao:
        conexao.execute("UPDATE orcamentos SET criado_em = ?, validade = ? WHERE id = ?",
                        ("2026-11-10T12:00:00-03:00", "2026-11-09", identificador))
    antes = buscar_orcamento(conexao, identificador)
    conteudo = texto(exportacao_pdf.exportar_orcamento(conexao, identificador, tmp_path))
    assert "09/11/2026" in conteudo
    assert buscar_orcamento(conexao, identificador) == antes
