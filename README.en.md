# ⚙️ Esports Hub - API (Backend Service)

<div align="center">

🇺🇸 English | 🇧🇷 [Português](./README.md)

### High-performance and resilient architecture for the Esports Hub ecosystem.

[![License](https://img.shields.io/github/license/FilipeLacerda738/esports-pro-api?style=flat-square\&logo=gnu\&color=2B3137\&labelColor=161B22)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square\&logo=python\&logoColor=white\&labelColor=161B22)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square\&logo=fastapi\&logoColor=white\&labelColor=161B22)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1.svg?style=flat-square\&logo=postgresql\&logoColor=white\&labelColor=161B22)](https://www.postgresql.org/)

</div>

---

> 📱 **The Android Client is also Open Source!**
> This API was designed exclusively to power our mobile application. To see data serialization and the UI consuming this API in practice, check out the [Android App Repository](https://github.com/FilipeLacerda738/EsportsNewsAppAndroid.git).

---

## 🎯 Architecture and Problem Solving

The **Esports Hub API** is not just a simple CRUD application. It acts as an intelligent *Middleware* between the **PandaScore API** and end-user devices.

One of the biggest challenges with free sports APIs is aggressive request limits (*Rate Limiting*). To solve this problem and guarantee `Uptime`, this API was built with a strong focus on **Autonomy and Resilience**.

### 🔥 Implemented Engineering Solutions

* 🔄 **Fallback System and API Key Rotation:** Implementation of an exception handler capable of identifying `HTTP 429 (Too Many Requests)` errors and automatically rotating (*fallbacking*) between a pool of API keys, ensuring the service never goes down.
* 🤖 **Autonomous Workers (Background Polling):** Instead of forwarding user requests directly to PandaScore, the server uses `APScheduler` to asynchronously fetch data and update a PostgreSQL database. Users query our database, not the external API.
* 🛡️ **Strict Environment Parsing:** Advanced usage of `Pydantic BaseSettings` to validate environment variables during startup, ensuring the server does not boot if critical credentials or security keys are missing.
* ⚡ **Fully Non-Blocking I/O:** The entire stack — from routing (`FastAPI`) to database access (`SQLAlchemy 2.0` + `asyncpg`) and external requests (`httpx`) — is fully asynchronous.

---

## 🛠 Tech Stack

<div align="center">

|        Framework & Validation        |         Database & ORM         |       DevOps & Tasks      |
| :----------------------------------: | :----------------------------: | :-----------------------: |
|      **FastAPI** (Async Routing)     |         **PostgreSQL**         | **Render** (Cloud Deploy) |
| **Pydantic** (Serialization/Schemas) | **SQLAlchemy 2.0** (Async ORM) | **Uvicorn** (ASGI Server) |
|        **HTTPX** (Web Client)        |     **asyncpg** (DB Driver)    | **APScheduler** (Workers) |

</div>

---

# Local Installation and Usage

## Prerequisites

* Python 3.10 or higher
* A PostgreSQL database running locally or in the cloud (Neon, Supabase, etc.)
* A free API key from [PandaScore](https://pandascore.co/)

---

## Step-by-Step

### 1. Clone the repository

```bash
git clone https://github.com/FilipeLacerda738/esports-pro-api.git
cd esports-pro-api
```

---

### 2. Create and activate the virtual environment

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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Start the local server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

Interactive documentation (Swagger UI) will be available at:

```txt
http://localhost:8000/docs
```

---

# Environment Variables (.env)

Create a `.env` file in the project root containing the following variables.

> ⚠️ Never commit this file to GitHub.

```ini
# Project Settings
PROJECT_NAME="Esports API"

# Protection Key
# The Android app must send this same key in the request header
API_ACCESS_KEY="your_random_key_here"

# Database
POSTGRES_USER="your_user"
POSTGRES_PASSWORD="your_password"
POSTGRES_DB="esports_db"

# SQLAlchemy requires the +asyncpg prefix
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/esports_db"

# PandaScore
PANDASCORE_API_KEY="your_pandascore_key"
```

---

# Deployment (Render)

This project is ready for deployment on [Render](https://render.com/).

## Steps

### 1. Create a new Web Service

Connect your GitHub account to Render and select this repository.

---

### 2. Configure the Start Command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

### 3. Configure environment variables

Add all `.env` variables under the:

```txt
Environment
```

section.

---

### 4. SSL configuration for remote databases

If you are using Neon, Supabase, or another remote database provider, append:

```txt
?sslmode=require
```

to the end of the `DATABASE_URL`.

Example:

```txt
postgresql+asyncpg://user:password@host/db?sslmode=require
```

---

# Contributions

Feel free to fork the project and propose improvements.

The eSports ecosystem evolves rapidly, and there is always room for new ideas.

---

# Roadmap

* [ ] WebSocket implementation for real-time updates
* [ ] API caching using Redis
* [ ] Worker decoupling with Celery
* [ ] JWT authentication system
* [ ] Monitoring and metrics with Prometheus + Grafana

---

# License

Distributed under the MIT License.

See the `LICENSE` file for more information.
