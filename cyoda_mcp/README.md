# Cyoda MCP Server

A Model Context Protocol (MCP) server for the Cyoda platform, providing AI assistants with seamless access to Cyoda's entity management, search, workflow, and deployment capabilities.

## Quick Start (One-liner Install)

### Zero-setup run (no clone, no venv)
```bash
# Set your Cyoda credentials
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"

# Run immediately with pipx
pipx run mcp-cyoda
```

### Install once and run repeatedly
```bash
# Install the package
pipx install mcp-cyoda

# Run the server
mcp-cyoda

# Or with custom options
mcp-cyoda --transport http --port 9000
mcp-cyoda --help
```

## Getting Your Cyoda Environment

1. **Sign up**: Go to [https://ai.cyoda.net](https://ai.cyoda.net) and create an account
2. **Deploy environment**: In a new chat, either:
   - Build an example application, or
   - Directly ask: "Please deploy a Cyoda environment for me"
3. **Get credentials**: Once your environment is deployed, ask for your credentials in the chat

You'll receive:
- `CYODA_CLIENT_ID` - Your unique client identifier
- `CYODA_CLIENT_SECRET` - Your client secret key
- `CYODA_HOST` - Your environment host (e.g., `client-123.eu.cyoda.net`)

## Configuration

### Required Environment Variables
```bash
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"  # Host only, no https://
```

### Optional Environment Variables
- `MCP_TRANSPORT` - Default transport type (stdio, http, sse)

### IDE/AI Assistant Integration

Add this to your MCP configuration (e.g., in Cursor, Claude Desktop, or other MCP-compatible tools):

```json
{
  "mcpServers": {
    "cyoda": {
      "command": "mcp-cyoda",
      "env": {
        "CYODA_CLIENT_ID": "your-client-id-here",
        "CYODA_CLIENT_SECRET": "your-client-secret-here",
        "CYODA_HOST": "client-123.eu.cyoda.net"
      }
    }
  }
}
```

## Available Tools

The MCP server provides comprehensive access to Cyoda platform capabilities:

### Entity Management
- **Create entities** - Store structured data in Cyoda
- **Read entities** - Retrieve entities by ID or search criteria
- **Update entities** - Modify existing entity data
- **Delete entities** - Remove entities from the system
- **List entities** - Browse all entities of a specific type

### Advanced Search
- **Field-based search** - Find entities by specific field values
- **Complex queries** - Use advanced search conditions with operators
- **Full-text search** - Search across entity content

### Edge Messages
- **Send messages** - Dispatch messages through Cyoda's messaging system
- **Retrieve messages** - Get message history and status

### Workflow Management
- **Export workflows** - Download workflow definitions
- **Import workflows** - Upload and deploy new workflows
- **Copy workflows** - Duplicate workflows between entities

## Example Conversations

With the MCP server connected to your AI assistant (Cursor, Claude Desktop, etc.), you can have natural conversations like:

### Data Collection and Storage
```
You: "Go to website https://example.com and fetch the product data"
AI: [Fetches data from the website]
You: "Save this data as entities in Cyoda"
AI: [Creates entities in your Cyoda environment using the MCP tools]
```

### Data Retrieval
```
You: "Search for entities where category equals 'electronics'"
AI: [Uses search tools to find matching entities]
You: "Get the entity with ID abc-123"
AI: [Retrieves the specific entity using entity management tools]
```

### Workflow Operations
```
You: "Export the workflow from my product entity"
AI: [Exports workflow definition using workflow management tools]
You: "Copy this workflow to my order entity"
AI: [Copies workflow between entities]
```

The AI assistant can seamlessly combine web scraping, data processing, and Cyoda operations in a single conversation, making complex data workflows as simple as natural language requests.

