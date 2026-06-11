# ⚙️ Esports Hub - API (Backend Service)

<div align="center">

### Arquitetura de alta performance e resiliência para o ecossistema Esports Hub.

[![Licença](https://img.shields.io/github/license/FilipeLacerda738/esports-pro-api?style=flat-square&logo=gnu)](https://www.gnu.org/licenses/gpl-3.0.html)
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

# Banco de Dados
POSTGRES_USER="seu_usuario"
POSTGRES_PASSWORD="sua_senha"
POSTGRES_DB="esports_db"

# Obrigatório usar o prefixo +asyncpg para o SQLAlchemy
DATABASE_URL="postgresql+asyncpg://usuario:senha@localhost:5432/esports_db"

# PandaScore
PANDASCORE_API_KEY="sua_chave_da_pandascore"
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

# Contribuições

Sinta-se à vontade para fazer um fork do projeto e propor melhorias.

O ecossistema de eSports cresce rapidamente e sempre existe espaço para novas ideias.

---

# Roadmap

* [ ] Implementação de WebSockets para atualizações em tempo real
* [ ] Cache de API utilizando Redis
* [ ] Desacoplamento dos workers com Celery
* [ ] Sistema de autenticação JWT
* [ ] Monitoramento e métricas com Prometheus + Grafana

---

# Licença

Distribuído sob a licença MIT.

Veja o arquivo `LICENSE` para mais informações.
