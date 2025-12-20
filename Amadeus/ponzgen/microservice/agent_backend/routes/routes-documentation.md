# Agent Backend API Routes Documentation

This document provides an overview of the API routes available in the agent_backend microservice.

## Table of Contents

1. [Overview](#overview)
2. [Required Infrastructure](#required-infrastructure)
3. [Agents API](#agents-api)
4. [Companies API](#companies-api)
5. [Roles API](#roles-api)
6. [Agent Logs API](#agent-logs-api)
7. [Agent Tools API](#agent-tools-api)

## Overview

The agent_backend microservice provides a set of RESTful API endpoints for managing agents, companies, roles, and related resources. The API is built using FastAPI and interacts with a Supabase database for data storage and retrieval.

## Required Infrastructure

These routes require the following infrastructure and data dependencies:

1. **Supabase Database** with the following tables:
   - `agents`
   - `companies`
   - `roles`
   - `agent_logs`
   - `tools`
   - `user_companies`
   - `agent_tool`
   - `tool_collection`
   - `agent_collection`

2. **Authentication System** that provides:
   - Authentication tokens
   - User identification
   - Role-based access control

3. **Error Handling Module** for consistent error responses

## Agents API

Endpoints for managing agents.

### Routes

#### `POST /agents/`
Create a new agent.

**Request Body:**
- `agent_name` (string): Name of the agent
- `description` (string, optional): Description of the agent
- `agent_style` (string, optional): Style/behavior of the agent
- `on_status` (boolean, optional): Active status of the agent
- `tools` (array of UUIDs, optional): List of tool IDs to associate with the agent
- `company_id` (UUID, optional): Company ID if the agent belongs to a company

**Authentication Requirements:**
- Valid user authentication
- If company_id is provided, user must have staff, admin, or super admin role in that company

**Responses:**
- `200`: Agent created successfully
- `400`: Bad request (invalid data)
- `403`: Forbidden (insufficient permissions)
- `500`: Internal server error

#### `GET /agents/`
Get a list of agents.

**Query Parameters:**
- `company_id` (UUID, optional): Filter agents by company ID

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: List of agents
- `500`: Internal server error

#### `GET /agents/{agent_id}`
Get a specific agent by ID.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent to retrieve

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent or have access to the company the agent belongs to

**Responses:**
- `200`: Agent details
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `PUT /agents/{agent_id}`
Update an existing agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent to update

**Request Body:** Same as for `POST /agents/`

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent or have write permission in the company the agent belongs to

**Responses:**
- `200`: Updated agent details
- `400`: Bad request (invalid data)
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `DELETE /agents/{agent_id}`
Delete an agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent to delete

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent or have admin permissions in the company the agent belongs to

**Responses:**
- `200`: Agent deleted successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `POST /agents/{agent_id}/tools/{tool_id}`
Add a tool to an agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent
- `tool_id` (UUID): ID of the tool to add

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent or have write permission in the company

**Responses:**
- `200`: Tool added successfully
- `400`: Bad request (tool already added or invalid data)
- `403`: Forbidden (insufficient permissions)
- `404`: Agent or tool not found
- `500`: Internal server error

#### `DELETE /agents/{agent_id}/tools/{tool_id}`
Remove a tool from an agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent
- `tool_id` (UUID): ID of the tool to remove

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent or have write permission in the company

**Responses:**
- `200`: Tool removed successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Agent, tool, or relationship not found
- `500`: Internal server error

#### `GET /agents/{agent_id}/tools`
Get all tools associated with an agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent or have access to the company

**Responses:**
- `200`: List of tools
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `POST /agents/{agent_id}/clone`
Clone an existing agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent to clone

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent or have access to the company

**Responses:**
- `200`: Cloned agent details
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

## Companies API

Endpoints for managing companies.

### Routes

#### `POST /companies/`
Create a new company.

**Request Body:**
- `name` (string): Name of the company
- `description` (string, optional): Description of the company

**Authentication Requirements:**
- Valid user authentication
- Must be a super admin in the "Predefined" company

**Responses:**
- `200`: Company created successfully
- `403`: Forbidden (insufficient permissions)
- `500`: Internal server error

#### `GET /companies/`
Get a list of companies.

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: List of companies the user has access to
- `500`: Internal server error

#### `GET /companies/{company_id}`
Get details of a specific company.

**Path Parameters:**
- `company_id` (UUID): ID of the company to retrieve

**Authentication Requirements:**
- Valid user authentication
- Must have access to the company

**Responses:**
- `200`: Company details
- `403`: Forbidden (insufficient permissions)
- `404`: Company not found
- `500`: Internal server error

#### `PUT /companies/{company_id}`
Update a company.

**Path Parameters:**
- `company_id` (UUID): ID of the company to update

**Request Body:**
- `name` (string): Name of the company
- `description` (string, optional): Description of the company

**Authentication Requirements:**
- Valid user authentication
- Must have admin role in the company

**Responses:**
- `200`: Updated company details
- `403`: Forbidden (insufficient permissions)
- `404`: Company not found
- `500`: Internal server error

#### `DELETE /companies/{company_id}`
Delete a company.

**Path Parameters:**
- `company_id` (UUID): ID of the company to delete

**Authentication Requirements:**
- Valid user authentication
- Must be a super admin in the company

**Responses:**
- `200`: Company deleted successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Company not found
- `500`: Internal server error

#### `GET /companies/{company_id}/users`
Get users associated with a company.

**Path Parameters:**
- `company_id` (UUID): ID of the company

**Authentication Requirements:**
- Valid user authentication
- Must have access to the company

**Responses:**
- `200`: List of users in the company
- `403`: Forbidden (insufficient permissions)
- `404`: Company not found
- `500`: Internal server error

#### `POST /companies/{company_id}/users`
Add a user to a company.

**Path Parameters:**
- `company_id` (UUID): ID of the company

**Request Body:**
- `user_id` (UUID): ID of the user to add
- `role_id` (integer): Role ID for the user

**Authentication Requirements:**
- Valid user authentication
- Must have admin role in the company

**Responses:**
- `200`: User added to company successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Company or user not found
- `500`: Internal server error

#### `DELETE /companies/{company_id}/users/{user_id_to_remove}`
Remove a user from a company.

**Path Parameters:**
- `company_id` (UUID): ID of the company
- `user_id_to_remove` (UUID): ID of the user to remove

**Authentication Requirements:**
- Valid user authentication
- Must have admin role in the company

**Responses:**
- `200`: User removed from company successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Company, user, or relationship not found
- `500`: Internal server error

## Roles API

Endpoints for managing roles.

### Routes

#### `GET /roles/`
Get a list of all roles.

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: List of roles
- `500`: Internal server error

#### `GET /roles/{role_id}`
Get a specific role by ID.

**Path Parameters:**
- `role_id` (integer): ID of the role to retrieve

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: Role details
- `404`: Role not found
- `500`: Internal server error

### System Initialization

The roles module includes a function `initialize_roles` that creates default roles if they don't exist:

- "super admin"
- "admin"
- "staff"
- "guest"

## Agent Logs API

Endpoints for managing agent logs.

### Routes

#### `POST /agent-logs/`
Create a new agent log.

**Request Body:**
- `agent_id` (UUID): ID of the agent
- `input_token` (integer): Number of input tokens
- `output_token` (integer): Number of output tokens
- `embedding_token` (integer): Number of embedding tokens
- `pricing` (decimal): Price calculated for the interaction
- `chat_history` (array): Conversation history
- `model_protocol` (string, optional): AI model protocol used
- `model_temperature` (decimal, optional): Temperature setting for the model (0-1)
- `media_input` (boolean): Whether media was used in input
- `media_output` (boolean): Whether media was generated in output
- `use_memory` (boolean): Whether memory was used
- `use_tool` (boolean): Whether tools were used

**Authentication Requirements:**
- Valid user authentication
- Must have access to the agent

**Responses:**
- `200`: Log created successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `GET /agent-logs/agent/{agent_id}`
Get logs for a specific agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent

**Authentication Requirements:**
- Valid user authentication
- Must have access to the agent

**Responses:**
- `200`: List of agent logs
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `GET /agent-logs/{agent_id}`
Get a specific agent log by ID.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent log

**Authentication Requirements:**
- Valid user authentication
- Must have access to the associated agent

**Responses:**
- `200`: Agent log details
- `403`: Forbidden (insufficient permissions)
- `404`: Agent log not found
- `500`: Internal server error

#### `DELETE /agent-logs/{agent_id}`
Delete an agent log.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent log to delete

**Authentication Requirements:**
- Valid user authentication
- Must have access to the associated agent

**Responses:**
- `200`: Agent log deleted successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Agent log not found
- `500`: Internal server error

## Agent Tools API

Endpoints for managing relationships between agents and tools.

### Routes

#### `POST /agent-tools/`
Assign a tool to an agent.

**Request Body:**
- `agent_id` (integer): ID of the agent
- `tool_id` (integer): ID of the tool

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent

**Responses:**
- `200`: Tool assigned successfully
- `400`: Bad request (tool already assigned)
- `403`: Forbidden (insufficient permissions)
- `404`: Agent or tool not found
- `500`: Internal server error

#### `GET /agent-tools/agent/{agent_id}/tools`
Get all tools assigned to an agent.

**Path Parameters:**
- `agent_id` (integer): ID of the agent

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent

**Responses:**
- `200`: List of tools
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `DELETE /agent-tools/{agent_id}/{tool_id}`
Remove a tool from an agent.

**Path Parameters:**
- `agent_id` (integer): ID of the agent
- `tool_id` (integer): ID of the tool

**Authentication Requirements:**
- Valid user authentication
- Must be the owner of the agent

**Responses:**
- `200`: Tool removed successfully
- `403`: Forbidden (insufficient permissions)
- `404`: Agent, tool, or relationship not found
- `500`: Internal server error 