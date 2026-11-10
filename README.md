# QuoteFlow

MVP local de criação e gerenciamento de orçamentos para prestadores de serviços e pequenos negócios, desenvolvido em Python para estudo e portfólio.

> **Status:** MVP de terminal com persistência SQLite e gestão básica de orçamentos.
> **Validação atual:** 294 testes automatizados aprovados no ambiente de referência.

## Sobre o projeto

O QuoteFlow permite elaborar e gerenciar orçamentos pelo terminal. O projeto é
desenvolvido de forma incremental, combinando aprendizado de programação,
testes automatizados e construção de um portfólio profissional.

Este repositório público contém a versão demonstrativa local. A evolução para um
SaaS comercial será planejada separadamente, em repositório privado, antes de
introduzir funcionalidades proprietárias, integrações e infraestrutura comercial.

## Funcionalidades implementadas

- Criação de orçamentos com nome do cliente e múltiplos serviços.
- Cálculo de subtotais, desconto percentual e total com `Decimal`.
- Arredondamento comercial e apresentação monetária no padrão brasileiro.
- Persistência SQLite, listagem e consulta por identificador.
- Filtros combinados por status e parte do nome do cliente.
- Status `pendente`, `aprovado` e `recusado`, com transições livres.
- Duplicação independente de propostas, com status inicial `pendente`.
- Edição de cliente, desconto, nome do serviço, quantidade e preço.
- Inclusão e remoção de itens; confirmação de remoção e proteção do último item.
- Validações numéricas e gravações em transações.
- Atualização automática de bancos antigos para status e campos comerciais.
- Configuração local do nome e contato do prestador.
- Validade, condições de pagamento e observações opcionais por orçamento.
- Exportação local em PDF A4, com tabelas, múltiplas páginas e fontes com acentos.
- Testes de cálculos, formatação, validações, persistência, migração, terminal e PDFs.

## Escopo e limitações

A aplicação funciona localmente, com um banco por instalação. Não há autenticação,
autorização por usuário, isolamento por empresa, acesso externo do cliente,
aprovação por link, interface web, assinaturas ou pagamentos.
O nome do cliente fica em cada orçamento; não há cadastro independente de clientes
nem histórico de alterações. As operações administrativas estão disponíveis para
quem tem acesso ao programa local. O MVP não está preparado para exposição como
serviço web ou uso simultâneo por múltiplas empresas.

## Tecnologias utilizadas

- Python
- SQLite (módulo `sqlite3` da biblioteca padrão)
- Biblioteca Decimal
- ReportLab para geração de PDF
- Pytest e pypdf para testes
- Git e GitHub

## Como executar

Ambiente de referência validado: Python 3.15 e pytest 9.2.0.
O programa utiliza ReportLab 5.1.0 para exportar PDFs, além da biblioteca padrão.
Pytest 9.2.0 e pypdf 6.21.4 são usados somente no desenvolvimento para executar
testes e validar os documentos. As fontes Vera são fornecidas pelo ReportLab;
não é necessário instalar fontes do sistema para os caracteres portugueses.

