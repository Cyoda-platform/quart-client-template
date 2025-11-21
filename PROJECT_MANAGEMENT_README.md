# Project Management Application

A comprehensive project management web application built using the Cyoda framework that enables teams to organize projects, assign tasks, track progress, and collaborate in real-time.

## Features

### Core Functionality
- **User Management**: Role-based access control (Admin, Manager, Member)
- **Project Organization**: Create and manage projects with team members
- **Task Management**: Full task lifecycle with workflow states
- **Real-time Collaboration**: Comments, mentions, and notifications
- **File Attachments**: Upload and manage task-related files
- **Time Tracking**: Log work hours and track project progress

### Task Workflow
Tasks follow a structured workflow:
- **Backlog** → **Todo** → **In Progress** → **Review** → **Done**

With role-based transition controls:
- Only assignees can move tasks to "In Progress"
- Only managers/owners can approve tasks from "Review" to "Done"
- Admins have full control over all transitions

### Entities
1. **User**: System users with roles and permissions
2. **Project**: Containers for tasks with team members
3. **Task**: Work items with assignments, priorities, and dependencies
4. **Comment**: Collaboration through task discussions
5. **Attachment**: File uploads associated with tasks
6. **TimeEntry**: Time tracking for tasks and projects

## Architecture

Built on the Cyoda framework with:
- **Entity-driven design**: Each business object extends CyodaEntity
- **Workflow management**: State transitions managed by Cyoda workflows
- **Processor-based logic**: Business logic implemented as processors
- **Criteria validation**: Rule-based validation for state transitions
- **REST API**: Full CRUD operations with filtering and pagination

## Setup and Installation

### Prerequisites
- Python 3.9+
- Virtual environment support
- PostgreSQL (for production)
- Redis (for real-time features)

### Development Setup

1. **Clone and setup environment**:
```bash
git clone <repository-url>
cd project-management-app
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -e ".[dev]"
```

3. **Run code quality checks**:
```bash
python -m black .
python -m isort .
python -m mypy .
python -m flake8 .
python -m bandit -r . -x tests/
```

4. **Start the application**:
```bash
python -m application.app
```

## API Endpoints

### Core CRUD Operations
All entities support standard REST operations:

- `GET /api/{entity}s` - List with pagination and filtering
- `GET /api/{entity}s/{id}` - Get by ID
- `POST /api/{entity}s` - Create new entity
- `PUT /api/{entity}s/{id}` - Update entity
- `DELETE /api/{entity}s/{id}` - Delete entity

### Special Endpoints

#### Task Management
- `POST /api/tasks/{id}/transition` - Manual state transitions
- `GET /api/projects/{id}/tasks` - Get all tasks for a project

#### Collaboration
- `POST /api/tasks/{id}/comments` - Add comment to task
- `POST /api/tasks/{id}/attachments` - Upload attachment
- `POST /api/tasks/{id}/time-entries` - Log time entry

### Filtering Examples

#### Tasks
```bash
GET /api/tasks?project_id=123&status=in_progress&assignee_id=456
GET /api/tasks?priority=HIGH&due_date_before=2024-12-31
```

#### Projects
```bash
GET /api/projects?owner_id=123&status=active
```

## Development Guidelines

### Code Quality
This project follows strict code quality standards:
- **Type hints**: All functions must have proper type annotations
- **Formatting**: Code formatted with Black
- **Import sorting**: Imports organized with isort
- **Linting**: Code must pass flake8 checks
- **Security**: Code scanned with bandit

### Entity Development
When creating new entities:
1. Extend `CyodaEntity` from `common.entity.cyoda_entity`
2. Define `ENTITY_NAME` and `ENTITY_VERSION` constants
3. Create corresponding JSON entity definition
4. Implement proper validation with Pydantic

### Workflow Development
1. Create workflow JSON in `application/resources/workflow/{entity}/version_1/`
2. Validate against `example_application/resources/workflow/workflow_schema.json`
3. Use explicit `manual: true/false` for all transitions
4. Match processor names exactly to Python class names

### Testing
Run the complete test suite:
```bash
# Code quality checks
python -m mypy .
python -m black . --check
python -m isort . --check-only
python -m flake8 .
python -m bandit -r . -x tests/

# Unit tests (when implemented)
python -m pytest tests/
```

## Project Structure

```
application/
├── entity/                 # Entity definitions
│   ├── user/
│   ├── project/
│   ├── task/
│   ├── comment/
│   ├── attachment/
│   └── time_entry/
├── processor/              # Business logic processors
├── criterion/              # Validation criteria
├── routes/                 # API endpoints
└── resources/
    ├── entity/            # JSON entity definitions
    ├── workflow/          # Workflow JSON files
    └── functional_requirements/
```

## Deployment

### Docker
```bash
docker build -t project-management-app .
docker run -p 8000:8000 project-management-app
```

### Docker Compose
```bash
docker-compose up -d
```

## Contributing

1. Follow the established code patterns in `example_application/`
2. Ensure all code quality checks pass
3. Update functional requirements if adding new features
4. Test thoroughly before submitting changes

## License

[Add your license information here]

## Support

For questions or issues, please refer to the functional requirements document in `application/resources/functional_requirements/` or contact the development team.
