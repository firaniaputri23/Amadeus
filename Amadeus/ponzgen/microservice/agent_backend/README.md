# Agent Backend Service

This directory contains the Agent Backend service for managing agents, companies, roles, and agent logs in Supabase PostgreSQL.

## Overview

The Agent Backend service provides API endpoints for:

1. Managing agents (CRUD operations)
2. Managing companies (CRUD operations)
3. Managing roles (CRUD operations)
4. Managing agent logs (CRUD operations)

## Components

### routes/agents.py

Provides API endpoints for managing agents:

- Creating new agents
- Retrieving agent information
- Updating existing agents
- Deleting agents

Agents are stored in Supabase PostgreSQL and include:
- Basic information (name, description)
- Route path for invocation
- Associated company
- Tool configurations
- Status (active/inactive)

### routes/companies.py

Provides API endpoints for managing companies:

- Creating new companies
- Retrieving company information
- Updating existing companies
- Deleting companies

Companies are used for organizing agents and controlling access permissions.

### routes/roles.py

Provides API endpoints for managing roles:

- Creating new roles
- Retrieving role information
- Updating existing roles
- Deleting roles

Roles are used for controlling access to agents and other resources. The system includes predefined roles such as:
- Super Admin
- Admin
- Staff
- User

### routes/agent_logs.py

Provides API endpoints for managing agent logs:

- Creating new logs
- Retrieving log information
- Querying logs by agent, user, or time period

Agent logs record interactions with agents, including:
- Input messages
- Agent responses
- Timestamps
- User information
- Error information (if applicable)

## API Endpoints

### Agent Management

- `POST /agents` - Create a new agent
- `GET /agents` - Get all agents
- `GET /agents/{agent_id}` - Get a specific agent
- `PUT /agents/{agent_id}` - Update an agent
- `DELETE /agents/{agent_id}` - Delete an agent

### Company Management

- `POST /companies` - Create a new company
- `GET /companies` - Get all companies
- `GET /companies/{company_id}` - Get a specific company
- `PUT /companies/{company_id}` - Update a company
- `DELETE /companies/{company_id}` - Delete a company

### Role Management

- `POST /roles` - Create a new role
- `GET /roles` - Get all roles
- `GET /roles/{role_id}` - Get a specific role
- `PUT /roles/{role_id}` - Update a role
- `DELETE /roles/{role_id}` - Delete a role

### Agent Log Management

- `POST /agent-logs` - Create a new log entry
- `GET /agent-logs` - Get all logs
- `GET /agent-logs/{log_id}` - Get a specific log
- `GET /agent-logs/agent/{agent_id}` - Get logs for a specific agent
- `GET /agent-logs/user/{user_id}` - Get logs for a specific user

## Authentication and Authorization

The Agent Backend service integrates with the authentication middleware to:

1. Verify that the user is authenticated
2. Check if the user has the appropriate role to perform the requested action
3. Enforce role-based access control for company-specific resources

## Database Schema

The service uses the following tables in Supabase PostgreSQL:

- `agents` - Stores agent configurations
- `companies` - Stores company information
- `roles` - Stores role definitions
- `agent_logs` - Stores agent interaction logs
- `users` - Stores user information (managed by Supabase Auth)

## Integration with Other Services

The Agent Backend service provides the data that is used by:

1. The Agent Boilerplate service for agent invocation
2. The MCP Tools service for tool management
3. The Website Tester service for UI testing

## Example Usage

### Creating a New Agent

```http
POST /agents
Content-Type: application/json

{
  "agent_name": "Customer Support Agent",
  "description": "An agent for handling customer support inquiries",
  "route_path": "customer-support",
  "company_id": "123e4567-e89b-12d3-a456-426614174000",
  "agent_style": "helpful and friendly",
  "on_status": true,
  "tools": ["tool-id-1", "tool-id-2"]
}
```

### Creating a New Company

```http
POST /companies
Content-Type: application/json

{
  "company_name": "Acme Corporation",
  "description": "A fictional company",
  "website": "https://acme.example.com",
  "logo_url": "https://acme.example.com/logo.png"
}
```

### Creating a New Role

```http
POST /roles
Content-Type: application/json

{
  "role_name": "Support Staff",
  "description": "Staff members who handle customer support",
  "permissions": ["read:agents", "invoke:agents", "read:logs"]
}
```

### Creating a New Log Entry

```http
POST /agent-logs
Content-Type: application/json

{
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "456e7890-e12b-34d5-a678-426614174000",
  "input": "How do I reset my password?",
  "response": "You can reset your password by clicking on the 'Forgot Password' link on the login page.",
  "status": "success",
  "metadata": {
    "model_name": "gpt-4",
    "tokens_used": 150
  }
}