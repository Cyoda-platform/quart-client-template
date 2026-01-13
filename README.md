# Cyoda Calculation Node Application

A comprehensive application framework for building calculation nodes within the Cyoda platform. This project provides a structured foundation for developing entity-driven applications with workflow automation, built on the asynchronous Quart web framework.

## What is This?

This is a **Cyoda Calculation Node** - a specialized application that:
- Manages **entities** (structured data models) within the Cyoda ecosystem
- Executes **workflows** (finite-state machines) to process entity state transitions
- Integrates with the Cyoda platform via gRPC for seamless data synchronization
- Provides REST APIs for entity management and workflow operations
- Supports AI assistant integration through the Model Context Protocol (MCP)

## Project Structure

```
├── application/          # Your application code (entities, workflows, routes)
├── common/              # Shared infrastructure (auth, config, gRPC, repository)
├── cyoda_mcp/           # MCP server for AI assistant integration
├── example_application/ # Reference implementation
├── services/            # Service configuration and initialization
└── tests/               # Comprehensive test suite
```

### Key Directories

- **`application/`** - Your custom business logic
  - `entity/` - Entity definitions and workflow implementations
  - `routes/` - REST API endpoints
  - `processor/` - Custom processors and criteria functions

- **`cyoda_mcp/`** - MCP server for AI integration
  - See [cyoda_mcp/README.md](cyoda_mcp/README.md) for MCP server documentation

- **`common/`** - Shared infrastructure (do not modify unless necessary)
  - `auth/` - Authentication and token management
  - `config/` - Configuration and environment variables
  - `grpc_client/` - Cyoda gRPC integration
  - `repository/` - Data access layer
  - `service/` - Business logic interfaces

- **`example_application/`** - Reference implementation showing best practices

## Quick Start

### 1. Set Up Environment

```bash
# Clone the repository
git clone <repository-url>
cd mcp-cyoda-quart-app

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"
```

### 3. Run the Application

```bash
# Run the application server
python -m application.app

# Or run the MCP server for AI integration
python -m cyoda_mcp
```

## MCP Server Integration

This project includes a **Model Context Protocol (MCP) server** that enables AI assistants to interact with your Cyoda application.

For complete MCP server documentation, see: **[cyoda_mcp/README.md](cyoda_mcp/README.md)**

### Quick MCP Setup

```bash
# Install globally
pipx install mcp-cyoda

# Run the server
mcp-cyoda
```

## Development

### Code Quality

```bash
# Run all quality checks
python -m black . && python -m isort . && python -m mypy . && python -m flake8 . && python -m bandit -r .

# Run tests
python -m pytest tests/ -v
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and development workflow
- **[AI_TESTING_GUIDE.md](AI_TESTING_GUIDE.md)** - Testing with AI assistants
- **[CYODA_E2E_TESTING_GUIDE.md](CYODA_E2E_TESTING_GUIDE.md)** - End-to-end testing procedures
- **[cyoda_mcp/README.md](cyoda_mcp/README.md)** - MCP server documentation
- **[docs/](docs/)** - Architecture and design documentation

## Getting Help

1. **Cyoda Platform**: [https://ai.cyoda.net](https://ai.cyoda.net)
2. **Documentation**: [https://docs.cyoda.net](https://docs.cyoda.net)
3. **Issues**: [GitHub Issues](https://github.com/Cyoda-platform/quart-client-template/issues)

## License

MIT License - See [LICENSE](LICENSE) for details