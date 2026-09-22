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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

---

A documentação interativa (Swagger UI) estará disponível em:

```txt
http://localhost:8000/docs
```

---

# Variáveis de Ambiente (.env)

Copie [.env.example](.env.example) para `.env` antes de iniciar o servidor e preencha suas credenciais.
Gere duas chaves diferentes com `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
`API_ACCESS_KEY` é usada pelo aplicativo para leitura; `SECRET_KEY` fica exclusivamente no servidor.
Nunca envie `.env` para o GitHub.

Para desenvolvimento local: `ENVIRONMENT=development`, `DATABASE_SSL=false` apenas com banco em localhost
e `RATE_LIMIT_STORAGE_URI=memory://`. Para Android, `BACKEND_CORS_ORIGINS=[]`.
Para navegador, informe origens exatas, sem `*`.

Em produção, são obrigatórios ambiente explícito e TLS verificado no banco. Redis compartilhado
só é necessário ao usar mais de um worker ou réplica. Leia [SECURITY.md](SECURITY.md) antes do deploy: contém as variáveis,
limites, configuração de proxy, rotação de chaves e mudanças de contrato da API.

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

### 4. TLS e limites em produção

Use `DATABASE_SSL=true`. A conexão verifica certificado e hostname; configure `DATABASE_CA_FILE`
se o provedor exigir uma CA específica. Apenas adicionar `sslmode=require` à URL não substitui
essa configuração. Alembic usa a mesma política TLS.

Com o worker único atual, `RATE_LIMIT_STORAGE_URI=memory://` preserva o deploy sem nova credencial.
Antes de escalar, configure `rediss://usuario:senha@host:porta/0`. Use CORS com origens HTTPS
exatas e um proxy HTTPS confiável. Execute um worker enquanto o agendador estiver embutido.
Veja o procedimento completo em [SECURITY.md](SECURITY.md).

---

# Contribuições

Sinta-se à vontade para fazer um fork do projeto e propor melhorias.

O ecossistema de eSports cresce rapidamente e sempre existe espaço para novas ideias.

---

# Licença

Distribuído sob a licença GNU General Public License v3.0.

Veja o arquivo `LICENSE` para mais informações.
