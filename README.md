# Esports Hub - API (Backend)

<div align="center">


[![Licença](https://img.shields.io/github/license/FilipeLacerda738/esports-pro-api?style=flat-square\&logo=gnu\&color=2B3137\&labelColor=161B22)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square\&logo=python\&logoColor=white\&labelColor=161B22)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square\&logo=fastapi\&logoColor=white\&labelColor=161B22)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1.svg?style=flat-square\&logo=postgresql\&logoColor=white\&labelColor=161B22)](https://www.postgresql.org/)

</div>

---

> 📱 **O Frontend também é Open Source!**
> Esta API foi construída sob medida para o aplicativo Android do Esports Hub. Para ver o consumo de dados na prática usando Kotlin e Jetpack Compose, confira o [Repositório do Aplicativo Android](https://github.com/FilipeLacerda738/EsportsNewsAppAndroid.git).

---

# Tabela de Conteúdos

* [Visão Geral](#visão-geral)
* [Stack Tecnológico](#stack-tecnológico)
* [Características Principais](#características-principais)
* [Instalação e Uso Local](#instalação-e-uso-local)
* [Variáveis de Ambiente (.env)](#variáveis-de-ambiente-env)
* [Deploy (Render)](#deploy-render)
* [Contribuições](#contribuições)
* [Licença](#licença)

---

# Visão Geral

A **Esports Hub API** é um serviço RESTful focado em performance, construído inteiramente de forma assíncrona. Ela atua como um intermediário inteligente entre a API oficial da **PandaScore** e os dispositivos móveis dos usuários.

Em vez de sobrecarregar a API original com milhares de requisições por minuto, este backend utiliza workers em segundo plano para buscar atualizações periodicamente, salvando os dados em um banco PostgreSQL e servindo os clientes instantaneamente sem gargalos de rate limit.

---

# Stack Tecnológico

<div align="center">

|                                            Framework & Linguagem                                           |                                        Banco de Dados & ORM                                        |                                             DevOps & Tarefas                                            |
| :--------------------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------: |
|   ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)  | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge\&logo=postgresql) | ![Render](https://img.shields.io/badge/Render-000000?style=for-the-badge\&logo=render\&logoColor=white) |
| ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white) |       ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Async-D71F00?style=for-the-badge)      |             ![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-499848?style=for-the-badge)            |
|                ![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge)               |         ![asyncpg](https://img.shields.io/badge/asyncpg-Driver-336791?style=for-the-badge)         |       ![APScheduler](https://img.shields.io/badge/APScheduler-Workers-F5A623?style=for-the-badge)       |

</div>

---

# Características Principais

* ⚡ **Alta Performance:** construída do zero usando `async`/`await`, permitindo dezenas de milhares de requisições simultâneas.
* 🤖 **Workers Autônomos:** integração com `APScheduler` para executar rotinas de polling que atualizam os jogos no banco de dados minuto a minuto.
* 🔒 **Segurança Blindada:** rotas protegidas por uma chave personalizada (`API_ACCESS_KEY`) exigida via cabeçalho e validação restrita de dados via Pydantic.
* 🗄️ **Banco Assíncrono:** uso do driver `asyncpg` integrado ao SQLAlchemy 2.0 para leituras e gravações não bloqueantes.

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
