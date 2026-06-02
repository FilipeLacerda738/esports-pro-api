# Esports Hub - API (Backend)

<div align="center">

### The asynchronous engine powering real-time CS2 and VALORANT live scores.

[![License](https://img.shields.io/github/license/FilipeLacerda738/esports-pro-api?style=flat-square\&logo=gnu\&color=2B3137\&labelColor=161B22)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square\&logo=python\&logoColor=white\&labelColor=161B22)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?style=flat-square\&logo=fastapi\&logoColor=white\&labelColor=161B22)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1.svg?style=flat-square\&logo=postgresql\&logoColor=white\&labelColor=161B22)](https://www.postgresql.org/)

</div>

---

> 📱 **The Frontend is Open Source too!**
> This API was specifically designed for the Esports Hub Android application. To see how the data is consumed in practice using Kotlin and Jetpack Compose, check out the [Android App Repository](your-frontend-repository-link-here).

---

# Table of Contents

* [Overview](#overview)
* [Tech Stack](#tech-stack)
* [Key Features](#key-features)
* [Local Installation & Usage](#local-installation--usage)
* [Environment Variables (.env)](#environment-variables-env)
* [Deployment (Render)](#deployment-render)
* [Contributing](#contributing)
* [License](#license)

---

# Overview

The **Esports Hub API** is a high-performance RESTful service built entirely with asynchronous architecture. It acts as an intelligent intermediary between the official **PandaScore API** and end-user mobile devices.

Instead of overwhelming the original API with thousands of requests per minute, this backend uses background workers to periodically fetch updates, store the data inside PostgreSQL, and instantly serve clients without rate-limit bottlenecks.

---

# Tech Stack

<div align="center">

|                                            Framework & Language                                            |                                           Database & ORM                                           |                                              DevOps & Tasks                                             |
| :--------------------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------: |
|   ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)  | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge\&logo=postgresql) | ![Render](https://img.shields.io/badge/Render-000000?style=for-the-badge\&logo=render\&logoColor=white) |
| ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white) |       ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-Async-D71F00?style=for-the-badge)      |             ![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-499848?style=for-the-badge)            |
|                ![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge)               |         ![asyncpg](https://img.shields.io/badge/asyncpg-Driver-336791?style=for-the-badge)         |       ![APScheduler](https://img.shields.io/badge/APScheduler-Workers-F5A623?style=for-the-badge)       |

</div>

---

# Key Features

* ⚡ **High Performance:** built from the ground up using `async`/`await`, allowing tens of thousands of simultaneous requests.
* 🤖 **Autonomous Workers:** integrated with `APScheduler` to run polling routines that continuously update match data in the database.
* 🔒 **Hardened Security:** routes protected with a custom `X-API-Key` header and strict data validation through Pydantic.
* 🗄️ **Asynchronous Database Layer:** powered by `asyncpg` and SQLAlchemy 2.0 for fully non-blocking reads and writes.

---

# Local Installation & Usage

## Requirements

* Python 3.10 or newer
* A running PostgreSQL database (local or cloud-hosted such as Neon or Supabase)
* A free API key from [PandaScore](https://pandascore.co/)

---

## Step-by-Step Setup

### 1. Clone the repository

```bash id="f8o2x1"
git clone https://github.com/FilipeLacerda738/esports-pro-api.git
cd esports-pro-api
```

---

### 2. Create and activate a virtual environment

#### Linux / macOS

```bash id="d7a3ke"
python -m venv .venv
source .venv/bin/activate
```

#### Windows

```bash id="q3m1ps"
python -m venv .venv
.venv\Scripts\activate
```

---

### 3. Install dependencies

```bash id="e9lmv2"
pip install -r requirements.txt
```

---

### 4. Start the local development server

```bash id="cw8qhz"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

Interactive API documentation (Swagger UI) will be available at:

```txt id="m0j4kd"
http://localhost:8000/docs
```

---

# Environment Variables (.env)

Create a `.env` file in the project root containing the following variables.

> ⚠️ Never upload this file to GitHub.

```ini id="pk7z4w"
# Project Settings
PROJECT_NAME="Esports API"

# API Protection Key
# The Android app must send this same key in the request header
API_ACCESS_KEY="your_secret_key_here"

# Database
POSTGRES_USER="your_username"
POSTGRES_PASSWORD="your_password"
POSTGRES_DB="esports_db"

# SQLAlchemy requires the +asyncpg driver prefix
DATABASE_URL="postgresql+asyncpg://username:password@localhost:5432/esports_db"

# PandaScore
PANDASCORE_API_KEY="your_pandascore_api_key"
```

---

# Deployment (Render)

This project is fully ready for deployment on [Render](https://render.com/).

## Deployment Steps

### 1. Create a new Web Service

Connect your GitHub account and select this repository.

---

### 2. Configure the Start Command

```bash id="z6rf1v"
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

### 3. Add Environment Variables

Add all variables from your `.env` file into the:

```txt id="yu7r1e"
Environment
```

section inside Render.

---

### 4. SSL Configuration for Remote Databases

If you are using Neon, Supabase, or any remote PostgreSQL provider, append:

```txt id="af7t5o"
?sslmode=require
```

to the end of your `DATABASE_URL`.

Example:

```txt id="vb9x2c"
postgresql+asyncpg://username:password@host/database?sslmode=require
```

---

# Contributing

Feel free to fork the project and propose improvements.

The esports ecosystem evolves rapidly, and there is always room for innovation.

---

# Roadmap

* [ ] WebSocket implementation for true real-time updates
* [ ] Redis API caching layer
* [ ] Worker decoupling using Celery
* [ ] JWT authentication system
* [ ] Monitoring and metrics with Prometheus + Grafana

---

# License

Distributed under the MIT License.

See `LICENSE` for more information.
