# Agents Microservice Flow

## Overview

The Agents Microservice provides functionality for creating and managing AI agents in the system. This document explains the application flow from the frontend UI through to the backend API and details the data requirements for the microservice.

## Application Components

1. **Frontend UI (`agents.html`)**
   - Provides the HTML structure for the agents management interface
   - Contains modals for creating, editing, and cloning agents
   - Includes interfaces for tool assignment

2. **Frontend Logic (`agents.js`)**
   - Handles all client-side interactions and API calls
   - Manages agent data rendering and form handling
   - Provides tool management functionality

3. **Backend API (`agents.py`)**
   - Provides RESTful endpoints for agent operations
   - Handles database interactions and business logic
   - Manages relationships between agents and tools

## User Flow

### 1. View Agents List

**Frontend:**
- On page load, the frontend automatically calls `loadAgents()` function
- The function makes a GET request to the `/agents` endpoint
- Results are displayed in a grid of cards with basic agent information
- Users can filter agents by company using the dropdown

**Backend:**
- The `/agents` endpoint retrieves agents based on:
  - User ID (personal agents)
  - Company ID (if a filter is applied)
- The backend fetches data from the `agents` table

### 2. View Agent Details

**Frontend:**
- When a user clicks the "View" button on an agent card, the `loadAgentDetails()` function is called
- This makes a GET request to `/agents/{agent_id}`
- Agent details are displayed including basic information
- The `loadAgentTools()` function is also called to display the agent's tools

**Backend:**
- The `/agents/{agent_id}` endpoint retrieves the full details of a specific agent
- It also fetches tool details for each tool assigned to the agent
- Data is fetched from the `agents` table and `tools_with_decrypted_keys` table

### 3. Create New Agent

**Frontend:**
1. User clicks "Create Agent" button, opening the agent modal
2. User fills out the form with:
   - Agent name
   - Description
   - Agent style (with optional autofill)
   - Status (active/inactive)
   - Company (optional)
   - Tools selection
3. User clicks "Save" to submit the form
4. The `saveAgent()` function sends a POST request to `/agents`

**Backend:**
1. The POST `/agents` endpoint receives the request
2. Validates user permissions for the company if specified
3. Verifies that all selected tools exist
4. Inserts the new agent into the database
5. Returns the created agent data

### 4. Edit Agent

**Frontend:**
1. User clicks "Edit" button on an agent card
2. The `editAgent()` function fetches the agent details
3. The agent modal is populated with the existing agent data
4. User makes changes and clicks "Save"
5. The `saveAgent()` function sends a PUT request to `/agents/{agent_id}`

**Backend:**
1. The PUT `/agents/{agent_id}` endpoint receives the request
2. Validates user permissions based on ownership and role
3. Updates the agent in the database
4. Returns the updated agent data

### 5. Delete Agent

**Frontend:**
1. User clicks "Delete" button on an agent card
2. A confirmation dialog is shown
3. If confirmed, the `deleteAgent()` function sends a DELETE request to `/agents/{agent_id}`

**Backend:**
1. The DELETE `/agents/{agent_id}` endpoint receives the request
2. Validates user permissions based on ownership and role
3. Deletes the agent from the database
4. Returns a success message

### 6. Clone Agent

**Frontend:**
1. User clicks "Clone" button, opening the clone agent modal
2. Available agents are displayed for selection
3. User selects an agent and clicks "Clone"
4. The `cloneSelectedAgent()` function sends a POST request to `/agents/{agent_id}/clone`

**Backend:**
1. The POST `/agents/{agent_id}/clone` endpoint receives the request
2. Verifies user permissions
3. Creates a copy of the agent with:
   - Name prefixed with "Clone of"
   - Same tools, description, and settings
4. Inserts the cloned agent into the database
5. Returns the cloned agent data

### 7. Manage Agent Tools

**Frontend:**
1. **Add Tool:**
   - User clicks "Add Tool" button when viewing an agent
   - Available tools (not already assigned) are displayed
   - User selects a tool and clicks "Add"
   - The `addToolToAgent()` function sends a POST request to `/agents/{agent_id}/tools/{tool_id}`

2. **Remove Tool:**
   - User clicks "Remove" button on a tool card
   - A confirmation dialog is shown
   - If confirmed, the `removeToolFromAgent()` function sends a DELETE request to `/agents/{agent_id}/tools/{tool_id}`

**Backend:**
1. The tool management endpoints handle adding/removing tools from agents
2. Validate user permissions based on ownership and role
3. Update the agent's tool list in the database
4. Return success messages

## Authentication Flow

The application uses a middleware-based authentication system:

1. JWT token is extracted from the Authorization header
2. Token is validated against Supabase (or a static file in development)
3. User information is added to the request state
4. Permissions are checked based on user role and company association

## Data Requirements

### Core Data Entities

1. **Agent Data**:
   - `agent_id`: Unique identifier for each agent (UUID)
   - `agent_name`: Name of the agent (string)
   - `description`: Optional description (string)
   - `agent_style`: Style/personality configuration (string)
   - `on_status`: Active status flag (boolean)
   - `tools`: Array of tool IDs (UUID[])
   - `company_id`: Optional association with a company (UUID)
   - `user_id`: Owner of the agent (UUID)
   - `created_at`: Timestamp when the agent was created

2. **Tool Data**:
   - `tool_id`: Unique identifier for each tool (UUID)
   - `name`: Tool name
   - `description`: Optional tool description
   - `versions`: Array of version configurations
   - Tool details are fetched from `tools_with_decrypted_keys` view

3. **User Data**:
   - `user_id`: Unique identifier
   - Authentication information (JWT)
   - Permissions

4. **Company Data**:
   - `company_id`: Unique identifier
   - `name`: Company name
   - User-company relationships
   - Role information for access control

5. **Role Data**:
   - `role_id`: Unique identifier
   - `role_name`: Name of the role (e.g., "super admin", "admin", "staff")
   - Associated permissions

### Database Tables & Relationships

The microservice relies on the following database tables:

- `agents`: Stores agent information
- `tools`: Stores tool information
- `tools_with_decrypted_keys`: View with decrypted environment variables
- `user_companies`: Maps users to companies with roles
- `roles`: Defines available roles and permissions

### Agent-Tool Relationship

- Agents can have multiple tools assigned to them
- The `tools` field in the agent record contains an array of tool IDs
- The relationship is managed through specific endpoints for adding/removing tools

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents` | GET | Get all agents (filtered by user or company) |
| `/agents` | POST | Create a new agent |
| `/agents/{agent_id}` | GET | Get a specific agent by ID with tool details |
| `/agents/{agent_id}` | PUT | Update an existing agent |
| `/agents/{agent_id}` | DELETE | Delete an agent |
| `/agents/{agent_id}/tools/{tool_id}` | POST | Add a tool to an agent |
| `/agents/{agent_id}/tools/{tool_id}` | DELETE | Remove a tool from an agent |
| `/agents/{agent_id}/tools` | GET | Get all tools assigned to an agent |
| `/agents/{agent_id}/clone` | POST | Clone an existing agent |

## Special Features

### Agent Style Autofill

The frontend includes functionality to automatically generate agent style descriptions:

1. User clicks the "magic wand" icon next to the style field
2. The `autofillAgentStyle()` function uses the agent name and description
3. A request is sent to `/agent_field_autofill/invoke` endpoint
4. The response is used to populate the style field with a smooth typing animation

## Error Handling

- The backend uses standardized error responses defined in the error module
- Specific error types include: `BadRequestError`, `NotFoundError`, `ForbiddenError`, `InternalServerError`
- The frontend shows error notifications to users when API calls fail 