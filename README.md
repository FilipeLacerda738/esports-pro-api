# ⚙️ Esports Hub - API (Backend Service)

<div align="center">
  
🇧🇷 Português | 🇺🇸 [English Version](./README.en.md)
  
### Arquitetura de alta performance e resiliência para o ecossistema Esports Hub.

[![Licença](https://img.shields.io/github/license/FilipeLacerda738/esports-pro-api?style=flat-square&logo=gnu&color=2B3137&labelColor=161B22)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white&labelColor=161B22)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square&logo=fastapi&logoColor=white&labelColor=161B22)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1.svg?style=flat-square&logo=postgresql&logoColor=white&labelColor=161B22)](https://www.postgresql.org/)

</div>

---

> 📱 **O Cliente Android também é Open Source!**
> Esta API foi desenhada exclusivamente para alimentar o nosso aplicativo mobile. Para ver a serialização de dados e a UI consumindo esta API na prática, confira o [Repositório do Aplicativo Android](https://github.com/FilipeLacerda738/EsportsNewsAppAndroid.git).

---

## 🎯 Arquitetura e Resolução de Problemas

A **Esports Hub API** não é um simples CRUD. Ela atua como um *Middleware* inteligente entre a API da **PandaScore** e os dispositivos dos usuários finais. 

O grande desafio de APIs gratuitas de esportes é o limite agressivo de requisições (*Rate Limiting*). Para resolver isso e garantir `Uptime`, esta API foi construída com foco em **Autonomia e Resiliência**.

### 🔥 Soluções de Engenharia Implementadas:

* 🔄 **Sistema de Fallback e Rotação de Chaves:** Implementação de um tratador de exceções que identifica erros `HTTP 429 (Too Many Requests)` e realiza a rotação automática (*fallback*) entre um *pool* de chaves da API, garantindo que o serviço nunca caia.
* 🤖 **Workers Autônomos (Background Polling):** Em vez de repassar a requisição do usuário para a PandaScore, o servidor usa o `APScheduler` para puxar os dados de forma assíncrona, atualizando um banco de dados PostgreSQL. O usuário consulta nosso banco, não a API externa.
* 🛡️ **Parsing Estrito de Ambiente:** Uso avançado de `Pydantic BaseSettings` para validar variáveis de ambiente no *startup*, garantindo que o servidor não suba se faltarem credenciais cruciais ou chaves de segurança.
* ⚡ **I/O Totalmente Não-Bloqueante:** Toda a cadeia, do roteamento (`FastAPI`) ao acesso ao banco de dados (`SQLAlchemy 2.0` + `asyncpg`) e requisições externas (`httpx`), é 100% assíncrona.

---

## 🛠 Stack Tecnológico

<div align="center">

| Framework & Validação | Banco de Dados & ORM | DevOps & Tarefas |
| :---: | :---: | :---: |
| **FastAPI** (Roteamento Async) | **PostgreSQL** | **Render** (Cloud Deploy) |
| **Pydantic** (Serialização/Schemas) | **SQLAlchemy 2.0** (ORM Async) | **Uvicorn** (ASGI Server) |
| **HTTPX** (Web Client) | **asyncpg** (Driver DB) | **APScheduler** (Workers) |

</div>

---


# Instalação e Uso Local

## Pré-requisitos

* Python 3.10 ou superior
* Um banco PostgreSQL rodando localmente ou em nuvem (Neon, Supabase, etc.)
* Uma chave de API gratuita da [PandaScore](https://pandascore.co/)

---

## Passo a Passo

### 1. Clone o repositório

```bash
git clone https://github.com/FilipeLacerda738/esports-pro-api.git
cd esports-pro-api
```

---

### 2. Crie e ative o ambiente virtual

#### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

---

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

### 4. Inicie o servidor local

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

A documentação interativa (Swagger UI) estará disponível em:

```txt
http://localhost:8000/docs
```

---

# Variáveis de Ambiente (.env)

Crie um arquivo `.env` na raiz do projeto contendo as seguintes variáveis.

> ⚠️ Nunca envie esse arquivo para o GitHub.

```ini
# Configurações do Projeto
PROJECT_NAME="Esports API"

# Chave de Proteção
# O app Android deve enviar esta mesma chave no header
API_ACCESS_KEY="sua_chave_aleatoria_aqui"

# Obrigatório usar o prefixo +asyncpg para o SQLAlchemy
DATABASE_URL="postgresql+asyncpg://usuario:senha@localhost:5432/esports_db"

# PandaScore
PANDASCORE_API_KEY="sua_chave_da_pandascore"
PANDASCORE_KEYS="sua_chave_da_pandascore1,sua_chave_da_pandascore2,sua_chave_da_pandascore3"

# ambiente de desenvolvimento
ENVIRONMENT=ambiente

# segurança
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "*"]
```

---

# Deploy (Render)

Este projeto está pronto para deploy no [Render](https://render.com/).

## Passos

### 1. Crie um novo Web Service

Conecte sua conta GitHub ao Render e selecione este repositório.

---

### 2. Configure o Start Command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

### 3. Configure as variáveis de ambiente

Adicione todas as variáveis do `.env` na aba:

```txt
Environment
```

---

### 4. Configuração SSL para bancos remotos

Caso utilize Neon, Supabase ou outro banco remoto, adicione:

```txt
?sslmode=require
```

ao final da `DATABASE_URL`.

Exemplo:

```txt
postgresql+asyncpg://usuario:senha@host/db?sslmode=require
```

---

# Segurança e operação

A chave `API_ACCESS_KEY` existente continua autorizando consultas de times,
partidas e detalhes, com os mesmos formatos de resposta utilizados pelo Android.
As operações `POST /api/v1/teams/` e `POST /api/v1/matches/sync-now` exigem uma
`ADMIN_API_KEY` exclusiva do servidor, enviada no header `X-API-Key`. Essa chave
é opcional: quando ausente ou igual à chave do aplicativo, as escritas retornam
403. Os jobs automáticos continuam funcionando sem ela. Nunca inclua a chave
administrativa no Android.

As consultas têm limite de 1200 requisições por minuto por IP; escritas têm
limite de 20 por minuto por IP. Há também um limite de 12000 requisições por
minuto para a instância. Excesso retorna 429 com `Retry-After: 60`. Clientes
que compartilham um IP compartilham os limites. OPTIONS e health checks são
isentos. A versão do app é cacheada por 60 segundos e o health check bem-sucedido
por 5 segundos. Limites e caches são locais, adequados ao deploy com um worker
e uma instância, sem depender de Redis.

Conexões remotas sem política SSL explícita exigem TLS. O parâmetro `sslmode`
é traduzido para o argumento `ssl` do asyncpg: `require` exige criptografia,
enquanto `verify-full` também verifica certificado e hostname. Políticas
explícitas são preservadas. Isso segue a [orientação de conexão do Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

O sistema de contas, login, cadastro, JWT e hashing de senhas foi removido.
As migrações históricas foram preservadas e as revisões ausentes foram
recuperadas; a revisão `8a6fe6b3f299` deixou de apagar usuários. A tabela legada
`users` é ignorada no autogenerate para evitar sua exclusão. Nenhuma migração
é executada automaticamente durante a inicialização da API.

O backend usa o papel `esports_backend`, sem privilégios administrativos,
propriedade de tabelas ou permissão para ignorar RLS. Ele pode consultar,
inserir e atualizar as cinco tabelas do aplicativo e excluir partidas para
executar as rotinas existentes. Não pode alterar o schema, truncar tabelas,
acessar `alembic_version` ou excluir times, ligas, jogadores e mapas diretamente.
As migrações usam uma conexão administrativa separada em
`MIGRATION_DATABASE_URL`; não configure essa credencial no serviço do Render.

O script `security/harden_database.sql` bloqueia o acesso de `anon`,
`authenticated` e `PUBLIC` ao schema `public`, remove seus privilégios de
tabelas, sequências e funções, corrige os privilégios padrão de `postgres`
e habilita RLS nas seis tabelas do projeto. Somente o papel do backend tem
políticas de acesso nas tabelas do aplicativo. Os privilégios padrão internos
de `supabase_admin` são gerenciados pelo Supabase; o bloqueio do schema impede
que esses privilégios exponham novas tabelas aos papéis públicos.

O provisionamento de produção é manual e exige o projeto explicitamente:

```powershell
.venv\Scripts\python.exe security/provision_backend.py --project-ref SEU_PROJECT_REF
```

Esse comando exige a conexão administrativa do projeto revisado, cria uma
credencial exclusiva para o banco sem modificar as chaves do app ou PandaScore,
salva a nova conexão no arquivo ignorado `.env.backend` e registra as permissões
anteriores em `logs/database-security-before.json`. Aplica as alterações numa
transação com limites de espera por locks e verifica a conexão restrita somente
com leituras. Não é executado durante o startup ou deploy. Revise schema e
políticas existentes antes de executá-lo; o comando interrompe a operação se
encontrar uma configuração diferente da revisada.

## Testes locais

Use um PostgreSQL descartável em `127.0.0.1:55439`, banco
`esports_security_test`, usuário `postgres` e senha de teste
`local-security-test-only`. Para executar a suíte, esse servidor local deve
estar com SSL desabilitado: um teste verifica que `sslmode=require` rejeita
servidores sem TLS. Os testes sobrescrevem as variáveis de ambiente antes de
importar a aplicação e limpam exclusivamente esse banco local.

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

A suíte cobre as consultas do Android, permissões de escrita, limites, caches,
sincronização, inicialização dos jobs e preservação de dados nas migrações.
As consultas e escritas da aplicação usam o papel restrito também nos testes;
somente a preparação do banco descartável e as migrações usam `postgres`.
As chamadas externas são simuladas na suíte; testes adicionais do backend
rodando podem usar a chave autorizada da PandaScore e um PostgreSQL local com
TLS habilitado. Nunca aponte os testes ou scripts de reset para o banco online.

Depois da suíte, habilite TLS no mesmo PostgreSQL local e execute:

```powershell
.venv\Scripts\python.exe tests/run_local_backend.py
```

Esse teste inicia Uvicorn em `127.0.0.1:58081`, usa a chave atual do app e
somente a terceira chave PandaScore do `.env` (ou a primeira, se não houver
três). A conexão do banco é sempre substituída pelo endereço local. Ele
valida consultas HTTP, bloqueio de escritas, 50 leituras simultâneas, limites,
health checks e um ciclo agendado do job ao vivo. O processo local é encerrado
ao final; os logs ficam em `logs/`, fora do Git.

---

# Contribuições

Sinta-se à vontade para fazer um fork do projeto e propor melhorias.

O ecossistema de eSports cresce rapidamente e sempre existe espaço para novas ideias.

---

# Licença

Distribuído sob a licença GNU General Public License v3.0.

Veja o arquivo `LICENSE` para mais informações.
