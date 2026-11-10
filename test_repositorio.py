from decimal import Decimal
import sqlite3

import pytest

from orcamento import criar_item
from repositorio import (
    abrir_banco, salvar_orcamento, listar_orcamentos, buscar_orcamento, alterar_status, duplicar_orcamento, editar_orcamento,
    listar_itens_orcamento, editar_item, adicionar_item, remover_item
)


@pytest.fixture
def conexao(tmp_path):
    banco = abrir_banco(tmp_path / "teste.db")
    yield banco
    banco.close()


def itens():
    return [criar_item("Instalação", 3, Decimal("1.005")),
            criar_item("Revisão", 2, Decimal("10"))]


def test_persistencia_apos_reabrir(tmp_path):
    caminho = tmp_path / "teste.db"
    banco = abrir_banco(caminho)
    identificador = salvar_orcamento(banco, " Ana ", itens(), Decimal("10.125"))
    banco.close()

    banco = abrir_banco(caminho)
    try:
        resultado = buscar_orcamento(banco, identificador)
        assert resultado["cliente"] == "Ana"
        assert resultado["percentual_desconto"] == Decimal("10.125")
        assert resultado["servicos"] == itens()
        assert resultado["subtotal_geral"] == Decimal("23.03")
        assert resultado["valor_desconto"] == Decimal("2.33")
        assert resultado["total"] == Decimal("20.70")
        assert resultado["criado_em"].endswith("+00:00")
        assert banco.execute(
            "SELECT valor_unitario_centavos FROM itens_orcamento ORDER BY id"
        ).fetchone()[0] == 101
    finally:
        banco.close()


def test_listagem_vazia_e_consulta_inexistente(conexao):
    assert listar_orcamentos(conexao) == []
    assert buscar_orcamento(conexao, 1) is None


def test_orcamentos_independentes_e_ordenados(conexao):
    primeiro = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    segundo = salvar_orcamento(conexao, "Bruno", [itens()[1]], Decimal("100"))
    registros = listar_orcamentos(conexao)

    assert [registro["id"] for registro in registros] == [segundo, primeiro]
    assert [registro["quantidade_servicos"] for registro in registros] == [1, 2]
    assert len(buscar_orcamento(conexao, primeiro)["servicos"]) == 2
    assert len(buscar_orcamento(conexao, segundo)["servicos"]) == 1
    assert buscar_orcamento(conexao, segundo)["total"] == Decimal("0.00")


@pytest.mark.parametrize("cliente", ["", "  ", None])
def test_cliente_invalido_nao_grava(conexao, cliente):
    with pytest.raises(ValueError):
        salvar_orcamento(conexao, cliente, itens(), Decimal("0"))
    assert listar_orcamentos(conexao) == []


def test_servicos_invalidos_nao_gravam(conexao):
    with pytest.raises(ValueError):
        salvar_orcamento(conexao, "Ana", [], Decimal("0"))
    assert listar_orcamentos(conexao) == []


@pytest.mark.parametrize("identificador", [0, -1, True, "1", 2**63])
def test_identificador_invalido(conexao, identificador):
    with pytest.raises(ValueError):
        buscar_orcamento(conexao, identificador)


def test_falha_no_segundo_item_desfaz_toda_a_gravacao(conexao):
    # Simula uma falha depois que cabeçalho e primeiro item já foram inseridos.
    conexao.execute("""
        CREATE TRIGGER simular_falha BEFORE INSERT ON itens_orcamento
        WHEN NEW.nome = 'Revisão'
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;
    """)
    with pytest.raises(sqlite3.IntegrityError):
        salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    assert listar_orcamentos(conexao) == []
    assert conexao.execute("SELECT COUNT(*) FROM itens_orcamento").fetchone()[0] == 0


def test_texto_com_apostrofo_preservado(conexao):
    nome = "D'Ávila; DROP TABLE orcamentos;"
    identificador = salvar_orcamento(conexao, nome, itens(), Decimal("0"))
    assert buscar_orcamento(conexao, identificador)["cliente"] == nome
    assert len(listar_orcamentos(conexao)) == 1


