# Agent Logs Microservice Flow

## Overview

The Agent Logs Microservice provides functionality for tracking, viewing, and managing the execution history of AI agents in the system. It captures detailed information about agent interactions, including token usage, pricing, and conversation history. This document explains the application flow from the frontend UI through to the backend API and details the data requirements.

## Application Components

1. **Frontend UI (`agent-logs.html`)**
   - Provides a comprehensive interface for managing agent logs
   - Includes sections for creating new logs, viewing existing logs, and examining log details
   - Features a form for manually adding logs and a tabular view for listing logs

2. **Frontend Logic (`agent-logs.js`)**
   - Handles all client-side interactions and API calls
   - Manages agent data loading and form handling
   - Provides functionality for creating, viewing, and deleting logs
   - Formats and displays chat history from logs

3. **Backend API (`agent_logs.py`)**
   - Provides RESTful endpoints for log operations
   - Handles authentication, permission checks, and data validation
   - Manages interactions with the database for log storage and retrieval

## User Flow

### 1. Load Agents for Selection

**Frontend:**
- On page load, the frontend automatically calls `loadAgents()` function
- The function makes a GET request to the `/agents` endpoint
- Results are displayed in two dropdowns: one for creating logs and one for filtering logs

**Backend:**
- The `/agents` endpoint retrieves agents based on:
  - User ID (personal agents)
  - Company ID (if a filter is applied)
- The backend fetches data from the `agents` table

### 2. Create a New Agent Log

**Frontend:**
1. User selects an agent from the dropdown
2. User fills out the form with:
   - Token counts (input, output, embedding)
   - Pricing information
   - Model details (protocol, temperature)
   - Feature flags (media input/output, memory usage, tool usage)
   - Chat history in JSON format
3. User submits the form by clicking "Create Log"
4. The `createAgentLog()` function sends a POST request to `/agent-logs`

**Backend:**
1. The POST `/agent-logs` endpoint receives the request
2. Validates user permissions based on ownership and role
3. Verifies that the agent exists
4. Inserts a new record into the `agent_logs` table
5. Returns the created log data

### 3. View Agent Logs

**Frontend:**
1. User selects an agent from the filter dropdown
2. The `loadAgentLogs()` function sends a GET request to `/agent-logs/agent/{agent_id}`
3. Results are displayed in a table showing:
   - Log ID
   - Date
   - Token counts
   - Pricing
   - Action buttons (View, Delete)

**Backend:**
1. The GET `/agent-logs/agent/{agent_id}` endpoint receives the request
2. Validates user permissions for the specified agent
3. Retrieves all logs for the agent from the database
4. Returns the log data sorted by date (newest first)

### 4. View Log Details

**Frontend:**
1. User clicks the "View" button for a specific log
2. The `loadLogDetails()` function sends a GET request to `/agent-logs/{agent_id}`
3. Detailed information is displayed, including:
   - Agent information
   - Token counts and pricing
   - Model details
   - Feature flags
   - Chat history in a conversation-like format
   - JSON representation of the entire log

**Backend:**
1. The GET `/agent-logs/{agent_id}` endpoint receives the request
2. Validates user permissions for the specified agent
3. Retrieves the most recent log for the agent
4. Returns the complete log data

### 5. Delete Agent Logs

**Frontend:**
1. User clicks the "Delete" button for a specific log
2. The user is prompted for confirmation
3. The `deleteLog()` function sends a DELETE request to `/agent-logs/{agent_id}`

**Backend:**
1. The DELETE `/agent-logs/{agent_id}` endpoint receives the request
2. Validates user permissions (ensuring the user has appropriate access)
3. Deletes all logs for the specified agent
4. Returns a success message

## Data Requirements

### Core Data Entities

1. **Agent Log Data**:
   - `agent_id`: Reference to the associated agent (UUID)
   - `input_token`: Count of tokens used in agent input (integer)
   - `output_token`: Count of tokens generated in output (integer)
   - `embedding_token`: Count of tokens used for embeddings (integer)
   - `pricing`: Cost of the agent execution (decimal)
   - `chat_history`: Complete conversation history (JSON array)
   - `model_protocol`: LLM protocol used (string)
   - `model_temperature`: Temperature setting for randomness (decimal)
   - `media_input`: Whether media was included in input (boolean)
   - `media_output`: Whether media was included in output (boolean)
   - `use_memory`: Whether agent used memory features (boolean)
   - `use_tool`: Whether agent used tools (boolean)
   - `date`: Timestamp of the log creation (datetime, auto-generated)
   - `agent_log_id`: Unique identifier for each log (integer, auto-generated)

2. **Chat History Data**:
   The chat history can be structured in two ways:

   **Individual Messages Format**:
   - An array of message objects with:
     - `role`: Speaker role, either "user" or "assistant" (string)
     - `content`: Message content (string)
     - `thread_id`: Optional thread identifier (string)

   **Thread-Based Format**:
   - An array of thread objects with:
     - `thread_id`: Thread identifier (string)
     - `messages`: Array of message objects with:
       - `role`: Speaker role (string)
       - `content`: Message content (string)

3. **Agent Reference Data**:
   - `agent_id`: Unique identifier (UUID)
   - `agent_name`: Name of the agent (string)
   - `company_id`: Optional association with a company (UUID)
   - `user_id`: Owner of the agent (UUID)

### Database Tables & Relationships

The microservice relies on the following database tables:

- `agent_logs`: Stores log data for agent executions
- `agents`: Stores agent information (referenced by agent_id)
- `user_companies`: Maps users to companies with roles
- `roles`: Defines role permissions
- `users`: Stores user information

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent-logs` | POST | Create a new agent log |
| `/agent-logs/agent/{agent_id}` | GET | Get all logs for a specific agent |
| `/agent-logs/{agent_id}` | GET | Get the most recent log for an agent |
| `/agent-logs/{agent_id}` | DELETE | Delete all logs for an agent |
| `/agents` | GET | Get all agents (filtered by user or company) |

## Data Validation

The backend implements robust validation for incoming data:

1. **Token Counts**:
   - Must be non-negative integers
   - Used for tracking resource usage and pricing

2. **Pricing**:
   - Must be a decimal with up to 10 digits and 4 decimal places
   - Represents the cost of agent execution

3. **Model Temperature**:
   - Must be a decimal between 0 and 1
   - Controls randomness in agent responses

4. **Chat History**:
   - Must be a valid JSON array
   - Frontend provides a helpful default template

## Access Control

The microservice implements the following access control rules:

1. **Agent Owner Access**:
   - The user who created the agent has full access to its logs

2. **Company Access**:
   - Users within the same company can access logs for company agents
   - Deletion requires admin or write role permissions

3. **Permission Verification**:
   - Each endpoint verifies the user has appropriate access to the agent
   - Company-level permissions are verified through role assignments

## UI Components

1. **Log Creation Form**:
   - Agent selection dropdown
   - Numeric inputs for token counts and pricing
   - Text fields for model information
   - Checkboxes for feature flags
   - Text area for JSON chat history with a default template

2. **Log Listing Table**:
   - Sortable by date (newest first)
   - Shows key metrics (token counts, pricing)
   - Action buttons for viewing and deleting logs

3. **Log Details View**:
   - Token and pricing information in a card layout
   - Model information and feature flags
   - Chat history displayed in a conversational format
   - Thread filtering dropdown for multi-threaded conversations
   - Raw JSON representation for debugging 