# 🧱 The Wall - Take-Home Project

> *"The White Walkers sleep beneath the ice for thousands of years. And when they wake up... I hope the Wall is high enough."*

A domain-driven, event-sourced construction simulation system built with Django, FastAPI, and Kafka. This project tracks the construction of a 30-foot ice wall by managing wall profile definitions, simulating builds asynchronously, and capturing logs and metrics for analysis.

---

## 📌 Overview

This system simulates a real-time, collaborative wall-building scenario. Inspired by the world of Westeros, each mile-long segment of the Wall is managed by its own construction team, with material quantities and costs tracked independently. The architecture is designed for scalability, modularity, and observability.

---

## 📚 Documentation

For an in-depth explanation of the architecture, components, and design decisions, see the full project documentation hosted on DeepWiki:

👉 [Project Documentation on DeepWiki](https://deepwiki.com/Septimus4/The-Wall-take-home/1-overview)

---

## ⚙️ Tech Stack

* **API Gateway**: Django + DRF
* **Simulation Service**: FastAPI
* **Messaging**: Kafka (Avro + Schema Registry)
* **Database**: PostgreSQL
* **Observability**: Prometheus + Grafana
* **Testing**: Pytest
* **Event Processing**: Custom Kafka Event Publisher & Listener

---

## 🧩 Features

* **Modular Architecture**: Domain logic isolated from Django and FastAPI apps
* **Asynchronous Simulation**: Triggered by Kafka events, decoupled from HTTP APIs
* **Threaded Execution**: Multi-threaded wall section building for team-based scenarios
* **Event Sourcing**: Log-driven state reconstruction and auditability
* **Metrics and Logs**: Track simulation performance (RPS, response time)
* **Reusable Domain Layer**: Pure Python layer reused across services for business logic

---

## 🏗️ Kafka Simulation Events

* Used for **decoupled orchestration** and event logging
* Enables **asynchronous simulation triggering**
* Drives **team-based, multi-threaded simulation mode**
* Allows **parallel testability** via thread pools

---

## 🚀 Getting Started

### 1. Clone & Setup

```bash
git clone https://github.com/yourname/The-Wall-take-home.git
cd The-Wall-take-home
poetry install
```

### 2. Start Services

```bash
docker-compose up -d wall-zookeeper wall-kafka wall-postgres wall-prometheus wall-grafana
```

### 3. Run Migrations & Server

```bash
# API Gateway (Django)
poetry run python manage.py migrate
poetry run python manage.py runserver
```

---

## 🔬 Running Simulations

Create a wall profile via the API (e.g., `/api/profiles/`).
This triggers a Kafka event which starts the asynchronous simulation in the simulation service.

You can monitor simulations via:

* Logs
* Kafka topics (e.g., `wall.simulation.events`)
* Prometheus metrics (e.g., Avg RPS, Avg Response Time)

---

## 📊 Observability

* **Prometheus**: Tracks simulation performance, Kafka throughput
* **Grafana Dashboards**: Preconfigured for wall simulation metrics
* **Log-Driven Replay**: Replay events for debugging or rerunning simulations

---

## 🧪 Testing

```bash
make test  # runs unit tests and API tests
```

Supports:

* Isolated domain layer testing
* Kafka event mocking
* Django REST API tests

---

## 🧠 Design Highlights

* **Domain-Driven Design**: Central `WallProfile` domain reused in Django and FastAPI
* **Testability**: Domain logic can be tested without Django or Kafka dependencies
* **Threaded Builders**: Simulates multiple crews working on wall segments concurrently
* **Extensibility**: Easily add new simulation modes or materials

---

## 📁 Project Structure

```bash
.
├── thewall/                 # Django app
├── services/simulation/    # FastAPI simulation app
├── shared/wall_common/     # Pure Python domain logic
├── docker-compose.yml      # Infra services
└── tests/                  # Unit + integration tests
```
