# Combined Agent API with Microservices Architecture

This project implements a combined API with a microservices architecture for agent management, invocation, and MCP (Model Context Protocol) tools. The architecture integrates multiple services into a single application while maintaining separation of concerns through a modular design.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│                          Combined Agent API                                │
│                                                                            │
├──────────┬───────────┬──────────┬───────────┬───────────┬────────────┬────┤
│          │           │          │           │           │            │    │
│  Agent   │  Agent    │  MCP     │  Agent    │  Agent    │  Feature   │Web │
│  Backend │  Boiler-  │  Tools   │  Field    │  Creator  │  Sharing   │site│
│  Service │  plate    │  Service │  Autofill │  Service  │  Service   │Test│
│          │  Service  │          │  Service  │           │            │er  │
│          │           │          │           │           │            │    │
└────┬─────┴─────┬─────┴────┬─────┴─────┬─────┴─────┬─────┴─────┬──────┴────┘
     │           │          │           │           │           │       
     │           │          │           │           │           │       
     ▼           ▼          ▼           ▼           ▼           ▼       
┌───────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│                                Supabase                                   │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

All services are integrated into a single application but maintain their independence through a modular microservice architecture. Each service has its own directory structure and routes, making it easy to maintain and extend.

## Microservices

### 1. Agent Backend Service

Handles database operations and provides API endpoints for managing:
- Agents
- Companies
- Roles
- Agent logs
- Role-based access control for company resources

### 2. Agent Boilerplate Service

Handles agent creation, management, and invocation:
- Agent invocation with streaming support
- Conversation memory management
- Tool integration via MCP
- Supports multiple LLM providers
- Agent information retrieval
- Logging agent interactions
- Agent API endpoints

### 3. MCP Tools Service

Manages Model Context Protocol (MCP) tools:
- Tool management (CRUD operations)
- Automatic tool refresh on startup
- MCP proxy process management and status monitoring

### 4. Agent Field Autofill Service

Provides automated field value generation for agent configuration:
- Field value recommendations based on context
- Streaming autofill responses for real-time updates
- Accepts GET or POST requests for SSE endpoints
- Integration with LLMs for intelligent field generation

### 5. Agent Creator Service

Facilitates the creation and configuration of AI agents:
- Natural language input parsing for agent configuration
- Streaming field parsing with SSE
- Tool recommendation based on agent purpose
- Keyword extraction from agent descriptions
- Field metadata and description retrieval
- Automated field generation and validation
- Support for multi-agent creation workflows

### 6. Feature Sharing Service

Enables sharing agents and threads with other users:
- Agent sharing with specific users (as editors or visitors)
- Thread sharing with specific users (as editors or visitors)
- Public link generation for agents and threads
- Access control management for shared resources

### 7. Chat Recommendation Service

Provides recommendations based on conversation history:
- Generate up to four suggestions from chat messages
- Stream recommendations using Server-Sent Events
- Invoke a chosen recommendation directly via API
- Summarize conversations and extract key topics

### 8. Website Tester Service

Provides a web interface for testing the API:
- HTML pages for interacting with the API
- Static files (CSS, JavaScript)
- Simple web server
- Stores auth tokens locally for easy testing
- Example pages for agents, tools, and sharing features

### MCP Library Components

Additional libraries supporting the microservices:
- `mcp_lib/agent_video` – generate images and videos via Fal.ai and FastMCP

## Running the Application

### Using Docker

```bash
# Build and run with Docker
./docker-run.sh
```

This will build the Docker image and start the application on port 8080.

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The application will be available at http://localhost:8080.

## API Endpoints

### Agent Backend Endpoints

- `/agents` - CRUD operations for agents
- `/companies` - CRUD operations for companies
- `/roles` - CRUD operations for roles
- `/agent-logs` - CRUD operations for agent logs

### Agent Boilerplate Endpoints

- `/agent-invoke/{route_path}/invoke` - Invoke an agent
- `/agent-invoke/{route_path}/info` - Get agent information
- `/agent-api/agents` - List available agents
- `/agent-api/agents/{agent_id}` - Get agent details

### MCP Tools Endpoints

- `/tools` - CRUD operations for tools
- `/mcp-tools/refresh` - Refresh MCP tools
- `/mcp-tools/status` - Get status of running MCP processes

### Agent Field Autofill Endpoints

- `/agent_field_autofill/invoke` - Generate field values
- `/agent_field_autofill/invoke-stream` - Stream field generation results

### Agent Creator Endpoints

