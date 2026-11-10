from decimal import Decimal
import importlib

import pytest

import main


def fornecer_entradas(monkeypatch, entradas):
    respostas = iter(entradas)
    monkeypatch.setattr("builtins.input", lambda mensagem: next(respostas))


def test_importacao_sem_interacao(monkeypatch, capsys):
    def entrada_proibida(mensagem):
        pytest.fail("Importar main não deve solicitar dados")
    monkeypatch.setattr("builtins.input", entrada_proibida)
    importlib.reload(main)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("funcao, entradas, esperado", [
    (main.ler_quantidade, ["abc", "0", "1000001", "2"], 2),
    (main.ler_valor_unitario, ["abc", "NaN", "1e30", "0.001", "1,005"], Decimal("1.01")),
    (main.ler_desconto, ["abc", "Infinity", "101", "100"], Decimal("100")),
    (main.deseja_adicionar_outro, ["talvez", " S "], True),
])
def test_recuperacao_de_entrada_invalida(monkeypatch, capsys, funcao, entradas, esperado):
    fornecer_entradas(monkeypatch, entradas)
    assert funcao() == esperado
    assert "Erro:" in capsys.readouterr().out


def test_nome_vazio(monkeypatch, capsys):
    fornecer_entradas(monkeypatch, ["  ", " Ana "])
    assert main.ler_nome("Cliente: ") == "Ana"
    assert "Erro:" in capsys.readouterr().out


def test_fluxo_completo_com_multiplos_servicos(monkeypatch, capsys):
    fornecer_entradas(monkeypatch, ["Ana", "Instalação", "1,005", "3", "s", "Revisão", "10", "2", "n", "10"])
    main.criar_orcamento()
    saida = capsys.readouterr().out
    assert "Cliente: Ana" in saida
    assert "Subtotal geral: R$ 23,03" in saida
    assert "Valor do desconto: R$ 2,30" in saida
    assert "TOTAL FINAL: R$ 20,73" in saida


def test_recuperacao_de_subtotal_invalido(monkeypatch, capsys):
    fornecer_entradas(monkeypatch, ["Ana", "Inválido", "999999999999", "2", "Válido", "10", "1", "n", "0"])
    main.criar_orcamento()
    saida = capsys.readouterr().out
    assert "Cadastre o serviço novamente" in saida
    assert "TOTAL FINAL: R$ 10,00" in saida


def test_soma_invalida_sem_encerramento_por_excecao(monkeypatch, capsys):
    fornecer_entradas(monkeypatch, ["Ana", "A", "600000000000", "1", "s", "B", "600000000000", "1", "n", "0"])
    main.criar_orcamento()
    saida = capsys.readouterr().out
    assert "O orçamento não foi gerado" in saida
    assert "TOTAL FINAL:" not in saida


