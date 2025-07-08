# API Reference - The Wall Construction Management

This document provides comprehensive API reference for The Wall construction management system.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, no authentication is required for the API endpoints.

## Task-Specific Endpoints

These endpoints implement the exact requirements from The Wall construction management task.

### Daily Ice Usage

Get the amount of ice used on a specific day for a wall profile.

**Endpoint:** `GET /profiles/{profile_id}/days/{day}/`

**Parameters:**
- `profile_id` (UUID): The unique identifier of the wall profile
- `day` (integer): The day number (starting from 1)

**Response:**
```json
{
  "day": 1,
  "ice_amount": "585.00",
  "active_sections": 3
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/profiles/e4ade876-04cf-40da-bcc3-30a587faca72/days/1/
```

### Profile Cost Overview

Get cost overview for a specific profile up to a given day.

**Endpoint:** `GET /profiles/{profile_id}/overview/{day}/`

**Parameters:**
- `profile_id` (UUID): The unique identifier of the wall profile
- `day` (integer): The day number to calculate costs up to

**Response:**
```json
{
  "day": 1,
  "cost": "1111500.00",
  "cumulative_cost": "1111500.00"
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/profiles/e4ade876-04cf-40da-bcc3-30a587faca72/overview/1/
```

### All Profiles Overview (Specific Day)

Get overview of all profiles for a specific day.

**Endpoint:** `GET /profiles/overview/{day}/`

**Parameters:**
- `day` (integer): The day number

**Response:**
```json
{
  "day": 1,
  "total_cost": "3334500.00",
  "profiles": [
    {
      "id": "da60ca07-1916-45bb-b34a-b73142552c86",
      "name": "Profile 3",
      "day": 1,
      "cost": 1852500.0,
      "sections_count": 5,
      "active_sections": 5
    },
    {
      "id": "cd0720f4-f5bd-41d6-b422-da52d21472e4",
      "name": "Profile 2",
      "day": 1,
      "cost": 370500.0,
      "sections_count": 1,
      "active_sections": 1
    },
    {
      "id": "e4ade876-04cf-40da-bcc3-30a587faca72",
      "name": "Profile 1",
      "day": 1,
      "cost": 1111500.0,
      "sections_count": 3,
      "active_sections": 3
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/profiles/overview/1/
```

### All Profiles Overview (Final Cost)

Get the final total cost when all construction is complete.

**Endpoint:** `GET /profiles/overview/`

**Response:**
```json
{
  "day": null,
  "total_cost": "32233500.00",
  "profiles": [
    {
      "id": "da60ca07-1916-45bb-b34a-b73142552c86",
      "name": "Profile 3",
      "day": 13,
      "cost": 21489000.0,
      "sections_count": 5,
      "active_sections": 5
    },
    {
      "id": "cd0720f4-f5bd-41d6-b422-da52d21472e4",
      "name": "Profile 2",
      "day": 13,
      "cost": 4816500.0,
      "sections_count": 1,
      "active_sections": 1
    },
    {
      "id": "e4ade876-04cf-40da-bcc3-30a587faca72",
      "name": "Profile 1",
      "day": 9,
      "cost": 5928000.0,
      "sections_count": 3,
      "active_sections": 3
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/profiles/overview/
```

## Configuration Management

### Load Wall Profiles from Config

Load multiple wall profiles from configuration data.

**Endpoint:** `POST /load-config/`

**Request Body:**
```json
{
  "config": [
    "21 25 28",
    "17",
    "17 22 17 19 17"
  ]
}
```

**Response:**
```json
{
  "message": "Created 3 profiles",
  "profiles": [
    {
      "id": "e4ade876-04cf-40da-bcc3-30a587faca72",
      "name": "Profile 1",
      "sections_count": 3
    },
    {
      "id": "cd0720f4-f5bd-41d6-b422-da52d21472e4",
      "name": "Profile 2",
      "sections_count": 1
    },
    {
      "id": "da60ca07-1916-45bb-b34a-b73142552c86",
      "name": "Profile 3",
      "sections_count": 5
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/load-config/ \
  -H "Content-Type: application/json" \
  -d '{
    "config": [
      "21 25 28",
      "17",
      "17 22 17 19 17"
    ]
  }'
```

## Profile Management

### List Task Profiles

Get all task wall profiles.

**Endpoint:** `GET /task-profiles/`

**Response:**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "e4ade876-04cf-40da-bcc3-30a587faca72",
      "name": "Profile 1",
      "sections": [
        {
          "id": "b1893e9c-bd9d-44c3-9740-b53c84c02dea",
          "section_index": 0,
          "initial_height": "21.00",
          "current_height": "21.00",
          "is_completed": false,
          "feet_remaining": 9.0,
          "completed_at": null
        }
      ],
      "active_sections_count": 3,
      "current_day": 0,
      "is_completed": false,
      "created_at": "2025-07-09T16:37:21.849143Z",
      "updated_at": "2025-07-09T16:37:21.849178Z"
    }
  ]
}
```

## Utility Endpoints

### Health Check

Check the health status of the API service.

**Endpoint:** `GET /health/`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1752078968.6095397,
  "service": "api-gateway"
}
```

## Error Responses

### Profile Not Found

**Status Code:** `404 Not Found`

**Response:**
```json
{
  "error": "Profile not found"
}
```

### Bad Request

**Status Code:** `400 Bad Request`

**Response:**
```json
{
  "error": "Config data is required"
}
```

### Internal Server Error

**Status Code:** `500 Internal Server Error`

**Response:**
```json
{
  "error": "Failed to calculate ice usage"
}
```

## Calculation Logic

### Constants
- **Target Height**: 30 feet
- **Ice per Foot**: 195 cubic yards
- **Cost per Cubic Yard**: 1,900 Gold Dragons

### Daily Progression
1. Each active section (not yet 30 feet) gets +1 foot per day
2. When a section reaches 30 feet, it's completed and crew is relieved
3. Ice usage = active_sections × 195 cubic yards
4. Daily cost = ice_usage × 1,900 Gold Dragons

### Example Calculation

For profile [21, 25, 28] on Day 1:
- Section 1: 21 → 22 feet (9 more needed)
- Section 2: 25 → 26 feet (5 more needed)
- Section 3: 28 → 29 feet (2 more needed)
- Active sections: 3
- Ice usage: 3 × 195 = 585 cubic yards
- Cost: 585 × 1,900 = 1,111,500 Gold Dragons