- `/agent_creator_autofill/invoke` - Generate field values based on context
- `/agent_creator_autofill/invoke-stream` - Stream field generation results
- `/agent_creator_autofill/tools` - Get available tools for integration
- `/user_input/parse-stream` - Stream parsing of user input for multiple fields
- `/user_input/parse-field` - Parse user input for a specific field
- `/user_input/field-description/{field_name}` - Get field description
- `/user_input/field-metadata` - Get metadata for all available fields
- `/user_input/extract-keywords` - Extract keywords from agent name and description
- `/user_input/parse-multi-agent` - Parse input for multiple agent creation

### Feature Sharing Endpoints

- `/feature-sharing/agent/share-editor-with/{agent_id}/` - Share agent as editor
- `/feature-sharing/agent/share-visitor-with/{agent_id}/` - Share agent as visitor
- `/feature-sharing/agent/share-anyone-with-link/{agent_id}/` - Generate public link
- `/feature-sharing/thread/share-editor-with/{agent_id}/{thread_id}` - Share thread as editor
- `/feature-sharing/thread/share-visitor-with/{agent_id}/{thread_id}` - Share thread as visitor
- `/feature-sharing/thread/share-anyone-with-link/{agent_id}/{thread_id}` - Generate public link

### Chat Recommendation Endpoints

- `/chat-recommendation/generate-recommendations` - Get recommendations for a conversation
- `/chat-recommendation/invoke-recommendation` - Invoke a selected recommendation
- `/chat-recommendation/stream` - Stream chat responses and recommendations

### Website Tester Endpoints

- `/website` - Web interface for testing the API

### Common Endpoints

- `/user/info` - Get user information
- `/health` - Health check endpoint
- `/public` - Public route for testing
- `/get-llms` - Get available language models

## Tool Management

The MCP Tools service provides functionality for managing tools that can be used by agents. Tools are defined with the following structure:

```json
{
  "name": "example_tool",
  "description": "An example tool",
  "versions": [
    {
      "version": "1.0.0",
      "released": {
        "env": {
          "API_KEY": "your-api-key"
        },
        "args": "uvx mcp-server-fetch",
        "port": "10001",
        "method": "sse",
        "required_env": [
          "API_KEY"
        ]
      }
    }
  ]
}
```

When tools are created, updated, or deleted, the MCP Tools service automatically refreshes the running MCP processes to ensure they're in sync with the database.

## Environment Variables

The application requires the following environment variables:

- `SUPABASE_URL` - The URL of your Supabase project
- `SUPABASE_KEY` - The API key for your Supabase project
- `OPEN_ROUTER_API_KEY` - API key for OpenRouter (for LLM access)
- `OPEN_ROUTER_BASE_URL` - Base URL for OpenRouter API

These can be set in a `.env` file in the root directory of the project.

## Authentication

The application uses JWT authentication middleware, which:

1. Validates JWT tokens from the Authorization header
2. Extracts user information
3. Checks company access permissions
4. Handles CORS preflight requests

Public endpoints for accessing shared content are available without authentication.

## Development

### Prerequisites

- Python 3.11 or higher
- FastAPI
- Supabase
- Docker (optional)

### Project Structure

```
/
├── app.py                      # Main application entry point
├── auth_middleware.py          # Authentication middleware
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-run.sh               # Script to build and run Docker container
├── .env                        # Environment variables
├── config/                     # Configuration files
└── microservice/               # Microservices
    ├── agent_backend/          # Agent backend service
    │   └── routes/             # API routes
    ├── agent_boilerplate/      # Agent boilerplate service
    │   ├── boilerplate/        # Core functionality
    │   └── routes/             # API routes
    ├── mcp_tools/              # MCP tools service
    │   ├── routes/             # API routes
    │   └── utils/              # Utility functions
    ├── agent_field_autofill/   # Agent field autofill service
    │   ├── routes/             # API routes
    │   └── utils/              # Utility functions
    ├── agent_creator/          # Agent creator service
    │   ├── routes/             # API routes
    │   └── utils/              # Utility functions
    ├── feature_sharing/        # Feature sharing service
    │   └── routes/             # API routes
    ├── website_tester/         # Website tester service
    │   ├── css/                # CSS files
    │   ├── js/                 # JavaScript files
    │   └── *.html              # HTML pages
    └── mcp_lib/                # MCP library components
```

### Adding a New Microservice

To add a new microservice:

1. Create a new directory in the `microservice` directory
2. Create a `routes` directory inside your new microservice
3. Create route files with FastAPI routers
4. Import and include your routers in the main `app.py` file

### CORS Configuration

The API is configured to allow cross-origin requests from any origin, which is suitable for development but should be restricted in production.

CORS is configured in two places:
1. In `app.py` using FastAPI's CORSMiddleware
2. In `auth_middleware.py` to handle preflight requests

## License

[MIT License](LICENSE)