def test_menu_salva_e_consulta_apos_reabrir(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, ["1", "Ana", "Serviço", "10,50", "2", "n", "10", "0"])
    main.main(caminho)
    assert "Orçamento salvo com o número 1" in capsys.readouterr().out

    fornecer_entradas(monkeypatch, ["2", "", "", "3", "1", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "#1 | Ana" in saida
    assert "Cliente: Ana" in saida
    assert "TOTAL FINAL: R$ 18,90" in saida


def test_menu_vazio_opcao_invalida_e_consulta_inexistente(monkeypatch, capsys, tmp_path):
    fornecer_entradas(monkeypatch, ["opção inválida", "2", "", "", "3", "abc", "3", "0", "3", "999", "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "escolha uma opção" in saida
    assert "Nenhum orçamento salvo" in saida
    assert "identificador inteiro positivo válido" in saida
    assert "Orçamento não encontrado" in saida


def test_erro_ao_abrir_banco(monkeypatch, capsys, tmp_path):
    main.main(tmp_path / "pasta_inexistente" / "teste.db")
    assert "não foi possível abrir" in capsys.readouterr().out


def test_erro_ao_salvar_nao_anuncia_sucesso(monkeypatch, capsys, tmp_path):
    import sqlite3

    def falhar(*args):
        raise sqlite3.OperationalError("falha simulada")

    monkeypatch.setattr(main, "salvar_orcamento", falhar)
    fornecer_entradas(monkeypatch, ["1", "Ana", "Serviço", "10", "1", "n", "0", "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "ele não foi salvo" in saida
    assert "Orçamento salvo com" not in saida


def test_menu_altera_status_e_exibe_apos_reabrir(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Serviço", "10", "1", "n", "0",
        "2", "", "", "3", "1", "4", "1", " APROVADO ", "0",
    ])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "1 serviço | pendente" in saida
    assert "Status: pendente" in saida
    assert "Status do orçamento #1 atualizado para aprovado." in saida

    fornecer_entradas(monkeypatch, ["2", "", "", "3", "1", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "1 serviço | aprovado" in saida
    assert "Status: aprovado" in saida


@pytest.mark.parametrize("identificador", ["abc", "0", "-1", str(2**63)])
def test_menu_alterar_status_identificador_invalido(monkeypatch, capsys, tmp_path, identificador):
    fornecer_entradas(monkeypatch, ["4", identificador, "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "identificador inteiro positivo válido" in saida
    assert "atualizado para" not in saida


def test_menu_alterar_status_inexistente(monkeypatch, capsys, tmp_path):
    fornecer_entradas(monkeypatch, ["4", "999", "aprovado", "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Orçamento não encontrado." in saida
    assert "atualizado para" not in saida


def test_menu_status_invalido_preserva_status(monkeypatch, capsys, tmp_path):
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Serviço", "10", "1", "n", "0",
        "4", "1", "cancelado", "3", "1", "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "O status deve ser pendente, aprovado ou recusado." in saida
    assert "Status: pendente" in saida
    assert "atualizado para" not in saida


def test_menu_falha_ao_alterar_status(monkeypatch, capsys, tmp_path):
    import sqlite3

    def falhar(*args):
        raise sqlite3.OperationalError("falha simulada")

    monkeypatch.setattr(main, "alterar_status", falhar)
    fornecer_entradas(monkeypatch, ["4", "1", "aprovado", "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Erro ao acessar o banco" in saida
    assert "atualizado para" not in saida


@pytest.mark.parametrize("filtro, cliente_esperado, cliente_ausente", [
    (" APROVADO ", "Ana", "Bruno"),
    ("pendente", "Bruno", "Ana"),
])
def test_menu_filtra_status(monkeypatch, capsys, tmp_path, filtro, cliente_esperado, cliente_ausente):
    from repositorio import abrir_banco, salvar_orcamento, alterar_status
    from orcamento import criar_item

    caminho = tmp_path / "teste.db"
    banco = abrir_banco(caminho)
    try:
        itens = [criar_item("Tomadas", 10, Decimal("15"))]
        identificador = salvar_orcamento(banco, "Ana", itens, Decimal("0"))
        alterar_status(banco, identificador, "aprovado")
        salvar_orcamento(banco, "Bruno", itens, Decimal("0"))
    finally:
        banco.close()
    fornecer_entradas(monkeypatch, ["2", filtro, "", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert f"| {cliente_esperado} |" in saida
    assert f"| {cliente_ausente} |" not in saida
    assert "1 serviço" in saida


def test_menu_filtro_invalido_e_sem_resultados(monkeypatch, capsys, tmp_path):
    fornecer_entradas(monkeypatch, ["2", "cancelado", "", "2", "recusado", "", "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Erro: O status deve ser pendente, aprovado ou recusado." in saida
    assert "Nenhum orçamento com status recusado." in saida


@pytest.mark.parametrize("status, termo, esperados", [
    ("", " bruno ", ["Bruno Henrique", "Bruno Silva"]),
    ("aprovado", "bruno", ["Bruno Henrique"]),
    ("pendente", "bruno", ["Bruno Silva"]),
    ("", "inexistente", []),
])
def test_menu_busca_cliente_com_status(monkeypatch, capsys, tmp_path, status, termo, esperados):
    from repositorio import abrir_banco, salvar_orcamento, alterar_status
    from orcamento import criar_item

    caminho = tmp_path / "teste.db"
    banco = abrir_banco(caminho)
    nomes = ["Bruno Henrique", "Bruno Silva", "Ana"]
    try:
        for nome in nomes:
            identificador = salvar_orcamento(
                banco, nome, [criar_item("Serviço", 1, Decimal("10"))], Decimal("0")
            )
            if nome == "Bruno Henrique":
                alterar_status(banco, identificador, "aprovado")
    finally:
        banco.close()
    fornecer_entradas(monkeypatch, ["2", status, termo, "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    for nome in nomes:
        assert (f"| {nome} |" in saida) == (nome in esperados)
    if not esperados:
        assert "Nenhum orçamento encontrado para os filtros informados." in saida


def test_menu_duplica_e_consulta_apos_reabrir(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Tomadas", "15", "10", "n", "10",
        "4", "1", "aprovado", "5", "1", "0",
    ])
    main.main(caminho)
    assert "Orçamento #1 duplicado com o número 2. Status: pendente." in capsys.readouterr().out
    fornecer_entradas(monkeypatch, ["3", "2", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Orçamento #2" in saida
    assert "Status: pendente" in saida
    assert "Cliente: Ana" in saida
    assert "TOTAL FINAL: R$ 135,00" in saida


@pytest.mark.parametrize("identificador", ["abc", "0", "-1", str(2**63), "999"])
def test_menu_duplicacao_numero_invalido_ou_inexistente(monkeypatch, capsys, tmp_path, identificador):
    fornecer_entradas(monkeypatch, ["5", identificador, "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "duplicado com o número" not in saida
    assert ("Orçamento não encontrado." if identificador == "999" else
            "identificador inteiro positivo válido") in saida


def test_menu_falha_ao_duplicar(monkeypatch, capsys, tmp_path):
    import sqlite3

    def falhar(*args):
        raise sqlite3.OperationalError("falha simulada")

    monkeypatch.setattr(main, "duplicar_orcamento", falhar)
    fornecer_entradas(monkeypatch, ["5", "1", "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Erro ao acessar o banco" in saida
    assert "duplicado com o número" not in saida


@pytest.mark.parametrize("cliente, desconto, nome_final, total", [
    ("Maria", "10,5", "Maria", "134,25"),
    ("", "", "Ana", "150,00"),
    ("Maria", "", "Maria", "150,00"),
    ("", "100", "Ana", "0,00"),
])
def test_menu_edita_e_consulta(monkeypatch, capsys, tmp_path, cliente, desconto, nome_final, total):
    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Tomadas", "15", "10", "n", "0",
        "4", "1", "aprovado", "6", "1", cliente, desconto, "0",
    ])
    main.main(caminho)
    assert "Orçamento #1 atualizado." in capsys.readouterr().out
    fornecer_entradas(monkeypatch, ["3", "1", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert f"Cliente: {nome_final}" in saida
    assert f"TOTAL FINAL: R$ {total}" in saida
    assert "Status: aprovado" in saida


@pytest.mark.parametrize("cliente, desconto", [
    ("  ", "0"), ("Maria", "abc"), ("Maria", "NaN"), ("Maria", "101"),
])
def test_menu_edicao_invalida_preserva_dados(monkeypatch, capsys, tmp_path, cliente, desconto):
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Tomadas", "15", "10", "n", "0",
        "6", "1", cliente, desconto, "3", "1", "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Nenhuma alteração foi salva." in saida
    assert "Cliente: Ana" in saida
    assert "TOTAL FINAL: R$ 150,00" in saida
    assert "Orçamento #1 atualizado." not in saida


@pytest.mark.parametrize("identificador", ["abc", "0", str(2**63), "999"])
def test_menu_edicao_identificador_invalido_ou_inexistente(monkeypatch, capsys, tmp_path, identificador):
    fornecer_entradas(monkeypatch, ["6", identificador, "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert ("Orçamento não encontrado." if identificador == "999" else
            "identificador inteiro positivo válido") in saida


def test_menu_falha_ao_editar(monkeypatch, capsys, tmp_path):
    import sqlite3

    def falhar(*args):
        raise sqlite3.OperationalError("falha simulada")

    monkeypatch.setattr(main, "editar_orcamento", falhar)
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Serviço", "10", "1", "n", "0",
        "6", "1", "Maria", "10", "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Erro ao acessar o banco" in saida
    assert "Orçamento #1 atualizado." not in saida


@pytest.mark.parametrize("nome, quantidade, preco, esperado", [
    ("Revisão", "2", "20,005", "36,02"),
    ("", "", "", "135,00"),
])
def test_menu_edita_servico_e_persiste(monkeypatch, capsys, tmp_path, nome, quantidade, preco, esperado):
    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Tomadas", "15", "10", "n", "10",
        "4", "1", "aprovado", "7", "1", "1", nome, quantidade, preco, "0",
    ])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "ID 1 | Tomadas" in saida
    assert "Serviço ID 1 atualizado no orçamento #1." in saida
    fornecer_entradas(monkeypatch, ["3", "1", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert f"TOTAL FINAL: R$ {esperado}" in saida
    assert "Status: aprovado" in saida
    assert "Cliente: Ana" in saida
    assert f"Serviço: {nome or 'Tomadas'}" in saida


@pytest.mark.parametrize("nome, quantidade, preco", [
    ("  ", "1", "10"), ("Novo", "abc", "10"), ("Novo", "0", "10"),
    ("Novo", "1", "abc"), ("Novo", "1", "NaN"),
])
def test_menu_servico_invalido_nao_grava(monkeypatch, capsys, tmp_path, nome, quantidade, preco):
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Tomadas", "15", "10", "n", "0",
        "7", "1", "1", nome, quantidade, preco, "3", "1", "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Nenhuma alteração foi salva." in saida
    assert "Serviço ID 1 atualizado" not in saida
    assert "TOTAL FINAL: R$ 150,00" in saida


@pytest.mark.parametrize("entradas, mensagem", [
    (["7", "abc", "0"], "identificador inteiro positivo válido"),
    (["7", "999", "0"], "Orçamento não encontrado."),
    (["7", "1", "abc", "0"], "identificador inteiro positivo válido"),
    (["7", "1", "999", "0"], "Serviço não encontrado neste orçamento."),
])
def test_menu_selecao_de_item_invalida(monkeypatch, capsys, tmp_path, entradas, mensagem):
    fornecer_entradas(monkeypatch, ["1", "Ana", "Tomadas", "15", "1", "n", "0", *entradas])
    main.main(tmp_path / "teste.db")
    assert mensagem in capsys.readouterr().out


def test_menu_adiciona_remove_e_consulta_apos_reabrir(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "Tomadas", "15", "10", "n", "10",
        "4", "1", "aprovado", "8", "1", "Revisão", "20,005", "2",
        "9", "1", "1", "talvez", " S ", "0",
    ])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Serviço ID 2 adicionado ao orçamento #1." in saida
    assert "digite apenas 's' ou 'n'" in saida
    assert "Serviço ID 1 removido do orçamento #1." in saida
    fornecer_entradas(monkeypatch, ["3", "1", "2", "", "", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Serviço: Revisão" in saida
    assert "Serviço: Tomadas" not in saida
    assert "TOTAL FINAL: R$ 36,02" in saida
    assert "Status: aprovado" in saida
    assert "1 serviço | aprovado" in saida


def test_menu_cancela_remocao_e_impede_remover_ultimo(monkeypatch, capsys, tmp_path):
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "A", "10", "1", "n", "0",
        "9", "1", "1", "8", "1", "B", "20", "1",
        "9", "1", "1", "n", "3", "1", "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "não é possível remover o último serviço" in saida
    assert "Remoção cancelada." in saida
    assert "Serviço: A" in saida and "Serviço: B" in saida
    assert "TOTAL FINAL: R$ 30,00" in saida
    assert "removido do orçamento" not in saida


@pytest.mark.parametrize("opcao, entradas, mensagem", [
    ("8", ["abc"], "identificador inteiro positivo válido"),
    ("8", ["999"], "Orçamento não encontrado."),
    ("9", ["0"], "identificador inteiro positivo válido"),
    ("9", ["999"], "Orçamento não encontrado."),
    ("9", ["1", "abc"], "identificador inteiro positivo válido"),
    ("9", ["1", "999"], "Serviço não encontrado neste orçamento."),
])
def test_menu_incluir_remover_selecao_invalida(monkeypatch, capsys, tmp_path, opcao, entradas, mensagem):
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "A", "10", "1", "n", "0", opcao, *entradas, "0",
    ])
    main.main(tmp_path / "teste.db")
    assert mensagem in capsys.readouterr().out


def test_menu_inclusao_recupera_entradas_invalidas(monkeypatch, capsys, tmp_path):
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "A", "10", "1", "n", "0",
        "8", "1", " ", "B", "abc", "NaN", "1,005", "0", "2", "3", "1", "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Serviço ID 2 adicionado" in saida
    assert "TOTAL FINAL: R$ 12,02" in saida


def test_menu_inclusao_rejeita_total_acima_do_limite(monkeypatch, capsys, tmp_path):
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "A", "600000000000", "1", "n", "0",
        "8", "1", "B", "600000000000", "1", "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Nenhum serviço foi adicionado." in saida
    assert "Serviço ID 2 adicionado" not in saida


@pytest.mark.parametrize("opcao, funcao, entradas", [
    ("8", "adicionar_item", ["1", "C", "10", "1"]),
    ("9", "remover_item", ["1", "1", "s"]),
])
def test_menu_falha_inclusao_remocao(monkeypatch, capsys, tmp_path, opcao, funcao, entradas):
    import sqlite3

    def falhar(*args):
        raise sqlite3.OperationalError("falha simulada")

    monkeypatch.setattr(main, funcao, falhar)
    fornecer_entradas(monkeypatch, [
        "1", "Ana", "A", "10", "1", "s", "B", "20", "1", "n", "0",
        opcao, *entradas, "0",
    ])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert "Erro ao acessar o banco" in saida
    assert "adicionado ao orçamento" not in saida
    assert "removido do orçamento" not in saida


def test_menu_prestador_condicoes_e_consulta(monkeypatch, capsys, tmp_path):
    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "10", "Empresa exemplo", "contato@example.com",
        "1", "Cliente fictício", "Serviço", "10", "2", "n", "10",
        "11", "1", "31/12/2026", "Pix", "Instalação agendada", "0",
    ])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Dados do prestador salvos." in saida
    assert "Dados comerciais do orçamento #1 salvos." in saida
    fornecer_entradas(monkeypatch, ["10", "", "", "3", "1", "0"])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Prestador atual: Empresa exemplo" in saida
    assert "Contato atual: contato@example.com" in saida
    assert "Validade: 31/12/2026" in saida
    assert "Condições de pagamento: Pix" in saida
    assert "Observações: Instalação agendada" in saida
    assert "TOTAL FINAL: R$ 18,00" in saida


def test_menu_campos_comerciais_manter_limpar_e_data_invalida(monkeypatch, capsys, tmp_path):
    from repositorio import abrir_banco, buscar_orcamento, buscar_prestador

    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "10", "", "", "10", "Empresa exemplo", "contato@example.com",
        "10", "", "-", "1", "Cliente fictício", "Serviço", "10", "1", "n", "0",
        "11", "1", "31/12/2026", "Pix", "Observação",
        "11", "1", "31/02/2026", "Boleto", "Não gravar",
        "11", "1", "", "", "",
        "11", "1", "-", "-", "-", "0",
    ])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "Nome do prestador não pode ficar vazio" in saida
    assert "informe uma data válida" in saida
    assert "Pagamento atual: Pix" in saida
    banco = abrir_banco(caminho)
    try:
        assert buscar_prestador(banco) == {"nome": "Empresa exemplo", "contato": ""}
        resultado = buscar_orcamento(banco, 1)
        assert resultado["validade"] is None
        assert resultado["condicoes_pagamento"] == resultado["observacoes"] == ""
    finally:
        banco.close()


@pytest.mark.parametrize("identificador", ["abc", "0", "999"])
def test_menu_condicoes_identificador_invalido(monkeypatch, capsys, tmp_path, identificador):
    fornecer_entradas(monkeypatch, ["11", identificador, "0"])
    main.main(tmp_path / "teste.db")
    saida = capsys.readouterr().out
    assert ("Orçamento não encontrado" if identificador == "999" else
            "identificador inteiro positivo válido") in saida


def test_menu_rejeita_validade_anterior_e_preserva_dados(monkeypatch, capsys, tmp_path):
    from repositorio import abrir_banco, buscar_orcamento

    caminho = tmp_path / "teste.db"
    fornecer_entradas(monkeypatch, [
        "1", "Cliente fictício", "Serviço", "10", "1", "n", "0",
        "11", "1", "01/01/2000", "Não salvar", "Não salvar", "0",
    ])
    main.main(caminho)
    saida = capsys.readouterr().out
    assert "A validade não pode ser anterior à data de emissão" in saida
    assert "Nenhuma alteração foi salva." in saida
    assert "Dados comerciais do orçamento #1 salvos." not in saida
    banco = abrir_banco(caminho)
    try:
        resultado = buscar_orcamento(banco, 1)
        assert resultado["validade"] is None
        assert resultado["condicoes_pagamento"] == resultado["observacoes"] == ""
    finally:
        banco.close()
