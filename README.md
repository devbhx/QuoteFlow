# QuoteFlow

SaaS de criação e gerenciamento de orçamentos profissionais, desenvolvido inicialmente para prestadores de serviços e pequenos negócios.

> **Status:** Em desenvolvimento — MVP inicial em Python.

## Sobre o projeto

O QuoteFlow é uma plataforma em desenvolvimento voltada à criação e ao gerenciamento de orçamentos profissionais para prestadores de serviços e pequenos negócios.
A proposta é simplificar o processo de elaboração de orçamentos, oferecendo ferramentas para organizar serviços, calcular valores e descontos e, futuramente, gerenciar clientes e acompanhar o histórico de propostas comerciais.
O projeto está sendo desenvolvido de forma incremental, com foco em organização do código, testes automatizados e boas práticas de engenharia de software.

## Funcionalidades implementadas

- Cálculo de subtotal, desconto e valor final.
- Validação de valores, quantidades e percentuais.
- Tratamento de entradas inválidas.
- Organização do código em funções e módulos.
- Testes automatizados das funções de cálculo.

## Tecnologias utilizadas

- Python
- Biblioteca Decimal
- Pytest
- Git e GitHub

## Como executar

Com Python instalado, execute na pasta do projeto:

```bash
python3 main.py
```

## Como executar os testes

Instale o pytest em um ambiente virtual e execute:

```bash
python -m pytest test_calculos.py -v
```

## Próximas etapas

- Ampliar os testes automatizados.
- Permitir múltiplos itens em um orçamento.
- Implementar gerenciamento de clientes e serviços.
- Evoluir o programa de terminal para uma aplicação web.

## Autor

Bruno Henrique — [GitHub](https://github.com/devbhx)

---

Projeto em desenvolvimento contínuo.
