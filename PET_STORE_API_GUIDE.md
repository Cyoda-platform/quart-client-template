# Pet Store API Guide

## Quick Start

The Pet Store application provides REST API endpoints to manage pets and download their data from the Swagger Petstore API.

## API Endpoints

### Create a Pet
```bash
POST /api/pets
Content-Type: application/json

{
  "name": "Fluffy",
  "status": "available",
  "petId": 1,
  "category": {"id": 1, "name": "Dogs"},
  "photoUrls": ["https://example.com/photo1.jpg"],
  "tags": [{"id": 1, "name": "friendly"}]
}
```

Response (201 Created):
```json
{
  "id": "uuid-here",
  "name": "Fluffy",
  "status": "available",
  "petId": 1,
  "state": "initial_state",
  "downloadedAt": null,
  "processedData": null
}
```

### List All Pets
```bash
GET /api/pets
```

Response (200 OK):
```json
{
  "entities": [
    {
      "id": "uuid-1",
      "name": "Fluffy",
      "status": "available",
      "state": "initial_state"
    }
  ],
  "total": 1
}
```

### Get a Specific Pet
```bash
GET /api/pets/{entity_id}
```

### Update a Pet
```bash
PUT /api/pets/{entity_id}
Content-Type: application/json

{
  "name": "Fluffy Updated",
  "status": "pending"
}
```

### Delete a Pet
```bash
DELETE /api/pets/{entity_id}
```

### Get Available Transitions
```bash
GET /api/pets/{entity_id}/transitions
```

Response:
```json
{
  "entity_id": "uuid-here",
  "available_transitions": ["download"]
}
```

### Trigger Workflow Transition
```bash
POST /api/pets/{entity_id}/transitions?transition=download
```

Available transitions:
- `download` - Downloads pet data from Petstore API
- `process` - Processes and enriches pet data
- `complete` - Marks pet as completed

## Workflow States

1. **initial_state** - Pet created but not yet processed
2. **created** - Pet entity created, ready for download
3. **downloaded** - Pet data downloaded from API
4. **processed** - Pet data enriched with processing
5. **completed** - Pet processing complete

## Example Workflow

```bash
# 1. Create a pet
curl -X POST http://localhost:8000/api/pets \
  -H "Content-Type: application/json" \
  -d '{"name": "Buddy", "status": "available", "petId": 1}'

# Response: {"id": "pet-uuid", "state": "initial_state", ...}

# 2. Download pet data from API
curl -X POST http://localhost:8000/api/pets/pet-uuid/transitions?transition=download

# Response: {"id": "pet-uuid", "newState": "downloaded", ...}

# 3. Process pet data
curl -X POST http://localhost:8000/api/pets/pet-uuid/transitions?transition=process

# Response: {"id": "pet-uuid", "newState": "processed", ...}

# 4. Complete processing
curl -X POST http://localhost:8000/api/pets/pet-uuid/transitions?transition=complete

# Response: {"id": "pet-uuid", "newState": "completed", ...}

# 5. Get final pet data
curl http://localhost:8000/api/pets/pet-uuid

# Response includes processedData with enriched information
```

## Data Processing

When a pet transitions through the workflow:

### Download Phase
- Fetches pet data from Swagger Petstore API using the petId
- Updates pet entity with API data (name, status, category, photos, tags)
- Records download timestamp

### Process Phase
- Enriches pet data with computed fields:
  - `name_upper`: Uppercase version of pet name
  - `status`: Current pet status
  - `has_photos`: Whether pet has photos
  - `photo_count`: Number of photos
  - `has_tags`: Whether pet has tags
  - `tag_count`: Number of tags
  - `category_name`: Pet category name

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad request (validation error)
- `404` - Not found
- `500` - Server error

Error responses include:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## Notes

- Pet IDs from the Petstore API are stored in the `petId` field
- The application uses the Cyoda framework for entity management
- All timestamps are in ISO 8601 format with UTC timezone
- The workflow is fully automated - transitions happen automatically

