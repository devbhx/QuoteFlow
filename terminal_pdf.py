"""Configuração do prestador e comando de exportação do documento."""

from repositorio import buscar_prestador, salvar_prestador, validar_identificador


def configurar_prestador_no_terminal(conexao):
    atual = buscar_prestador(conexao) or {"nome": "", "contato": ""}
    print(f"Prestador atual: {atual['nome'] or 'não configurado'}")
    print(f"Contato atual: {atual['contato'] or 'não informado'}")
    nome = input("Nome do prestador (Enter para manter): ")
    contato = input("Contato (Enter para manter, - para limpar): ")
    nome = atual["nome"] if nome == "" else nome
    contato = atual["contato"] if contato == "" else ("" if contato.strip() == "-" else contato)
    try:
        salvar_prestador(conexao, nome, contato)
    except ValueError as erro:
        print(f"Erro: {erro} Nenhuma alteração foi salva.")
        return
    print("Dados do prestador salvos.")


def exportar_pdf_no_terminal(conexao):
    try:
        identificador = int(input("Número do orçamento a exportar: "))
        validar_identificador(identificador)
    except ValueError:
        print("Erro: informe um identificador inteiro positivo válido.")
        return
    try:
        # Importação local mantém as outras opções disponíveis sem a dependência.
        from exportacao_pdf import exportar_orcamento
        caminho = exportar_orcamento(conexao, identificador)
    except ModuleNotFoundError:
        print("Erro: instale as dependências com python -m pip install -r requirements.txt.")
        return
    except ValueError as erro:
        print(f"Erro: {erro}")
        return
    except OSError:
        print("Erro: não foi possível gravar o PDF. Verifique a pasta de exportação.")
        return
    if caminho is None:
        print("Orçamento não encontrado.")
    else:
        print(f"PDF exportado: {caminho}")
