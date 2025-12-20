# Agent Boilerplate

This directory contains the agent boilerplate code for creating, managing, and invoking agents using Supabase PostgreSQL.

## Overview

The agent boilerplate provides a framework for:

1. Managing agent configurations in Supabase PostgreSQL
2. Dynamically routing agent invocations
3. Handling agent memory and conversation state
4. Integrating with tools via MCP (Model Context Protocol)

## Components

### agent_boilerplate.py

The core module that handles agent creation, configuration loading, and invocation. It provides:

- Memory management for agent conversations
- Input parsing and formatting
- Agent invocation with configurable model selection
- Tool integration

### agent_templates/react_agent.py

Provides the implementation for the React agent pattern using LangChain. It includes:

- Agent creation with the ReAct pattern
- Tool integration via LangChain tools
- Memory management for conversation history

### utils/get_llms.py

Utility for creating LLM instances with the appropriate configuration:

- Support for multiple LLM providers
- Configuration for OpenRouter API
- Model selection based on user preferences

### routes/agent_invoke.py and routes/agent_api.py

Set up the FastAPI routes for agent management and invocation. They integrate:

- The agent boilerplate with the FastAPI application
- Routes for agent invocation
- Routes for agent information retrieval

### models.py

Defines the Pydantic models used in the agent boilerplate:

- Agent input and configuration models
- Tool configuration models

## Integration with Main Application

The agent boilerplate is integrated with the main FastAPI application in app.py:

1. The routers from agent_invoke.py and agent_api.py are imported
2. These routers are included in the main FastAPI application

```python
# Import routes from agent_boilerplate microservice
from microservice.agent_boilerplate.routes.agent_invoke import router as agent_invoke_router
from microservice.agent_boilerplate.routes.agent_api import router as agent_api_router

# In app.py
app = FastAPI()

# Include routers from agent_boilerplate
app.include_router(agent_invoke_router)
app.include_router(agent_api_router)
```

## Agent Invocation

Agents can be invoked using the following endpoint:

```
POST /agent-invoke/{agent_route_path}/invoke
```

The agent_invoke router handles this endpoint and passes the request to the agent_boilerplate.py module.

The request body should follow this format:

```json
{
  "input": {
    "messages": "Your query here",
    "context": "Optional context information"
  },
  "config": {
    "configurable": {
      "thread_id": "123"
    }
  },
  "metadata": {
    "model_name": "gpt-4",
    "reset_memory": false,
    "load_from_json": true,
    "agent_style": ""
  },
  "agent_config": {
    "agent_name": "example_agent",
    "description": "An example agent",
    "route_path": "example-agent",
    "agent_style": "",
    "on_status": true,
    "tools": ["tool-id-1", "tool-id-2"],
    "tool_details": [
      {
        "tool_id": "tool-id-1",
        "name": "example_tool",
        "description": "An example tool",
        "versions": [
          {
            "version": "1",
            "released": {
              "env": {
                "API_KEY": "your-api-key"
              },
              "args": "your-command-args",
              "port": "10001",
              "method": "sse",
              "version": "1.0.0"
            }
          }
        ]
      }
    ]
  }
}
```

## Agent Information

Basic information about an agent can be retrieved using:

```
GET /agent-invoke/{agent_route_path}/info
```

## Available Agents

A list of all agents available to the current user can be retrieved using:

```
GET /agent-api/agents
```

Additionally, a list of available LLM models can be retrieved using:

```
GET /agent-api/get-llms
```

This endpoint returns a list of available LLM models that can be used with agents, sourced from OpenRouter or other providers.

## Agent Details

Detailed information about an agent can be retrieved using:

```
GET /agent-api/agents/{agent_id}
```

## Authentication and Authorization

The agent boilerplate integrates with the authentication middleware to:

1. Verify that the user is authenticated
2. Check if the user has access to the requested agent
3. Enforce role-based access control for company agents

## Tool Integration

Agents can be configured to use tools via MCP (Model Context Protocol). Tool configurations are managed by the MCP Tools service and can be included in the agent_config when invoking an agent.

The agent_boilerplate.py module includes functionality to:

1. Extract tool configurations from the agent_config
2. Connect to MCP proxy processes using the MultiServerMCPClient
3. Make tools available to the agent during invocation
4. Handle tool execution and response processing

Tools are defined in the Supabase database and managed through the `/tools` endpoints provided by the MCP Tools service.

## Memory Management

Each agent has its own conversation memory, which persists across invocations. The memory can be reset using the `reset_memory` flag in the agent input metadata.