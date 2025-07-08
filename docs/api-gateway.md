# Django REST API Reference (v1)

The Django API provides the primary HTTP interface for managing wall profiles and simulations.

## API Versioning

The Wall project uses **URL path versioning** to ensure stability and allow smooth future upgrades.

* **Current Version**: `v1`
* **Base URL**: `/api/v1/`
* **Namespace**: `profiles`
* **URL Names**: All prefixed with `v1-`

### Example Endpoints

* `GET/POST    /api/v1/profiles/` (name: `profiles:v1-profile-list-create`)
* `GET/PUT/PATCH/DELETE /api/v1/profiles/{id}/` (name: `profiles:v1-profile-detail`)
* `GET        /api/v1/profiles/{id}/simulations/` (name: `profiles:v1-simulation-list`)
* `POST       /api/v1/profiles/{id}/start-simulation/` (name: `profiles:v1-start-simulation`)
* `POST       /api/v1/profiles/{id}/stop-simulation/` (name: `profiles:v1-stop-simulation`)
* `GET        /api/v1/overview/` (name: `profiles:v1-project-overview`)

To add future versions, create new URL modules and views, and register them in `thewall/urls.py`.

---

## Base URL

* **Local Development**: `http://localhost:8000/api/v1/`
* **Production**: Configure via environment variables

## Interactive Documentation

* **Django REST Browsable API**: `http://localhost:8000/api/v1/`
* **Django Admin**: `http://localhost:8000/admin/`

---

## Core Endpoints

### Wall Profiles

#### Create Wall Profile

```http
POST /api/v1/profiles/
Content-Type: application/json

{
  "name": "Great Wall of Testing",
  "height": 5.0,
  "length": 100.0,
  "width": 3.0,
  "ice_thickness": 0.3
}
```

#### List Wall Profiles

```http
GET /api/v1/profiles/
```

#### Get Wall Profile Details

```http
GET /api/v1/profiles/{id}/
```

#### Update Wall Profile

```http
PUT /api/v1/profiles/{id}/
PATCH /api/v1/profiles/{id}/
```

#### Delete Wall Profile

```http
DELETE /api/v1/profiles/{id}/
```

---

### System Overview

#### Project Overview

```http
GET /api/v1/overview/
```

---

## Health Check

```http
GET /health/
```

---

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages.

### 400 Bad Request

```json
{
  "height": ["Height must be a positive number"]
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

---

## Data Validation

| Field           | Type    | Required | Validation                            |
| --------------- | ------- | -------- | ------------------------------------- |
| `name`          | String  | Yes      | Max 200 characters                    |
| `height`        | Decimal | Yes      | Positive number, max 2 decimal places |
| `length`        | Decimal | Yes      | Positive number, max 2 decimal places |
| `width`         | Decimal | Yes      | Positive number, max 2 decimal places |
| `ice_thickness` | Decimal | Yes      | Positive number, max 2 decimal places |

---

## Quick Examples

### cURL Examples

```bash
# Create profile
curl -X POST http://localhost:8000/api/v1/profiles/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Wall",
    "height": 25.5,
    "length": 100.0,
    "width": 3.0,
    "ice_thickness": 0.5
  }'

# List all profiles
curl http://localhost:8000/api/v1/profiles/

# Get project overview
curl http://localhost:8000/api/v1/overview/

# Health check
curl http://localhost:8000/health/
```

### Python (requests)

```python
import requests

# Create a profile
profile_data = {
    "name": "Test Wall",
    "height": 25.5,
    "length": 100.0,
    "width": 3.0,
    "ice_thickness": 0.5
}

response = requests.post(
    "http://localhost:8000/api/v1/profiles/",
    json=profile_data
)

profile = response.json()
print(f"Created profile: {profile['name']} (ID: {profile['id']})")
```

---

## Event Integration

The Django API publishes events to Kafka when profiles are created or updated.

### Events Published

* `ProfileCreated`
* `ProfileUpdated`

See [Simulator Documentation](simulator.md) for event schema details.

---

## Testing the API

### Unit Tests

```bash
make test-api
```

### Integration Tests

```bash
make test-all
```