def test_chave_estrangeira_impede_item_orfao(conexao):
    with pytest.raises(sqlite3.IntegrityError):
        with conexao:
            conexao.execute("""INSERT INTO itens_orcamento
                (orcamento_id, nome, quantidade, valor_unitario_centavos)
                VALUES (999, 'Serviço', 1, 100)""")


def test_novo_orcamento_comeca_pendente(conexao):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    assert buscar_orcamento(conexao, identificador)["status"] == "pendente"
    assert listar_orcamentos(conexao)[0]["status"] == "pendente"


@pytest.mark.parametrize("status", ["cancelado", "", None])
def test_banco_rejeita_status_invalido(conexao, status):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    with pytest.raises(sqlite3.IntegrityError):
        with conexao:
            conexao.execute("UPDATE orcamentos SET status = ? WHERE id = ?", (status, identificador))
    assert buscar_orcamento(conexao, identificador)["status"] == "pendente"


def test_migracao_preserva_dados_e_pode_ser_repetida(tmp_path):
    caminho = tmp_path / "antigo.db"
    antigo = sqlite3.connect(caminho)
    # Estrutura anterior à introdução da coluna status.
    antigo.executescript("""
        CREATE TABLE orcamentos (
            id INTEGER PRIMARY KEY,
            cliente TEXT NOT NULL,
            percentual_desconto TEXT NOT NULL,
            criado_em TEXT NOT NULL
        );
        CREATE TABLE itens_orcamento (
            id INTEGER PRIMARY KEY,
            orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id),
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            valor_unitario_centavos INTEGER NOT NULL
        );
        INSERT INTO orcamentos VALUES (7, 'Bruno', '10', '2026-11-10T00:00:00+00:00');
        INSERT INTO itens_orcamento VALUES (9, 7, 'Tomadas', 10, 1500);
    """)
    antigo.close()

    banco = abrir_banco(caminho)
    try:
        resultado = buscar_orcamento(banco, 7)
        assert resultado["status"] == "pendente"
        assert resultado["cliente"] == "Bruno"
        assert resultado["criado_em"] == "2026-11-10T00:00:00+00:00"
        assert resultado["percentual_desconto"] == Decimal("10")
        assert resultado["servicos"] == [criar_item("Tomadas", 10, Decimal("15"))]
        assert resultado["total"] == Decimal("135.00")
        assert banco.execute("SELECT id FROM itens_orcamento").fetchone()[0] == 9
        with banco:
            banco.execute("UPDATE orcamentos SET status = 'aprovado' WHERE id = 7")
    finally:
        banco.close()

    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, 7)["status"] == "aprovado"
        assert len(listar_orcamentos(banco)) == 1
        colunas = banco.execute("PRAGMA table_info(orcamentos)").fetchall()
        assert [coluna["name"] for coluna in colunas].count("status") == 1
        novo_id = salvar_orcamento(banco, "Ana", itens(), Decimal("0"))
        assert buscar_orcamento(banco, novo_id)["status"] == "pendente"
    finally:
        banco.close()


@pytest.mark.parametrize("inicial", ["pendente", "aprovado", "recusado"])
@pytest.mark.parametrize("destino", ["pendente", "aprovado", "recusado"])
def test_transicoes_livres_de_status(conexao, inicial, destino):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("10"))
    outro = salvar_orcamento(conexao, "Bruno", itens(), Decimal("0"))
    assert alterar_status(conexao, identificador, inicial) is True
    antes = buscar_orcamento(conexao, identificador)

    assert alterar_status(conexao, identificador, destino) is True
    depois = buscar_orcamento(conexao, identificador)
    assert depois == {**antes, "status": destino}
    assert buscar_orcamento(conexao, outro)["status"] == "pendente"
    assert listar_orcamentos(conexao)[1]["status"] == destino


@pytest.mark.parametrize("status", ["cancelado", "", None, 1, "APROVADO"])
def test_alterar_status_invalido_preserva_registro(conexao, status):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    with pytest.raises(ValueError, match="status"):
        alterar_status(conexao, identificador, status)
    assert buscar_orcamento(conexao, identificador)["status"] == "pendente"


