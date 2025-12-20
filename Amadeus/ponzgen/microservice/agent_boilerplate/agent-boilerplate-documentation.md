# Agent Boilerplate Microservice Documentation

This document provides a comprehensive overview of the Agent Boilerplate microservice, which serves as the foundation for creating, managing, and invoking AI agents within the system.

## Table of Contents

1. [Overview](#overview)
2. [Required Infrastructure](#required-infrastructure)
3. [Components](#components)
   - [Boilerplate](#boilerplate)
   - [Routes](#routes)
4. [API Routes](#api-routes)
   - [Agent Invoke API](#agent-invoke-api)
   - [Agent API](#agent-api)
5. [Data Models](#data-models)
6. [Agent Invocation Flow](#agent-invocation-flow)
7. [Tool Integration](#tool-integration)
8. [Memory Management](#memory-management)

## Overview

The Agent Boilerplate microservice provides a framework for:

1. Managing agent configurations in Supabase PostgreSQL
2. Dynamically routing agent invocations
3. Handling agent memory and conversation state
4. Integrating with tools via MCP (Model Context Protocol)
5. Supporting multiple LLM providers

It abstracts the complexity of agent management and invocation, providing a consistent interface for applications to interact with AI agents.

## Required Infrastructure

The Agent Boilerplate microservice requires the following infrastructure:

1. **Supabase Database** with the following tables:
   - `agents`: Stores agent configurations
   - `tools`: Stores tool configurations
   - `agent_logs`: Stores logs of agent interactions
   - `user_companies`: Maps users to companies
   - `companies`: Stores company information
   - `roles`: Stores role information
   - `users`: Stores user information

2. **Environment Variables**:
   - `SUPABASE_URL`: URL for the Supabase instance
   - `SUPABASE_KEY`: API key for Supabase
   - Various LLM provider API keys depending on configuration

3. **External Services**:
   - MCP (Model Context Protocol) for tool integration
   - LLM providers (OpenAI, OpenRouter, etc.)

## Components

### Boilerplate

The core components of the Agent Boilerplate are located in the `boilerplate` directory:

#### `agent_boilerplate.py`

The primary class that handles:
- Agent creation and configuration loading
- Memory management (conversation history)
- Input parsing and formatting
- Agent invocation with configurable model selection
- Tool integration via MCP
- Logging agent interactions to Supabase

**Key Functions:**
- `get_or_create_memory`: Manages agent conversation memory
- `reset_memory`: Clears an agent's conversation history
- `parse_agent_input`: Processes input for the agent
- `_parse_tools`: Extracts tool configurations
- `_log_interaction`: Records agent interactions in the database
- `invoke_agent`: Main method to run an agent with given input
- `invoke_agent_stream`: Streaming version of agent invocation

#### `agent_templates/react_agent.py`

Implements the React agent pattern using LangChain:
- Agent creation with ReAct pattern
- Tool integration via LangChain tools
- Memory handling for conversation context

#### `models.py`

Defines Pydantic models for:
- Agent input structure
- Configuration parameters
- Metadata for agent invocation
- Tool configuration

#### `errors.py`

Provides standardized error handling for the API:
- Custom error classes for different HTTP status codes
- Structured error responses
- Error handling utilities

### Routes

The API routes for the Agent Boilerplate are defined in the `routes` directory:

#### `agent_invoke.py`

Routes for invoking agents and accessing agent information:
- `POST /agent-invoke/{agent_id}/invoke`: Run an agent
- `POST /agent-invoke/{agent_id}/invoke-stream`: Run an agent with streaming response
- `GET /agent-invoke/{agent_id}/info`: Get agent information
- `GET /agent-invoke/shared-agent/{agent_hash}`: Access a shared agent
- `GET /agent-invoke/shared-thread/{thread_hash}`: Access a shared conversation thread

#### `agent_api.py`

Routes for agent management:
- `GET /agent-api/agents`: List available agents
- `GET /agent-api/agents/{agent_id}`: Get agent details
- `GET /agent-api/get-llms`: Get available LLM models (not implemented in the provided code)

## API Routes

### Agent Invoke API

#### `POST /agent-invoke/{agent_id}/invoke`

Invoke an agent by its agent_id.

**Path Parameters:**
- `agent_id` (string): ID of the agent to invoke

**Request Body:**
- `input`: Object containing agent input
  - `messages` (string): The query or message for the agent
  - `context` (string, optional): Additional context
- `config`: Configuration object
  - `configurable` (object): Key-value pairs for configuration
    - `thread_id` (string): Conversation thread ID
- `metadata`: Metadata for the invocation
  - `model_name` (string): LLM model to use (e.g., "gpt-4")
  - `reset_memory` (boolean): Whether to reset the conversation memory
  - `load_from_json` (boolean): Legacy parameter
  - `agent_style` (string): Additional agent instructions
- `agent_config` (object, optional): Full agent configuration (if not provided, fetched from database)

**Authentication Requirements:**
- Valid user authentication
- Must have access to the agent (owner or company member)

**Responses:**
- `200`: Agent response
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

#### `POST /agent-invoke/{agent_id}/invoke-stream`

Invoke an agent with streaming response.

**Parameters:** Same as non-streaming version

**Responses:**
- Streaming response with agent output
- Error responses same as non-streaming version

#### `GET /agent-invoke/{agent_id}/info`

Get information about an agent.

**Path Parameters:**
- `agent_id` (string): ID of the agent

**Authentication Requirements:**
- Valid user authentication
- Must have access to the agent

**Responses:**
- `200`: Agent information
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

### Agent API

#### `GET /agent-api/agents`

Get all agents available to the current user.

**Authentication Requirements:**
- Valid user authentication

**Responses:**
- `200`: List of available agents
- `500`: Internal server error

#### `GET /agent-api/agents/{agent_id}`

Get detailed information about an agent.

**Path Parameters:**
- `agent_id` (UUID): ID of the agent

**Authentication Requirements:**
- Valid user authentication
- Must have access to the agent

**Responses:**
- `200`: Agent details including tools
- `403`: Forbidden (insufficient permissions)
- `404`: Agent not found
- `500`: Internal server error

## Data Models

### AgentInput

The primary data model for agent invocation:

```python
class AgentInput(BaseModel):
    """Input for agent invocation."""
    input: AgentInputMessage
    config: AgentInputConfig = Field(default_factory=AgentInputConfig)
    metadata: AgentInputMetadata = Field(default_factory=AgentInputMetadata)
    agent_config: Optional[Dict[str, Any]] = None
```

Where:
- `AgentInputMessage`: Contains the user messages and context
- `AgentInputConfig`: Contains configurable parameters (thread_id, etc.)
- `AgentInputMetadata`: Contains model selection and memory options
- `agent_config`: Optional full agent configuration

## Agent Invocation Flow

The agent invocation process follows these steps:

1. **Request Validation**:
   - Validate the incoming request against the AgentInput model
   - Check if the request includes a complete agent_config

2. **Authorization**:
   - Verify the user has access to the requested agent
   - Check permissions based on ownership or company membership

3. **Agent Configuration**:
   - If agent_config is provided, use it directly
   - Otherwise, fetch the agent configuration from the database

4. **Tool Integration**:
   - Parse tool configurations from the agent_config
   - Set up connections to the required MCP tool services

5. **Memory Management**:
   - Get or create a memory instance for the agent
   - Reset memory if requested in the metadata

6. **Input Processing**:
   - Parse the agent input into a format suitable for the LLM
   - Include agent style, context, and other configuration

7. **Agent Invocation**:
   - Create the appropriate agent using the template
   - Invoke the agent with the processed input
   - Handle streaming responses if requested

8. **Logging**:
   - Record the interaction in the agent_logs table
   - Track token usage, pricing, and other metrics

9. **Response Formatting**:
   - Format the agent's response for the client
   - Include any additional metadata

## Tool Integration

Agents can be configured to use tools via MCP (Model Context Protocol):

1. **Tool Configuration**:
   - Tools are defined in the Supabase database
   - Each tool has a name, description, and versions
   - The latest released version is used for invocation

2. **MCP Connection**:
   - The agent boilerplate connects to tool services via MCP
   - Each tool service runs on its own port
   - Communication happens via SSE (Server-Sent Events)

3. **Tool Execution**:
   - The agent can execute tools during invocation
   - Tool results are incorporated into the agent's context
   - Tools can access shared environment variables

## Memory Management

Each agent has its own conversation memory:

1. **Memory Creation**:
   - Memory is created for each agent on first invocation
   - Memory is stored in the `agent_memories` dictionary

2. **Memory Persistence**:
   - Memory persists across invocations using the same agent_id
   - Thread_id can be used to separate different conversations

3. **Memory Reset**:
   - Memory can be reset using the `reset_memory` flag
   - This starts a new conversation with no history

4. **Memory Integration**:
   - Memory is integrated with the agent using MemorySaver
   - This allows the agent to reference previous messages
   - Memory is used to provide continuity in conversations 