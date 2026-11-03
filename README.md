# AppBuilder – APIs Governamentais

Serviço REST (FastAPI) que serve de fachada para:

- **PNCP**: API de Consultas do Portal Nacional de Contratações Públicas ([swagger](https://pncp.gov.br/api/consulta/swagger-ui/index.html)). É pública e não exige chave.
- **Portal da Transparência (CGU)**: [API de Dados](https://portaldatransparencia.gov.br/api-de-dados). Exige uma chave gratuita ([cadastro](https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email)).

O serviço padroniza datas (sempre ISO `YYYY-MM-DD` na entrada), paginação e erros, e repete a requisição com backoff em 429/5xx.

## Rodando

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env   # preencha PORTAL_TRANSPARENCIA_API_KEY
.venv/bin/uvicorn app.main:app --reload
```

A documentação interativa fica em http://localhost:8000/docs.

## Rotas

### PNCP

| Rota | Fonte | Observações |
|---|---|---|
| `GET /pncp/modalidades` | — | Tabela de códigos de modalidade |
| `GET /pncp/contratacoes` | `/v1/contratacoes/publicacao` | `data_inicial`, `data_final` e `modalidade` são obrigatórios |
| `GET /pncp/contratacoes/abertas` | `/v1/contratacoes/proposta` | Propostas abertas até `data_final` |
| `GET /pncp/contratacoes/{cnpj}/{ano}/{seq}` | `/v1/orgaos/{cnpj}/compras/{ano}/{seq}` | Detalhe de uma contratação |
| `GET /pncp/contratos` | `/v1/contratos` | Contratos e empenhos do período |
| `GET /pncp/atas` | `/v1/atas` | Atas de registro de preço |

Filtros comuns: `uf`, `codigo_municipio_ibge`, `cnpj_orgao`, `codigo_unidade`, `pagina`, `tamanho_pagina` (de 10 a 50).

### Portal da Transparência

| Rota | Fonte | Observações |
|---|---|---|
| `GET /transparencia/contratos` | `/contratos` | `codigo_orgao` (SIAFI) é obrigatório |
| `GET /transparencia/contratos/fornecedor/{cpf_cnpj}` | `/contratos/cpf-cnpj` | |
| `GET /transparencia/licitacoes` | `/licitacoes` | Período de no máximo 1 mês |
| `GET /transparencia/sancoes/ceis` | `/ceis` | Busca por `cpf_cnpj` ou `nome` |
| `GET /transparencia/sancoes/cnep` | `/cnep` | Busca por `cpf_cnpj` ou `nome` |
| `GET /transparencia/sancoes/{cpf_cnpj}` | `/ceis` + `/cnep` | Retorna `sancionado: true/false` |

### Formato das respostas

```json
{ "fonte": "pncp", "pagina": 1, "total_registros": 1234, "total_paginas": 25, "dados": [ ... ] }
```

O Portal da Transparência não informa totais. Nesse caso a resposta traz `quantidade` (até 15 registros por página), e quando uma página volta vazia é porque os resultados acabaram.

Erros das fontes viram **502** (a fonte respondeu com erro) ou **504** (falha de rede ou timeout), com `fonte` e `status_fonte` no corpo. Se a chave da Transparência não estiver configurada, as rotas `/transparencia/*` retornam **503**.

## Testes

```bash
.venv/bin/python -m pytest
```

Os testes simulam as APIs externas com `respx` e conferem o que enviamos (parâmetros, formato de data, header `chave-api-dados`) e como tratamos respostas, 204, retries e erros.

## Pendente de validação contra as APIs reais

Este código foi escrito sem acesso de rede aos domínios `.gov.br`. Antes de usar em produção, confira no swagger:

- O nome do parâmetro de CPF/CNPJ no CEIS e no CNEP. O código usa `codigoSancionado`; versões antigas da API usavam `cnpjSancionado`.
- O limite de `tamanhoPagina` em `/v1/contratos` e `/v1/atas` do PNCP. Aqui o limite está fixado em 50 para todas as rotas.