@pytest.mark.parametrize("identificador", [0, -1, True, "1", 2**63])
def test_alterar_status_identificador_invalido(conexao, identificador):
    with pytest.raises(ValueError, match="identificador"):
        alterar_status(conexao, identificador, "aprovado")
    assert listar_orcamentos(conexao) == []


def test_alterar_status_inexistente(conexao):
    assert alterar_status(conexao, 999, "aprovado") is False
    assert listar_orcamentos(conexao) == []


def test_status_alterado_persiste_apos_reabrir(tmp_path):
    caminho = tmp_path / "status.db"
    banco = abrir_banco(caminho)
    try:
        identificador = salvar_orcamento(banco, "Ana", itens(), Decimal("0"))
        assert alterar_status(banco, identificador, "recusado") is True
    finally:
        banco.close()

    banco = abrir_banco(caminho)
    try:
        assert buscar_orcamento(banco, identificador)["status"] == "recusado"
    finally:
        banco.close()


@pytest.mark.parametrize("status", ["pendente", "aprovado", "recusado"])
def test_filtro_por_status_preserva_ordem_e_contagem(conexao, status):
    primeiro = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    segundo = salvar_orcamento(conexao, "Bruno", [itens()[0]], Decimal("0"))
    outro = salvar_orcamento(conexao, "Carla", itens(), Decimal("0"))
    alterar_status(conexao, primeiro, status)
    alterar_status(conexao, segundo, status)
    alterar_status(conexao, outro, "recusado" if status != "recusado" else "aprovado")

    registros = listar_orcamentos(conexao, status=status)
    assert [r["id"] for r in registros] == [segundo, primeiro]
    assert [r["quantidade_servicos"] for r in registros] == [1, 2]
    assert all(r["status"] == status for r in registros)
    assert len(listar_orcamentos(conexao)) == 3
    assert listar_orcamentos(conexao, status=None) == listar_orcamentos(conexao)


def test_filtro_sem_resultados(conexao):
    salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    assert listar_orcamentos(conexao, status="aprovado") == []


@pytest.mark.parametrize("status", ["", "cancelado", "APROVADO", 1, "' OR 1=1 --"])
def test_filtro_invalido(conexao, status):
    with pytest.raises(ValueError, match="status"):
        listar_orcamentos(conexao, status=status)


@pytest.mark.parametrize("termo", ["Bruno", "bruno", " Henrique "])
def test_busca_parcial_cliente_com_status(conexao, termo):
    primeiro = salvar_orcamento(conexao, "Bruno Henrique", itens(), Decimal("0"))
    segundo = salvar_orcamento(conexao, "Bruno Henrique", [itens()[0]], Decimal("0"))
    terceiro = salvar_orcamento(conexao, "Bruno Henrique", itens(), Decimal("0"))
    salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    alterar_status(conexao, terceiro, "aprovado")
    registros = listar_orcamentos(conexao, status="pendente", cliente=termo)
    assert [r["id"] for r in registros] == [segundo, primeiro]
    assert [r["quantidade_servicos"] for r in registros] == [1, 2]
    assert len(listar_orcamentos(conexao, cliente=termo)) == 3


@pytest.mark.parametrize("termo", [None, "", "  "])
def test_cliente_vazio_nao_filtra(conexao, termo):
    salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    assert listar_orcamentos(conexao, cliente=termo) == listar_orcamentos(conexao)


@pytest.mark.parametrize("termo", ["%", "_", "!", "D'Ávila", "' OR 1=1 --"])
def test_busca_caracteres_literais(conexao, termo):
    identificador = salvar_orcamento(conexao, f"Cliente {termo}", itens(), Decimal("0"))
    salvar_orcamento(conexao, "Outro cliente", itens(), Decimal("0"))
    assert [r["id"] for r in listar_orcamentos(conexao, cliente=termo)] == [identificador]


def test_cliente_sem_correspondencia(conexao):
    salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    assert listar_orcamentos(conexao, cliente="Bruno") == []


