# MCP Tools Service

This directory contains the MCP (Model Context Protocol) Tools service for managing and running MCP tools that can be used by agents.

## Overview

The MCP Tools service provides functionality for:

1. Managing tool configurations in Supabase PostgreSQL
2. Starting, stopping, and monitoring MCP proxy processes
3. Refreshing tools automatically when changes are made
4. Providing status information about running MCP processes

## Components

### routes/tools.py

Provides API endpoints for managing tools:

- Creating new tools
- Retrieving tool information
- Updating existing tools
- Deleting tools

Tools are stored in Supabase PostgreSQL and include:
- Basic information (name, description)
- Version information
- Configuration details for running the tool

### routes/mcp_tools.py

Provides API endpoints for managing MCP processes:

- `/mcp-tools/refresh` - Refresh all MCP tools
- `/mcp-tools/status` - Get status of running MCP processes

### utils/_mcp_manager.py

Core class that manages MCP proxy processes:

- Starting processes with the correct configuration
- Monitoring process status
- Stopping processes when needed
- Updating processes when configurations change

### utils/_tool_args_converter.py

Utility for converting tool configurations from the database into command-line arguments for MCP proxy processes.

### utils/_get_tools_supabase.py

Utility for retrieving tool configurations from Supabase PostgreSQL.

## Tool Configuration Format

Tools are defined with the following structure:

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

Key components:

- `name` - The name of the tool
- `description` - A description of what the tool does
- `versions` - An array of version configurations
  - `version` - The version identifier
  - `released` - Configuration for the released version
    - `env` - Environment variables required by the tool
    - `args` - Command-line arguments for the tool
    - `port` - Port number for the MCP proxy
    - `method` - Communication method (usually "sse")
    - `required_env` - List of required environment variables

## Integration with Agents

Tools managed by this service can be used by agents through the Agent Boilerplate service. When an agent is invoked with tool configurations, the Agent Boilerplate service connects to the running MCP proxy processes to provide tool functionality to the agent.

## Automatic Tool Refresh

When tools are created, updated, or deleted through the API, the MCP Tools service automatically refreshes the running MCP processes to ensure they're in sync with the database. This happens in the following cases:

1. When a new tool is created
2. When an existing tool is updated
3. When a tool is deleted
4. When the application starts up

## API Endpoints

### Tool Management

- `POST /tools` - Create a new tool
- `GET /tools` - Get all tools
- `GET /tools/{tool_id}` - Get a specific tool
- `PUT /tools/{tool_id}` - Update a tool
- `DELETE /tools/{tool_id}` - Delete a tool

### MCP Process Management

- `POST /mcp-tools/refresh` - Refresh all MCP tools
- `GET /mcp-tools/status` - Get status of running MCP processes

## Authentication and Authorization

The MCP Tools service integrates with the authentication middleware to:

1. Verify that the user is authenticated
2. Check if the user has the appropriate role to manage tools
3. Enforce role-based access control for company-specific tools

## Example Usage

### Creating a New Tool

```http
POST /tools
Content-Type: application/json

{
  "name": "weather_tool",
  "description": "A tool for getting weather information",
  "versions": [
    {
      "version": "1.0.0",
      "released": {
        "env": {
          "WEATHER_API_KEY": "your-api-key"
        },
        "args": "uvx mcp-server-weather",
        "port": "10002",
        "method": "sse",
        "required_env": [
          "WEATHER_API_KEY"
        ]
      }
    }
  ]
}
```

### Refreshing Tools

```http
POST /mcp-tools/refresh
```

### Getting Tool Status

```http
GET /mcp-tools/status
```

Response:
```json
{
  "status": "success",
  "message": "Status retrieved successfully",
  "data": {
    "processes": {
      "10001": {
        "running": true,
        "command": "mcp-proxy --sse-port=10001 -e API_KEY your-api-key -- uvx mcp-server-fetch"
      },
      "10002": {
        "running": true,
        "command": "mcp-proxy --sse-port=10002 -e WEATHER_API_KEY your-api-key -- uvx mcp-server-weather"
      }
    },
    "count": 2
  }
}