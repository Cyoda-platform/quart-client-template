# Customer Management REST API

A complete Customer Management REST API built with the Cyoda Python framework (Quart). This API provides full CRUD operations for customer entities with comprehensive validation, pagination, filtering, and sorting capabilities.

## Features

- **Full CRUD Operations**: Create, Read, Update, Delete customers
- **Comprehensive Validation**: Email format validation, uniqueness constraints, required field validation
- **Pagination**: Support for page-based pagination with configurable page sizes
- **Filtering**: Filter customers by name and email with partial matching
- **Sorting**: Sort by name, email, or created_at with ascending/descending order
- **Workflow Management**: Built-in workflow states and transitions
- **OpenAPI Documentation**: Auto-generated Swagger/OpenAPI specification
- **Type Safety**: Full mypy type checking support
- **Error Handling**: Proper HTTP status codes and JSON error responses

## Customer Entity

The Customer entity includes the following fields:

- `id`: UUID (system-generated primary key)
- `name`: string (required, 2-100 characters)
- `email`: string (required, unique, valid email format, max 255 characters)
- `phone`: string (optional, 10-20 digits)
- `address`: object (optional)
  - `street`: string (optional)
  - `city`: string (optional)
  - `state`: string (optional)
  - `zip`: string (optional)
- `created_at`: timestamp (auto-generated)
- `updated_at`: timestamp (auto-updated)
- `state`: string (workflow state, managed automatically)

## API Endpoints

### Core CRUD Operations

#### Create Customer
```
POST /api/customers
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-123-4567",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip": "12345"
  }
}
```

**Response**: 201 Created with Location header
**Error Codes**: 400 (validation error), 409 (duplicate email), 500 (server error)

#### Get Customer by ID
```
GET /api/customers/{id}
```

**Response**: 200 OK with customer data
**Error Codes**: 404 (not found), 400 (invalid ID), 500 (server error)

#### List Customers with Pagination and Filtering
```
GET /api/customers?page=1&size=20&name=John&email=example.com&sort_by=created_at&order=desc
```

**Query Parameters**:
- `page`: Page number (default: 1)
- `size`: Page size (default: 20, max: 100)
- `name`: Filter by name (partial match)
- `email`: Filter by email (partial match)
- `sort_by`: Sort field (name, email, created_at)
- `order`: Sort order (asc, desc)

**Response**: 200 OK with paginated results

#### Update Customer (Full Replace)
```
PUT /api/customers/{id}?transition=validate
Content-Type: application/json

{
  "name": "John Smith",
  "email": "john.smith@example.com",
  "phone": "+1-555-987-6543"
}
```

**Query Parameters**:
- `transition`: Optional workflow transition to trigger

**Response**: 200 OK with updated customer
**Error Codes**: 404 (not found), 400 (validation error), 409 (duplicate email), 500 (server error)

#### Update Customer (Partial)
```
PATCH /api/customers/{id}
Content-Type: application/json

{
  "phone": "+1-555-999-8888"
}
```

**Response**: 200 OK with updated customer
**Error Codes**: 404 (not found), 400 (validation error), 409 (duplicate email), 500 (server error)

#### Delete Customer
```
DELETE /api/customers/{id}
```

**Response**: 200 OK with success message
**Error Codes**: 404 (not found), 400 (invalid ID), 500 (server error)

### Additional Endpoints

#### Search Customers
```
POST /api/customers/search
Content-Type: application/json

{
  "name": "John",
  "email": "example.com"
}
```

#### Check if Customer Exists
```
GET /api/customers/{id}/exists
```

#### Count Customers
```
GET /api/customers/count
```

#### Get Available Workflow Transitions
```
GET /api/customers/{id}/transitions
```

#### Trigger Workflow Transition
```
POST /api/customers/{id}/transitions
Content-Type: application/json

{
  "transition_name": "validate"
}
```

## Setup Instructions

### Prerequisites

- Python 3.12+
- pip package manager

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mcp-cyoda-quart-app
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set environment variables** (optional):
   ```bash
   export APP_HOST=127.0.0.1
   export APP_PORT=8000
   export APP_DEBUG=false
   export CHAT_REPOSITORY=in_memory  # Use in-memory DB for development
   ```

### Running the Application

1. **Start the server**:
   ```bash
   python -m application.app
   ```

2. **Access the API**:
   - Base URL: `http://localhost:8000`
   - OpenAPI Documentation: `http://localhost:8000/openapi.json`
   - Swagger UI: Available through the OpenAPI spec

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=application

# Run specific test file
pytest tests/test_customer_api.py
```

### Code Quality Checks

```bash
# Format code
python -m black .

# Sort imports
python -m isort .

# Type checking
python -m mypy .

# Linting
python -m flake8 .

# Security scanning
python -m bandit -r application/
```

## Example curl Commands

### Create a Customer
```bash
curl -X POST http://localhost:8000/api/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "email": "alice.johnson@example.com",
    "phone": "+1-555-123-4567",
    "address": {
      "street": "456 Oak Ave",
      "city": "Springfield",
      "state": "IL",
      "zip": "62701"
    }
  }'
```

### Get All Customers with Pagination
```bash
curl "http://localhost:8000/api/customers?page=1&size=10&sort_by=name&order=asc"
```

### Search Customers
```bash
curl -X POST http://localhost:8000/api/customers/search \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice",
    "email": "example.com"
  }'
```

### Update Customer
```bash
curl -X PUT http://localhost:8000/api/customers/{customer-id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Smith",
    "email": "alice.smith@example.com",
    "phone": "+1-555-987-6543"
  }'
```

### Delete Customer
```bash
curl -X DELETE http://localhost:8000/api/customers/{customer-id}
```

## Architecture

The Customer Management API follows the Cyoda framework patterns:

- **Entity Layer**: `application/entity/customer/version_1/customer.py`
- **Workflow**: `application/resources/workflow/customer/version_1/Customer.json`
- **Processor**: `application/processor/customer_processor.py`
- **Validation**: `application/criterion/customer_validation_criterion.py`
- **Routes**: `application/routes/customers.py`
- **Models**: `application/models/customer_models.py`

### Workflow States

1. `initial_state` → `created` (automatic)
2. `created` → `validated` (with validation criterion)
3. `validated` → `processed` (with processor)
4. `processed` → `completed` (automatic)

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `201`: Created (with Location header)
- `400`: Bad Request (validation errors)
- `404`: Not Found
- `409`: Conflict (duplicate email)
- `500`: Internal Server Error

Error responses include:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

## OpenAPI Specification

The API automatically generates OpenAPI 3.0 specification available at:
- JSON format: `GET /openapi.json`
- The specification includes all endpoints, request/response schemas, and validation rules

## Development Notes

- Email uniqueness is enforced at both application and database levels
- All timestamps are in ISO 8601 format with UTC timezone
- Pagination uses 1-based page numbering
- Partial matching is supported for name and email filters
- Workflow transitions can be triggered manually via API or automatically by the system
- The application uses SQLite for development (in-memory mode available)

## Contributing

1. Follow the existing code patterns and architecture
2. Run all code quality checks before submitting
3. Add appropriate tests for new functionality
4. Update documentation as needed

## License

[Add your license information here]