@pytest.mark.parametrize("cliente", [1, True, []])
def test_filtro_cliente_tipo_invalido(conexao, cliente):
    with pytest.raises(ValueError, match="texto"):
        listar_orcamentos(conexao, cliente=cliente)


@pytest.mark.parametrize("status", ["pendente", "aprovado", "recusado"])
def test_duplicacao_preserva_original_e_copia_dados(conexao, status):
    original_id = salvar_orcamento(conexao, "Ana", itens(), Decimal("10.125"))
    alterar_status(conexao, original_id, status)
    # Data fixa antiga permite conferir que a cópia recebeu uma nova data.
    with conexao:
        conexao.execute("UPDATE orcamentos SET criado_em = ? WHERE id = ?",
                        ("2020-01-01T00:00:00+00:00", original_id))
    original = buscar_orcamento(conexao, original_id)
    copia_id = duplicar_orcamento(conexao, original_id)
    copia = buscar_orcamento(conexao, copia_id)
    assert copia_id != original_id
    assert copia["criado_em"] != original["criado_em"]
    assert copia["status"] == "pendente"
    for campo in ("cliente", "servicos", "percentual_desconto", "subtotal_geral", "valor_desconto", "total"):
        assert copia[campo] == original[campo]
    assert buscar_orcamento(conexao, original_id) == original
    ids_original = {r[0] for r in conexao.execute(
        "SELECT id FROM itens_orcamento WHERE orcamento_id = ?", (original_id,))}
    ids_copia = {r[0] for r in conexao.execute(
        "SELECT id FROM itens_orcamento WHERE orcamento_id = ?", (copia_id,))}
    assert len(ids_copia) == len(ids_original) == 2
    assert ids_original.isdisjoint(ids_copia)
    alterar_status(conexao, copia_id, "recusado")
    assert buscar_orcamento(conexao, original_id) == original


def test_duplicacao_inexistente_nao_grava(conexao):
    assert duplicar_orcamento(conexao, 999) is None
    assert listar_orcamentos(conexao) == []


@pytest.mark.parametrize("identificador", [0, -1, True, "1", 2**63])
def test_duplicacao_identificador_invalido(conexao, identificador):
    with pytest.raises(ValueError):
        duplicar_orcamento(conexao, identificador)
    assert listar_orcamentos(conexao) == []


def test_duplicacao_falha_desfaz_copia(conexao):
    original_id = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    original = buscar_orcamento(conexao, original_id)
    conexao.execute("""
        CREATE TRIGGER falhar_copia BEFORE INSERT ON itens_orcamento
        WHEN NEW.nome = 'Revisão'
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;
    """)
    with pytest.raises(sqlite3.IntegrityError):
        duplicar_orcamento(conexao, original_id)
    assert len(listar_orcamentos(conexao)) == 1
    assert conexao.execute("SELECT COUNT(*) FROM itens_orcamento").fetchone()[0] == 2
    assert buscar_orcamento(conexao, original_id) == original


@pytest.mark.parametrize("status", ["pendente", "aprovado", "recusado"])
def test_edicao_preserva_campos_e_outros_orcamentos(conexao, status):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    outro = salvar_orcamento(conexao, "Bruno", itens(), Decimal("10"))
    alterar_status(conexao, identificador, status)
    antes = buscar_orcamento(conexao, identificador)
    outro_antes = buscar_orcamento(conexao, outro)
    assert editar_orcamento(conexao, identificador, " Maria ", Decimal("10")) is True
    depois = buscar_orcamento(conexao, identificador)
    assert depois["cliente"] == "Maria"
    assert depois["percentual_desconto"] == Decimal("10")
    assert depois["valor_desconto"] == Decimal("2.30")
    assert depois["total"] == Decimal("20.73")
    for campo in ("id", "criado_em", "status", "servicos", "subtotal_geral"):
        assert depois[campo] == antes[campo]
    assert buscar_orcamento(conexao, outro) == outro_antes


