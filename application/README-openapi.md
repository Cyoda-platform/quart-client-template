# OpenAPI Specifications

This directory contains comprehensive OpenAPI 3.0 specifications for the Cyoda Client Application API.

## Files

### `application/resources/openapi/openapi.yaml`
Main OpenAPI specification file containing:
- API metadata and server configuration
- Common security schemes (Bearer token authentication)
- Shared components (schemas, responses, parameters)
- Common error response definitions
- System endpoints (health check)

### `application/resources/openapi/order_api.yaml`
Detailed Order entity API specification containing:
- Complete CRUD operations for Order entities
- Workflow-aware state management
- Request/response schemas with validation rules
- Comprehensive examples for all operations
- Error handling for business rule violations

## API Operations

### Order Management
The Order API provides the following operations:

| Method | Endpoint | Description | State Transition |
|--------|----------|-------------|------------------|
| `POST` | `/orders` | Create new order | `initial_state` → `created` |
| `GET` | `/orders` | List all orders | N/A (read-only) |
| `GET` | `/orders/{id}` | Get order by ID | N/A (read-only) |
| `PUT` | `/orders/{id}` | Update existing order | `created`/`updated` → `updated` |
| `POST` | `/orders/{id}/cancel` | Cancel order | `created`/`updated` → `cancelled` |

### Authentication
All API endpoints require Bearer token authentication:
```
Authorization: Bearer <your-jwt-token>
```

## Viewing the Specifications

### Option 1: Swagger UI (Recommended)
1. Install a local Swagger UI server or use online tools
2. Load the `openapi.yaml` file to view the complete API documentation
3. Interactive documentation with request/response examples

### Option 2: Redoc
1. Use Redoc CLI or online viewer
2. Load the specification files for a clean, readable documentation format

### Option 3: VS Code Extension
1. Install the "OpenAPI (Swagger) Editor" extension
2. Open the YAML files directly in VS Code
3. Get syntax highlighting and validation

### Option 4: Online Validators
- [Swagger Editor](https://editor.swagger.io/) - Paste YAML content
- [Redoc Online](https://redocly.github.io/redoc/) - Load from URL or paste content

## Using the Specifications

### For API Development
- Use the schemas as reference for request/response structures
- Implement endpoints following the defined patterns
- Ensure proper error handling as specified

### For Client Development
- Generate client SDKs using OpenAPI generators
- Use the examples for testing and integration
- Reference the business rules for proper API usage

### For Testing
- Use the examples as test cases
- Validate responses against the defined schemas
- Test error scenarios as documented

## Business Rules

### Order Entity Rules
- **Customer ID**: Must be at least 3 characters long
- **Amount**: Must be greater than 0 and ≤ 1,000,000
- **Description**: Optional, maximum 500 characters
- **State Management**: Orders follow workflow-driven state transitions

### State Transitions
- **Create**: Automatic transition from `initial_state` to `created`
- **Update**: Manual transition, only from `created` or `updated` states
- **Cancel**: Manual transition to `cancelled` (terminal state)
- **Cancelled orders**: Cannot be updated or reactivated

## Validation

### Schema Validation
All requests and responses are validated against the defined schemas:
- Required fields must be present
- Data types must match specifications
- String lengths and numeric ranges are enforced
- Enum values are restricted to defined options

### Business Logic Validation
Additional validation occurs at the business logic level:
- Workflow state compatibility checks
- Entity relationship validations
- Custom business rule enforcement

## Error Handling

### Standard HTTP Status Codes
- `200` - Success (GET, PUT operations)
- `201` - Created (POST operations)
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (entity doesn't exist)
- `409` - Conflict (business rule violations)
- `500` - Internal Server Error (unexpected errors)

### Error Response Format
All errors follow a consistent format:
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "additional": "context information"
  }
}
```

### Validation Errors
Validation errors include detailed field-level information:
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "validation_errors": [
    {
      "field": "amount",
      "message": "Amount must be greater than 0",
      "value": -10.50
    }
  ]
}
```

## Integration Notes

### Workflow Integration
The API is designed to work with Cyoda's workflow engine:
- State transitions trigger appropriate processors
- Entity metadata is automatically managed
- Workflow validation ensures proper state progression

### Entity Service Integration
All operations use the EntityService for:
- Consistent entity management
- Automatic state synchronization
- Proper error handling and validation

### Future Extensions
The specification structure supports easy extension for:
- Additional entity types
- New workflow states and transitions
- Enhanced filtering and search capabilities
- Batch operations and bulk updates

## Maintenance

### Updating Specifications
When modifying the API:
1. Update the relevant YAML files
2. Validate against OpenAPI 3.0 standards
3. Test with actual API implementation
4. Update examples and documentation
5. Increment version numbers as appropriate

### Version Management
- Follow semantic versioning for API changes
- Maintain backward compatibility when possible
- Document breaking changes clearly
- Provide migration guides for major updates
