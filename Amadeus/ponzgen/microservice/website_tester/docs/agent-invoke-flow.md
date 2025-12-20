# Agent Invoke Microservice Flow

## Overview

The Agent Invoke Microservice provides functionality for invoking AI agents in the system and retrieving agent information. This document explains the application flow from the frontend UI through to the backend API and details the data requirements for the microservice.

## Application Components

1. **Frontend UI (`agent-invoke.html`)**
   - Provides the HTML structure for the agent invocation interface
   - Contains sections for agent selection, invocation inputs, and response display
   - Includes debugging sections showing request details

2. **Frontend Logic (`agent-invoke.js`)**
   - Handles all client-side interactions and API calls
   - Manages agent data loading and form handling
   - Provides agent invocation functionality

3. **Backend API (`agent_invoke.py`)**
   - Provides RESTful endpoints for agent invocation operations
   - Handles authentication, permission checks, and business logic
   - Manages interactions with the agent boilerplate

## User Flow

### 1. Select an Agent

**Frontend:**
- On page load, the frontend automatically calls `loadAgentsForDropdown()` function
- The function makes a GET request to the `/agents` endpoint
- Results are displayed in a dropdown for selection
- Users can select an agent to view details

**Backend:**
- The `/agents` endpoint retrieves agents based on:
  - User ID (personal agents)
  - Company ID (if a filter is applied)
- The backend fetches data from the `agents` table

### 2. View Agent Details

**Frontend:**
- When a user selects an agent, the `getAgentDetails()` function is called
- This makes a GET request to `/agents/{agent_id}`
- Agent details are displayed including basic information and tools
- The agent details are stored in the `currentAgentDetails` variable for use in invocation

**Backend:**
- The `/agents/{agent_id}` endpoint retrieves the full details of a specific agent
- It also fetches tool details for each tool assigned to the agent
- Data is fetched from the `agents` table and `tools_with_decrypted_keys` table

### 3. Invoke Agent

**Frontend:**
1. User selects an agent from the dropdown
2. User fills out the form with:
   - Message (required)
   - Context (optional)
   - Thread ID (default: "1")
   - Model Name (selected from available models)
   - Reset Memory (checkbox)
   - Load From JSON (checkbox)
   - Agent Style (optional custom style)
3. User clicks "Invoke Agent" to submit the form
4. The `invokeAgent()` function sends a POST request to `/agent-invoke/{agent_id}/invoke`

**Backend:**
1. The POST `/agent-invoke/{agent_id}/invoke` endpoint receives the request
2. Validates user permissions based on ownership and role
3. Verifies that the agent exists and is active
4. Processes the invocation request through the agent boilerplate
5. Returns the agent's response

### 4. Get Available Models

**Frontend:**
- On page load, the `loadAvailableModels()` function is called
- This makes a GET request to the `/get-llms` endpoint
- Available models are displayed in a dropdown for selection

**Backend:**
- The `/get-llms` endpoint retrieves available language models
- If no models are available, default models are provided

## Authentication Flow

The application uses a token-based authentication system:

1. JWT token is extracted from the Authorization header
2. Token is validated against Supabase
3. User information is added to the request state
4. Permissions are checked based on user role, ownership, and company association

## Data Requirements

### Core Data Entities

1. **Agent Input Data**:
   - `input`: Contains messages and context
     - `messages`: The user's message to the agent (string, required)
     - `context`: Additional context for the agent (string, optional)
   - `config`: Configuration options
     - `configurable`: Contains configurable options
       - `thread_id`: Identifier for conversation continuity (string, required)
   - `metadata`: Additional settings
     - `model_name`: The language model to use (string)
     - `reset_memory`: Whether to reset agent memory (boolean)
     - `load_from_json`: Whether to load from JSON (boolean)
     - `agent_style`: Custom agent style (string, optional)
   - `agent_config`: Full agent configuration (object)

2. **Agent Config Data**:
   - `agent_id`: Unique identifier for each agent (UUID)
   - `agent_name`: Name of the agent (string)
   - `description`: Optional description (string)
   - `agent_style`: Style/personality configuration (string)
   - `on_status`: Active status flag (boolean)
   - `tools`: Array of tool IDs (UUID[])
   - `company_id`: Optional association with a company (UUID)
   - `user_id`: Owner of the agent (UUID)
   - `share_editor_with`: Array of email addresses with editor access
   - `share_visitor_with`: Array of email addresses with visitor access

3. **Tool Data**:
   - `tool_id`: Unique identifier for each tool (UUID)
   - `name`: Tool name (string)
   - `description`: Tool description (string)
   - `versions`: Array of version configurations (object[])

4. **User Data**:
   - `user_id`: Unique identifier (UUID)
   - `email`: User email address (string)
   - Authentication information (JWT)

### Database Tables & Relationships

The microservice relies on the following database tables:

- `agents`: Stores agent information
- `tools_with_decrypted_keys`: View with decrypted environment variables
- `user_companies`: Maps users to companies with roles
- `users`: Stores user information
- `agent_logs`: Stores agent conversation history

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent-invoke/{agent_id}/invoke` | POST | Invoke an agent with the provided input |
| `/agent-invoke/{agent_id}/invoke-stream` | POST | Invoke an agent with streaming response |
| `/agent-invoke/{agent_id}/info` | GET | Get basic information about an agent |
| `/agent-invoke/shared-agent/{agent_hash}` | GET | Get a publicly shared agent by hash |
| `/agent-invoke/shared-thread/{thread_hash}` | GET | Get a publicly shared thread by hash |
| `/agents` | GET | Get all agents (filtered by user or company) |
| `/agents/{agent_id}` | GET | Get a specific agent by ID with tool details |
| `/get-llms` | GET | Get available language models |

## Access Control

The microservice implements strict access control:

1. **Agent Owner Access**:
   - The user who created the agent has full access

2. **Company Access**:
   - Users within the same company can access company agents
   - Access is determined by role within the company

3. **Shared Access**:
   - Users listed in `share_editor_with` have editor access
   - Users listed in `share_visitor_with` have visitor access

4. **Public Access**:
   - Shared agents and threads can be accessed via public hash without authentication

## Error Handling

- The backend uses standardized error responses defined in the error module
- Specific error types include: `BadRequestError`, `NotFoundError`, `ForbiddenError`, `InternalServerError`
- The frontend shows error notifications to users when API calls fail 