@pytest.mark.parametrize("cliente, desconto", [
    ("", Decimal("0")), ("  ", Decimal("0")), (None, Decimal("0")),
    ("Maria", Decimal("-1")), ("Maria", Decimal("101")),
    ("Maria", Decimal("NaN")), ("Maria", Decimal("Infinity")),
    ("Maria", Decimal("sNaN")), ("Maria", 10),
])
def test_edicao_invalida_nao_salva_nenhum_campo(conexao, cliente, desconto):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    with pytest.raises(ValueError):
        editar_orcamento(conexao, identificador, cliente, desconto)
    assert buscar_orcamento(conexao, identificador) == antes


@pytest.mark.parametrize("identificador", [0, -1, True, "1", 2**63])
def test_edicao_identificador_invalido(conexao, identificador):
    with pytest.raises(ValueError):
        editar_orcamento(conexao, identificador, "Ana", Decimal("0"))


def test_edicao_inexistente(conexao):
    assert editar_orcamento(conexao, 999, "Ana", Decimal("0")) is False
    assert listar_orcamentos(conexao) == []


def test_edicao_persiste_apos_reabrir(tmp_path):
    caminho = tmp_path / "edicao.db"
    banco = abrir_banco(caminho)
    try:
        identificador = salvar_orcamento(banco, "Ana", itens(), Decimal("0"))
        assert editar_orcamento(banco, identificador, "Maria", Decimal("100")) is True
    finally:
        banco.close()
    banco = abrir_banco(caminho)
    try:
        resultado = buscar_orcamento(banco, identificador)
        assert resultado["cliente"] == "Maria"
        assert resultado["percentual_desconto"] == Decimal("100")
        assert resultado["total"] == Decimal("0.00")
    finally:
        banco.close()


