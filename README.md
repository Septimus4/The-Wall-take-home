# The Wall - Construction Management System
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Septimus4/The-Wall-take-home)

> *"The White Walkers sleep beneath the ice for thousands of years. And when they wake up... I hope the Wall is high enough."*

A Django REST API system for managing the construction of the 30-foot ice wall defending the Seven Kingdoms. Track material quantities, costs, and crew management with real-time calculations.

🏰 **[Task Requirements](#-task-requirements)** | 🚀 **[Quick Start](#-quick-start)** | 🧪 **[Testing](#-testing)**

## 🏗️ The Story

The Wall is a colossal fortification stretching for 100 leagues (300 miles) along the northern border. Standing 30 feet tall and made of solid ice, it defends against the wildlings beyond. Each mile-long section has its own construction crew working simultaneously to reach the target height.

### Construction Rules

* **Target Height**: 30 feet for all sections
* **Materials**: 195 cubic yards of ice per foot of height
* **Cost**: 1,900 Gold Dragons per cubic yard
* **Daily Progress**: Each crew adds 1 foot per day
* **Crew Management**: Crews are relieved at 30 feet

## 🎯 Task Requirements

This system implements the exact requirements from *The Wall* construction management task:

### Required API Endpoints

* `GET /profiles/{id}/days/{day}/`
* `GET /profiles/{id}/overview/{day}/`
* `GET /profiles/overview/{day}/`
* `GET /profiles/overview/`

### Example Data & Expected Results

```
Input profiles:
21 25 28
17
17 22 17 19 17

Day 1 Results:
Profile 1: 3 crews × 195 = 585 cubic yards
Profile 2: 1 crew × 195 = 195 cubic yards
Profile 3: 5 crews × 195 = 975 cubic yards
Total: 1,755 cubic yards × 1,900 = 3,334,500 Gold Dragons
```

## ⚙️ Architecture

* **Django 5** + **Django REST Framework**
* **PostgreSQL** for data storage
* **Docker** for orchestration
* **Prometheus + Grafana** for observability
* **Calculation engine** in `shared/wall_common/`

## 🚀 Quick Start

### Prerequisites

* Docker & Docker Compose

### 1. Start the System

```bash
docker compose up -d kafka zookeeper postgres prometheus grafana

docker compose up -d api

docker compose ps
```

### 2. Load Wall Profiles

```bash
curl -X POST http://localhost:8000/api/v1/load-config/ \
  -H "Content-Type: application/json" \
  -d '{"config": ["21 25 28", "17", "17 22 17 19 17"]}'
```

### 3. Verify Implementation

```bash
./test_task_final.sh
```

## 📊 API Reference

### Daily Ice Usage

```http
GET /api/v1/profiles/{profile_id}/days/{day}/
```

Returns: `{"day": 1, "ice_amount": "585.00", "active_sections": 3}`

### Profile Cost Overview

```http
GET /api/v1/profiles/{profile_id}/overview/{day}/
```

### All Profiles Overview

```http
GET /api/v1/profiles/overview/{day}/
```

### Final Total Cost

```http
GET /api/v1/profiles/overview/
```

## 🧪 Testing

### Automated Test Suite

```bash
./test_task_final.sh
```

Validates:

* All endpoints respond correctly
* Crew management & calculations are accurate
* All example cases from task are covered

### Manual Testing

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/api/v1/task-profiles/
```

## 🗂️ Project Structure

```
thewall/
├── apps/
│   ├── profiles/
│   ├── health/
│   └── common/
├── shared/wall_common/
├── infrastructure/
├── test_task_final.sh
├── docker-compose.yml
```

## ⚡ Performance & Monitoring

* **Grafana**: [http://localhost:3000](http://localhost:3000) (admin/admin)
* **Prometheus**: [http://localhost:9090](http://localhost:9090)
* **Health**: [http://localhost:8000/health/](http://localhost:8000/health/)

### Benchmark Results

* Avg RPS: 337.5
* Avg Response Time: 29.6ms
* Error Rate: 0.00%

### Example Performance

* `GET /profiles/1/days/1/` → 13.8ms
* `GET /profiles/overview/` → 117.3ms

## 🔧 Development

### Local

```bash
pip install poetry
poetry install
cd thewall
python manage.py migrate
python manage.py runserver
```

### Docker

```bash
docker compose up -d
docker compose logs -f api
docker compose down -v
```

## 🎯 Validation Summary

### Task Verification ✅

| Test Case          | Expected  | Actual       | Status |
| ------------------ | --------- | ------------ | ------ |
| Profile 1, Day 1   | 585       | 585.00       | ✅      |
| Profile 2, Day 1   | 195       | 195.00       | ✅      |
| Profile 3, Day 1   | 975       | 975.00       | ✅      |
| Day 1 Cost         | 3,334,500 | 3,334,500.00 | ✅      |
| Profile 2 Complete | Day 14    | Day 14       | ✅      |

### Logic & API

* ✅ Concurrent crew simulation
* ✅ Section completion + crew relief
* ✅ Accurate cost: `ice × 1,900`
* ✅ Exact match with task-provided data

##  Production Deployment

```bash
export DJANGO_SETTINGS_MODULE=thewall.settings.production
export SECRET_KEY=your-production-secret
export DB_HOST=your-postgres-host
export DB_NAME=wall_production
export DB_USER=wall_user
export DB_PASSWORD=secure-password
```

## 🤝 Contributing

1. Fork and branch
2. Code + tests
3. Run `./test_task_final.sh`
4. Open a PR

## 📜 License

GNU GPL v3.0 - see LICENSE