Na pasta do projeto (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python main.py
```

Para instalar somente as dependências de execução, use
`python -m pip install -r requirements.txt`. O arquivo `requirements-dev.txt`
já inclui essas dependências.

## Como executar os testes

Com o ambiente virtual ativado, execute a suíte completa:

```bash
python -m pytest -v
```

## Regras monetárias e limites iniciais

- Valores usam `Decimal`, com arredondamento `ROUND_HALF_UP`: `1,005` vira `1,01`.
- O preço unitário é arredondado para centavos antes da multiplicação pela quantidade.
- O desconto é aplicado à soma dos subtotais e arredondado para centavos antes da subtração.
- A apresentação monetária usa a mesma regra de arredondamento.
- Preços devem ser positivos e resultar em pelo menos R$ 0,01 após arredondar.
- Quantidades são inteiras entre 1 e 1.000.000.
- Preço unitário, subtotal por serviço e subtotal geral têm limite de R$ 999.999.999.999,99, antes do desconto.
- Descontos vão de 0% a 100%, inclusive.
- Valores aceitam vírgula ou ponto decimal, sem separador de milhares: `1234,56` ou `1234.56`.

Os limites são escolhas iniciais ajustáveis, centralizadas em `orcamento.py`.
Se um serviço exceder o limite, o terminal solicita seu cadastro novamente.
Se a soma exceder o limite durante a criação, o programa informa que o orçamento
não foi gerado e retorna ao menu. Nos orçamentos já salvos, a edição valida os
novos totais antes de gravar.

## Organização

- `main.py`: interface de terminal; importar o módulo não inicia o programa.
- `repositorio.py`: criação das tabelas, gravação e consultas SQLite.
- `orcamento.py`: validações e composição do orçamento.
- `calculos.py`: operações monetárias.
- `formatacao.py`: apresentação em reais.
- `dados_comerciais.py`: validação de textos comerciais e validade.
- `exportacao_pdf.py`: montagem do documento e gravação sem sobrescrever arquivos.
- `requirements.txt`: dependência de execução para exportação.
- `test_*.py`: testes automatizados com bancos temporários.
- `requirements-dev.txt`: dependência de desenvolvimento para executar os testes.
- `treino_funcoes.py`: exercício independente de estudo, não é o fluxo oficial da aplicação.

## Salvar e consultar orçamentos

Ao executar `python main.py`, o menu oferece:

1. Criar e salvar orçamento: ao concluir um orçamento válido, informa seu número.
2. Listar orçamentos: permite filtrar por `pendente`, `aprovado` ou `recusado`;
   pressione Enter para listar todos. Mostra número, cliente, data, quantidade de
   serviços e status. Em seguida, permite buscar por parte do nome do cliente,
   combinando os dois filtros. Deixe o nome vazio para incluir todos os clientes.
   `%` e `_` são buscados literalmente. A busca ignora diferenças entre maiúsculas
   e minúsculas ASCII, mas não normaliza acentos ou letras Unicode.
3. Consultar orçamento: recebe o número e apresenta status, serviços e totais.
4. Alterar status: recebe o número e um dos status disponíveis.
5. Duplicar orçamento: recebe o número do original e informa o número da cópia.
6. Editar cliente e desconto: recebe o número e mostra os valores atuais; Enter mantém cada campo.
7. Editar serviço: recebe o orçamento, mostra os IDs dos itens e permite editar um deles.
8. Adicionar serviço: inclui um novo item em um orçamento salvo.
9. Remover serviço: seleciona pelo ID e solicita confirmação; mantém ao menos um item.
10. Configurar prestador: nome obrigatório e contato opcional.
11. Editar validade, pagamento e observações de um orçamento salvo.
12. Exportar orçamento em PDF: requer o nome do prestador configurado na opção 10.
0. Sair.

O arquivo `quoteflow.db` é criado automaticamente ao lado de `main.py`,
independentemente da pasta de onde o comando for executado. Fechar o programa
não apaga os registros. O arquivo do banco e seus auxiliares são ignorados pelo Git.
Os testes usam bancos temporários, sem acessar os dados reais.

### Modelo e conceitos desta sprint

| Tabela | Campos principais | Responsabilidade |
|---|---|---|
| `orcamentos` | `id`, `cliente`, `percentual_desconto`, `criado_em`, `status`, `validade`, `condicoes_pagamento`, `observacoes` | Identificação e dados gerais |
| `configuracao_prestador` | `id` fixo em 1, `nome`, `contato` | Configuração local reutilizável |
| `itens_orcamento` | `id`, `orcamento_id`, `nome`, `quantidade`, `valor_unitario_centavos` | Serviços de cada orçamento |

O `id` é uma **chave primária**, que identifica um registro. O `orcamento_id`
é uma **chave estrangeira**: cada item pertence a um orçamento existente.
Um orçamento pode ter vários itens; essa é uma relação de um para muitos.

Preços são armazenados como centavos inteiros (`10,50` vira `1050`), e o
percentual como texto para preservar exatamente seu `Decimal`. Subtotais,
desconto em reais e total são recalculados pelas regras atuais ao consultar.
Se as regras de cálculo mudarem no futuro, será necessário definir como preservar
os valores históricos antes de aplicar a mudança aos orçamentos existentes.

A gravação utiliza uma **transação**: cabeçalho e itens são confirmados juntos;
se um item falhar, toda a gravação é desfeita. Consultas usam parâmetros `?`,
mantendo o texto informado pelo usuário separado do código SQL.
As datas são guardadas em UTC e exibidas no horário local do computador.

Objetivo da sprint: salvar e recuperar orçamentos após reabrir o programa.
Critérios de conclusão: preservar preços, serviços e desconto; listar registros;
consultar identificadores; tratar ausência e falhas de gravação.
Os testes verificam persistência, precisão monetária, isolamento entre orçamentos,
transações e o fluxo do menu.

Esta etapa mantém o nome do cliente em cada orçamento. Cadastro independente
de clientes e exclusão de orçamentos inteiros serão especificados em etapas futuras.

## Status dos orçamentos

A tabela `orcamentos` possui a coluna `status`, com padrão `pendente`.
O banco aceita somente `pendente`, `aprovado` ou `recusado`.
Ao abrir um banco antigo, o programa verifica suas colunas e adiciona `status`
automaticamente, atribuindo `pendente` aos registros existentes sem apagar dados.
Abrir novamente não repete a alteração nem redefine status já gravados.

As funções de listagem e consulta já retornam esse campo. A função
`alterar_status(conexao, identificador, novo_status)` permite transições livres
entre as três opções, inclusive repetir o status atual. Retorna `True` para um
orçamento existente, `False` para um inexistente e lança `ValueError` para
identificador ou status inválido. O menu mostra o status na listagem e na consulta,
e a opção 4 permite alterá-lo. No terminal, espaços nas extremidades são removidos
e letras maiúsculas são convertidas para minúsculas. Entradas inválidas ou números
inexistentes apresentam uma mensagem e retornam ao menu.
Os testes verificam valor padrão, rejeição de status inválido e atualização de um
banco antigo com preservação dos registros.

## Duplicação de orçamentos

A opção 5 copia cliente, serviços e desconto, gerando um novo número e registrando
uma nova data de criação em UTC. Como as datas têm precisão de segundos, duas
criações no mesmo segundo podem mostrar o mesmo horário. A cópia sempre começa
como `pendente`, independentemente do status original. O original permanece intacto.
As duas propostas possuem registros de itens separados; mudar o status de uma não
altera a outra. Identificadores inválidos e orçamentos inexistentes apresentam
mensagens e retornam ao menu.

`duplicar_orcamento()` combina `buscar_orcamento()` e `salvar_orcamento()`,
reutilizando as validações, os cálculos atuais e a transação de gravação. A cópia
é salva por inteiro ou nenhuma parte dela é gravada. Não foi necessário alterar
a estrutura do banco.

## Edição de cliente e desconto

A opção 6 permite editar esses dois campos em qualquer status. Enter, sem digitar
nada, mantém o valor atual. Um nome composto apenas de espaços é rejeitado.
O desconto aceita vírgula ou ponto decimal e deve ser finito entre 0% e 100%.
Entradas inválidas retornam ao menu sem salvar nenhuma das alterações.
Número, data de criação, serviços e status são preservados; os totais são
recalculados na consulta com o novo desconto. Não há histórico das edições nesta etapa.
Cliente e desconto são gravados juntos, por um `UPDATE` parametrizado em uma
transação. O cadastro de cliente aqui continua sendo apenas o nome no orçamento.

## Edição de serviços

A opção 7 permite alterar nome, quantidade e preço de um serviço existente.
Primeiro informe o orçamento e depois o ID do item mostrado na tela. Mesmo com
nomes repetidos, cada item é identificado separadamente. Enter mantém o campo;
preços aceitam vírgula ou ponto e seguem o arredondamento monetário atual.
O item precisa pertencer ao orçamento escolhido. Dados inválidos ou uma alteração
que exceda o limite do subtotal geral são rejeitados sem gravação parcial.
Cliente, desconto, status, data e outros itens permanecem iguais. Os totais são
recalculados com os novos valores.

As opções de edição são administrativas. Nesta versão local não há autenticação
nem controle de acesso por usuário. Na versão web, a edição será restrita ao
proprietário autorizado; o cliente destinatário poderá visualizar e aprovar ou
recusar a proposta. Essas permissões ainda não estão implementadas.

## Inclusão e remoção de serviços

A opção 8 reutiliza as validações de nome, preço e quantidade. Antes de incluir,
o sistema valida a soma de todos os itens com o desconto atual. Se exceder os
limites, nenhum item é gravado. Serviços com nomes iguais continuam permitidos.

A opção 9 mostra os IDs e solicita confirmação com `s` ou `n`. Cancelar preserva
os dados. A remoção também verifica no repositório que o item pertence ao orçamento
e impede remover o último serviço, mesmo quando chamada fora do terminal.
As duas operações preservam número, cliente, desconto, data, status e demais itens.
A consulta recalcula os totais; a listagem reflete a nova quantidade de serviços.
Ambas são permitidas em qualquer status, conforme a regra atual de edição livre.

## Dados comerciais para o futuro PDF

A opção 10 salva uma única configuração de prestador por instalação. O nome é
obrigatório e o contato é texto livre opcional (telefone, e-mail ou outro contato).
Enter mantém os dados existentes; `-` limpa o contato. Não é preciso configurar
o prestador para continuar criando orçamentos nesta etapa.

A opção 11 edita dados opcionais de um orçamento salvo:

- **Validade:** data em `DD/MM/AAAA` no terminal, armazenada como `AAAA-MM-DD`.
- **Condições de pagamento:** texto livre.
- **Observações:** texto livre.

Enter mantém cada campo; `-` limpa um campo opcional. Uma data inválida impede
salvar todos os campos dessa operação. Em novos orçamentos e alterações da validade,
a data não pode ser anterior à emissão (data de criação exibida no horário local).
O mesmo dia é permitido; a comparação não usa a data de exportação nem exige que
uma proposta histórica tenha validade futura. Datas antigas já gravadas não são
corrigidas automaticamente: consulta, exportação e edição de outros campos mantendo
a mesma validade continuam disponíveis. Não há bloqueio automático de orçamento vencido. Os dados comerciais
aparecem na consulta quando preenchidos e não alteram os cálculos nem o status.
A duplicação copia esses campos, mas a cópia tem uma nova emissão: se a validade
copiada for anterior a ela, a duplicação é recusada sem criar registros ou alterar
o original. Nesse caso, revise explicitamente a validade antes de duplicar. O cadastro do prestador é global e não guarda uma
cópia histórica de sua identidade em cada orçamento.

Bancos existentes recebem as novas colunas vazias sem perder registros; abrir
novamente preserva os dados já preenchidos. Os testes usam somente dados fictícios.

## Exportação de PDF

1. Configure o nome do prestador na opção 10; o contato é opcional.
2. Se desejar, preencha validade, pagamento e observações pela opção 11.
3. Escolha a opção 12 e informe o número de um orçamento salvo.
4. O terminal mostra o caminho absoluto do arquivo gerado.

O documento A4 inclui prestador e contato, número e data de criação da proposta,
cliente, validade quando preenchida, serviços, preços, subtotais, desconto,
total e textos comerciais opcionais. O rodapé mostra a data de exportação com
fuso local e o número da página. As tabelas repetem seu cabeçalho nas páginas
seguintes; textos longos quebram linhas e podem continuar em outra página.
O status é interno ao sistema e não aparece no documento comercial.
A exportação utiliza os cálculos existentes e não modifica o orçamento no banco.
Textos digitados são tratados literalmente, inclusive caracteres como `<` e `&`.

Os arquivos são salvos em `exports/`, ao lado de `main.py`, independentemente da
pasta de execução. O nome segue `orcamento_ID_AAAAMMDD_HHMMSS.pdf`; em caso de
colisão, um sufixo numérico é acrescentado. Nenhum PDF existente é sobrescrito.
O documento é montado em memória antes da gravação. A pasta está ignorada pelo
Git; documentos com dados reais não devem ser adicionados ao repositório.

Esta primeira versão não inclui logo, CPF/CNPJ, endereço, assinatura digital,
aprovação externa ou envio automático. Usa o prestador configurado no momento
da exportação, sem histórico dessa configuração. Uma nova exportação após editar
os dados gera outro arquivo; PDFs anteriores permanecem iguais. Os testes usam
somente dados fictícios e conferem texto extraído, valores e paginação.

Documentação da biblioteca: [ReportLab — tabelas e paginação](https://docs.reportlab.com/reportlab/userguide/ch7_tables/).

## Segurança e publicação

- Não versionar bancos reais, dumps, credenciais, chaves, arquivos `.env` ou documentos com dados de clientes.
- O `.gitignore` protege extensões comuns de SQLite e auxiliares, ambientes virtuais,
  caches, credenciais, temporários e pastas locais de exportação e backup.
- Arquivos `.env.example`, se criados, devem conter somente valores fictícios.
- Antes de cada publicação, revisar arquivos rastreados, não rastreados e o conteúdo
  do commit. O `.gitignore` não remove arquivos já rastreados nem protege contra
  inclusão forçada ou segredos escritos em arquivos de código.
- Usar dados fictícios nos exemplos e testes. Não incluir capturas com dados reais.
- Não há licença open source adicionada nesta etapa. A escolha de licença será discutida separadamente.

A publicação do MVP e a separação da versão comercial são revisadas antes de cada nova fase.

## Próximas etapas

- Avaliar o primeiro PDF com exemplos de uso e priorizar melhorias de apresentação.
- Especificar os próximos recursos antes da implementação.
- Planejar a separação público/privado antes da fase comercial e da evolução para web.

## Autor

Bruno Henrique — [GitHub](https://github.com/devbhx)

---

Projeto em desenvolvimento contínuo.