def test_falha_no_update_preserva_orcamento(conexao):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    conexao.execute("""CREATE TRIGGER falhar_edicao BEFORE UPDATE ON orcamentos
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        editar_orcamento(conexao, identificador, "Maria", Decimal("10"))
    assert buscar_orcamento(conexao, identificador) == antes


@pytest.mark.parametrize("status", ["pendente", "aprovado", "recusado"])
def test_editar_item_preserva_cabecalho_e_outros_itens(conexao, status):
    servicos = [criar_item("Tomadas", 1, Decimal("10"))] * 2
    orcamento_id = salvar_orcamento(conexao, "Ana", servicos, Decimal("10"))
    alterar_status(conexao, orcamento_id, status)
    antes = buscar_orcamento(conexao, orcamento_id)
    itens_antes = listar_itens_orcamento(conexao, orcamento_id)
    item_id = itens_antes[1]["id"]
    assert editar_item(conexao, orcamento_id, item_id, " Revisão ", 3, Decimal("1.005")) is True
    depois = buscar_orcamento(conexao, orcamento_id)
    itens_depois = listar_itens_orcamento(conexao, orcamento_id)
    assert itens_depois[0] == itens_antes[0]
    assert itens_depois[1] == {"id": item_id, **criar_item("Revisão", 3, Decimal("1.01"))}
    assert depois["subtotal_geral"] == Decimal("13.03")
    assert depois["total"] == Decimal("11.73")
    for campo in ("id", "cliente", "criado_em", "status", "percentual_desconto"):
        assert depois[campo] == antes[campo]


def test_item_de_outro_orcamento_nao_pode_ser_editado(conexao):
    primeiro = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    segundo = salvar_orcamento(conexao, "Bruno", itens(), Decimal("0"))
    item_id = listar_itens_orcamento(conexao, segundo)[0]["id"]
    antes = buscar_orcamento(conexao, segundo)
    assert editar_item(conexao, primeiro, item_id, "Novo", 2, Decimal("5")) is False
    assert buscar_orcamento(conexao, segundo) == antes
    assert editar_item(conexao, primeiro, 999, "Novo", 2, Decimal("5")) is False
    assert editar_item(conexao, 999, item_id, "Novo", 2, Decimal("5")) is False


@pytest.mark.parametrize("nome, quantidade, preco", [
    (" ", 1, "10"), ("Novo", 0, "10"), ("Novo", True, "10"),
    ("Novo", 1000001, "10"), ("Novo", 1, "0.001"),
    ("Novo", 1, "NaN"), ("Novo", 1, "Infinity"), ("Novo", 1, "1e30"),
])
def test_edicao_item_invalida_preserva_dados(conexao, nome, quantidade, preco):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    item_id = listar_itens_orcamento(conexao, identificador)[0]["id"]
    with pytest.raises(ValueError):
        editar_item(conexao, identificador, item_id, nome, quantidade, Decimal(preco))
    assert buscar_orcamento(conexao, identificador) == antes


def test_edicao_item_rejeita_soma_acima_do_limite(conexao):
    identificador = salvar_orcamento(conexao, "Ana", [
        criar_item("A", 1, Decimal("600000000000")),
        criar_item("B", 1, Decimal("1")),
    ], Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    item_id = listar_itens_orcamento(conexao, identificador)[1]["id"]
    with pytest.raises(ValueError, match="subtotal geral"):
        editar_item(conexao, identificador, item_id, "Novo", 1, Decimal("600000000000"))
    assert buscar_orcamento(conexao, identificador) == antes


@pytest.mark.parametrize("orcamento_id, item_id", [(0, 1), (1, True), (1, 2**63)])
def test_edicao_item_identificadores_invalidos(conexao, orcamento_id, item_id):
    with pytest.raises(ValueError):
        editar_item(conexao, orcamento_id, item_id, "Novo", 1, Decimal("10"))


def test_falha_na_edicao_item_desfaz_alteracao(conexao):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    item_id = listar_itens_orcamento(conexao, identificador)[0]["id"]
    conexao.execute("""CREATE TRIGGER falhar_item BEFORE UPDATE ON itens_orcamento
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        editar_item(conexao, identificador, item_id, "Novo", 2, Decimal("10"))
    assert buscar_orcamento(conexao, identificador) == antes


@pytest.mark.parametrize("status", ["pendente", "aprovado", "recusado"])
def test_incluir_remover_preserva_cabecalho_e_outros_itens(conexao, status):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("10"))
    alterar_status(conexao, identificador, status)
    antes = buscar_orcamento(conexao, identificador)
    itens_antes = listar_itens_orcamento(conexao, identificador)
    novo_id = adicionar_item(conexao, identificador, " Instalação ", 3, Decimal("1.005"))
    depois = buscar_orcamento(conexao, identificador)
    assert depois["subtotal_geral"] == Decimal("26.06")
    assert depois["total"] == Decimal("23.45")
    assert listar_itens_orcamento(conexao, identificador)[:-1] == itens_antes
    assert listar_itens_orcamento(conexao, identificador)[-1] == {
        "id": novo_id, **criar_item("Instalação", 3, Decimal("1.01"))}
    for campo in ("id", "cliente", "criado_em", "status", "percentual_desconto"):
        assert depois[campo] == antes[campo]
    assert listar_orcamentos(conexao)[0]["quantidade_servicos"] == 3
    assert remover_item(conexao, identificador, novo_id) is True
    assert buscar_orcamento(conexao, identificador) == antes
    assert listar_itens_orcamento(conexao, identificador) == itens_antes
    assert listar_orcamentos(conexao)[0]["quantidade_servicos"] == 2


