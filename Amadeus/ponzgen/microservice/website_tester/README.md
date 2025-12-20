# API Testing Frontend

This testing frontend provides a user interface for interacting with the backend API services. This README documents the data flow for each feature, including endpoints, required data, and expected responses.

## Table of Contents

1. [Authentication](#authentication)
2. [Agents](#agents)
   - [Agent List](#agent-list)
   - [Agent Creation/Update](#agent-creationupdate)
   - [Agent Deletion](#agent-deletion)
3. [Tools](#tools)
   - [Tool List](#tool-list)
   - [Tool Creation/Update](#tool-creationupdate)
   - [Tool Deletion](#tool-deletion)
   - [MCP Tools Refresh](#mcp-tools-refresh)
4. [Agent Invocation](#agent-invocation)
   - [Agent Selection](#agent-selection)
   - [Agent Details](#agent-details)
   - [Agent Invocation](#agent-invocation-1)
   - [Available Models](#available-models)

## Authentication

All API requests require authentication using a bearer token.

**Data Flow:**
- The token is stored in localStorage under the key `api_token`
- The token is retrieved and added to the `Authorization` header for all API requests
- If no token is found, the user is redirected to the login page

**Implementation:**
- Authentication logic is in `js/main.js` in the `API.getHeaders()` function
- Token validation is handled by `Utils.checkAuth()`

## Agents

### Agent List

**Endpoint:** `GET /agents`

**Data Flow:**
- Frontend sends a GET request to `/agents`
- Backend returns an array of agent objects
- Frontend displays the agents in a table/grid

**Response Data Structure:**
```json
[
  {
    "agent_id": "uuid-string",
    "agent_name": "Agent Name",
    "description": "Agent description",
    "route_path": "agent-route-path",
    "on_status": true,
    "tools": ["tool-id-1", "tool-id-2"],
    "agent_style": "The agent will reply in a warm and friendly manner, using English."
  }
]
```

### Agent Creation/Update

**Endpoints:** 
- Create: `POST /agents`
- Update: `PUT /agents/{agent_id}`

**Data Flow:**
- Frontend collects agent data from form inputs
- For updates, the current agent data is pre-filled in the form
- Frontend sends POST/PUT request with the agent data
- Backend creates/updates the agent and returns the agent object

**Request Data Structure:**
```json
{
  "agent_name": "Agent Name",
  "description": "Agent description",
  "route_path": "agent-route-path",
  "on_status": true,
  "tools": ["tool-id-1", "tool-id-2"],
  "agent_style": "The agent will reply in a warm and friendly manner, using English."
}
```

**Notes:**
- If agent_style is left empty, a default friendly message is used
- The agent_style field is a free-form text area (not a dropdown)

### Agent Deletion

**Endpoint:** `DELETE /agents/{agent_id}`

**Data Flow:**
- Frontend sends DELETE request to `/agents/{agent_id}`
- Backend deletes the agent and returns a success message
- Frontend removes the agent from the display

## Tools

### Tool List

**Endpoint:** `GET /tools`

**Optional Query Parameters:**
- `company_id`: Filter tools by company ID

**Data Flow:**
- Frontend sends a GET request to `/tools` (optionally with company_id)
- Backend returns an array of tool objects
- Frontend displays the tools in a grid

**Response Data Structure:**
```json
[
  {
    "tool_id": "uuid-string",
    "name": "Tool Name",
    "description": "Tool description",
    "versions": [
      {
        "version": "1.0.0",
        "released": {
          "env": {"API_KEY": "your-api-key"},
          "args": "command arguments",
          "port": "10001",
          "method": "sse",
          "required_env": ["API_KEY"]
        }
      }
    ]
  }
]
```

### Tool Creation/Update

**Endpoints:** 
- Create: `POST /tools`
- Update: `PUT /tools/{tool_id}`

**Optional Query Parameters:**
- `company_id`: Assign tool to a company

**Data Flow:**
- Frontend collects tool data from form inputs
- For each version, collects version number, args, port, and JSON data for env and required_env
- Frontend sends POST/PUT request with the tool data
- Backend creates/updates the tool and returns the tool object
- Frontend automatically calls the MCP tools refresh endpoint

**Request Data Structure:**
```json
{
  "name": "Tool Name",
  "description": "Tool description",
  "versions": [
    {
      "version": "1.0.0",
      "released": {
        "env": {"API_KEY": "your-api-key"},
        "args": "command arguments",
        "port": "10001",
        "method": "sse",
        "required_env": ["API_KEY"]
      }
    }
  ]
}
```

**Notes:**
- The method is currently fixed to "sse"
- Environment variables are entered as JSON
- Required environment variables are entered as a JSON array

### Tool Deletion

**Endpoint:** `DELETE /tools/{tool_id}`

**Data Flow:**
- Frontend sends DELETE request to `/tools/{tool_id}`
- Backend deletes the tool and returns a success message
- Frontend removes the tool from the display
- Frontend automatically calls the MCP tools refresh endpoint

### MCP Tools Refresh

**Endpoint:** `POST /mcp-tools/refresh`

**Data Flow:**
- Frontend sends an empty POST request to `/mcp-tools/refresh`
- Backend refreshes the MCP tools cache
- This endpoint is called automatically after tool creation, update, or deletion

## Agent Invocation

### Agent Selection

**Endpoint:** `GET /agents`

**Data Flow:**
- Frontend sends a GET request to `/agents`
- Backend returns an array of agent objects with route paths
- Frontend populates a dropdown with the agent names and stores their route paths

### Agent Details

**Endpoint:** `GET /agents/{agent_id}`

**Data Flow:**
- When an agent is selected, frontend sends a GET request to `/agents/{agent_id}`
- Backend returns the agent details including associated tools
- Frontend displays the agent details and tool information

**Response Data Structure:**
```json
{
  "agent_id": "uuid-string",
  "agent_name": "Agent Name",
  "description": "Agent description",
  "route_path": "agent-route-path",
  "on_status": true,
  "tools": ["tool-id-1", "tool-id-2"],
  "agent_style": "The agent will reply in a warm and friendly manner, using English.",
  "tool_details": [
    {
      "tool_id": "tool-id-1",
      "name": "Tool Name",
      "description": "Tool description"
    }
  ]
}
```

### Agent Invocation

**Endpoint:** `POST /agent-invoke/{route_path}/invoke`

**Data Flow:**
- Frontend collects user input (message, context, thread_id, model, etc.)
- Frontend sends POST request to `/agent-invoke/{route_path}/invoke`
- Backend processes the request through the agent and returns the response
- Frontend displays the response

**Request Data Structure:**
```json
{
  "input": {
    "messages": "User message",
    "context": "Additional context"
  },
  "config": {
    "configurable": {
      "thread_id": "1"
    }
  },
  "metadata": {
    "model_name": "gpt-4",
    "reset_memory": false,
    "load_from_json": true,
    "agent_style": "Custom style override (optional)"
  },
  "agent_config": {
    // Full agent details object from GET /agents/{agent_id}
  }
}
```

**Notes:**
- thread_id is required (defaults to "1")
- The agent_config contains the full agent details retrieved from the agent details endpoint
- The response format depends on the agent implementation

### Available Models

**Endpoint:** `GET /get-llms`

**Data Flow:**
- Frontend sends a GET request to `/get-llms`
- Backend returns an object with an array of available model IDs
- Frontend populates the model selection dropdown with these options

**Response Data Structure:**
```json
{
  "available_models": [
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.7-sonnet",
    "deepseek/deepseek-chat",
    "gpt-3.5-turbo",
    "openai/gpt-4o-mini"
  ]
}
```

## Migration Notes

When migrating this testing frontend to a production frontend, consider the following:

1. **Authentication**: Implement a more robust authentication system with token refresh
2. **Error Handling**: Enhance error handling for production use
3. **Validation**: Add more client-side validation before sending requests
4. **UI/UX**: Improve the user interface for better user experience
5. **State Management**: Consider using a state management library for complex applications
6. **Caching**: Implement caching strategies for frequently accessed data
7. **Performance**: Optimize performance for production use
8. **Security**: Ensure all user inputs are properly sanitized

The core data flow and API interactions should remain the same, making the migration process straightforward.