def test_remover_ultimo_item_e_bloqueado(conexao):
    identificador = salvar_orcamento(conexao, "Ana", [itens()[0]], Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    item_id = listar_itens_orcamento(conexao, identificador)[0]["id"]
    with pytest.raises(ValueError, match="último serviço"):
        remover_item(conexao, identificador, item_id)
    assert buscar_orcamento(conexao, identificador) == antes


def test_remover_item_de_outro_orcamento_ou_inexistente(conexao):
    primeiro = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    segundo = salvar_orcamento(conexao, "Bruno", itens(), Decimal("0"))
    antes = buscar_orcamento(conexao, segundo)
    item_id = listar_itens_orcamento(conexao, segundo)[0]["id"]
    assert remover_item(conexao, primeiro, item_id) is False
    assert remover_item(conexao, primeiro, 999) is False
    assert remover_item(conexao, 999, item_id) is False
    assert buscar_orcamento(conexao, segundo) == antes


def test_adicionar_em_orcamento_inexistente(conexao):
    assert adicionar_item(conexao, 999, "Serviço", 1, Decimal("10")) is None
    assert conexao.execute("SELECT COUNT(*) FROM itens_orcamento").fetchone()[0] == 0


@pytest.mark.parametrize("nome, quantidade, preco", [
    (" ", 1, "10"), ("Novo", 0, "10"), ("Novo", True, "10"),
    ("Novo", 1000001, "10"), ("Novo", 1, "0.001"),
    ("Novo", 1, "NaN"), ("Novo", 1, "Infinity"), ("Novo", 1, "1e30"),
])
def test_adicionar_item_invalido_nao_grava(conexao, nome, quantidade, preco):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    with pytest.raises(ValueError):
        adicionar_item(conexao, identificador, nome, quantidade, Decimal(preco))
    assert buscar_orcamento(conexao, identificador) == antes


def test_adicionar_item_rejeita_soma_acima_do_limite(conexao):
    identificador = salvar_orcamento(conexao, "Ana", [
        criar_item("A", 1, Decimal("600000000000"))], Decimal("100"))
    antes = buscar_orcamento(conexao, identificador)
    with pytest.raises(ValueError, match="subtotal geral"):
        adicionar_item(conexao, identificador, "B", 1, Decimal("600000000000"))
    assert buscar_orcamento(conexao, identificador) == antes


@pytest.mark.parametrize("identificador", [0, -1, True, "1", 2**63])
def test_adicionar_remover_identificadores_invalidos(conexao, identificador):
    with pytest.raises(ValueError):
        adicionar_item(conexao, identificador, "A", 1, Decimal("10"))
    with pytest.raises(ValueError):
        remover_item(conexao, identificador, 1)
    with pytest.raises(ValueError):
        remover_item(conexao, 1, identificador)


@pytest.mark.parametrize("operacao", ["INSERT", "DELETE"])
def test_falha_na_inclusao_ou_remocao_preserva_registros(conexao, operacao):
    identificador = salvar_orcamento(conexao, "Ana", itens(), Decimal("0"))
    antes = buscar_orcamento(conexao, identificador)
    itens_antes = listar_itens_orcamento(conexao, identificador)
    # Operação vem de uma lista fixa do teste, não de uma entrada de usuário.
    conexao.execute(f"""CREATE TRIGGER falhar_operacao BEFORE {operacao} ON itens_orcamento
        BEGIN SELECT RAISE(ABORT, 'falha simulada'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        if operacao == "INSERT":
            adicionar_item(conexao, identificador, "Novo", 1, Decimal("10"))
        else:
            remover_item(conexao, identificador, itens_antes[0]["id"])
    assert buscar_orcamento(conexao, identificador) == antes
    assert listar_itens_orcamento(conexao, identificador) == itens_antes


def test_inclusao_remocao_persistem_e_nao_afetam_copia(tmp_path):
    caminho = tmp_path / "itens.db"
    banco = abrir_banco(caminho)
    try:
        identificador = salvar_orcamento(banco, "Ana", itens(), Decimal("10"))
        copia_id = duplicar_orcamento(banco, identificador)
        copia_antes = buscar_orcamento(banco, copia_id)
        primeiro_id = listar_itens_orcamento(banco, identificador)[0]["id"]
        novo_id = adicionar_item(banco, identificador, "Novo", 2, Decimal("10"))
        assert remover_item(banco, identificador, primeiro_id) is True
    finally:
        banco.close()
    banco = abrir_banco(caminho)
    try:
        resultado = buscar_orcamento(banco, identificador)
        assert [i["nome"] for i in resultado["servicos"]] == ["Revisão", "Novo"]
        assert resultado["total"] == Decimal("36.00")
        assert listar_itens_orcamento(banco, identificador)[-1]["id"] == novo_id
        assert buscar_orcamento(banco, copia_id) == copia_antes
    finally:
        banco.close()
