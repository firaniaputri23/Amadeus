# Agent Management MCP Server Documentation

This document provides a comprehensive overview of the Agent Management MCP (Model Context Protocol) Server, which provides tools for creating, managing, and configuring AI agents through MCP protocol integration.

## Table of Contents

1. [Overview](#overview)
2. [Required Infrastructure](#required-infrastructure)
3. [MCP Tools](#mcp-tools)
   - [Agent Management](#agent-management)
   - [Tool Management](#tool-management)
   - [Agent-Tool Associations](#agent-tool-associations)
4. [Authentication](#authentication)
5. [Error Handling](#error-handling)
6. [Usage Examples](#usage-examples)

## Overview

The Agent Management MCP Server provides a set of tools that can be used by MCP clients to:

1. Create new agents in the system
2. Retrieve and manage tools
3. Assign tools to agents
4. Remove tool assignments from agents
5. Query agent-tool relationships

This MCP server acts as a bridge between MCP clients and the FastAPI backend, providing a standardized interface for agent management operations.

## Required Infrastructure

The Agent Management MCP Server requires the following infrastructure:

1. **FastAPI Backend** running at the configured base URL (default: `https://boilerplate-agent.dev.chiswarm.ai`)
2. **Authentication System** that provides Bearer tokens for API access
3. **Database Backend** (via FastAPI) with the following entities:
   - Agents
   - Tools
   - Agent-Tool associations
   - Companies (optional)

## MCP Tools

### Agent Management

#### `create_new_agent`

Creates a new agent in the system.

**Parameters:**
- `auth_token` (str): Bearer token for FastAPI backend authentication
- `agent_name` (str): The name of the agent
- `description` (str, optional): A description for the agent
- `agent_style` (str, optional): The style of the agent (e.g., "formal", "casual")
- `on_status` (bool, optional): Whether the agent is active (default: True)
- `tools` (List[UUID], optional): List of tool UUIDs to associate with the agent
- `company_id` (UUID, optional): The UUID of the company the agent belongs to

**Returns:**
- Dictionary containing the details of the newly created agent
- Error dictionary if the operation fails

**Example:**
```python
result = await create_new_agent(
    auth_token="your_bearer_token",
    agent_name="Customer Support Agent",
    description="Handles customer inquiries and support requests",
    agent_style="professional",
    on_status=True,
    tools=["tool-uuid-1", "tool-uuid-2"],
    company_id="company-uuid"
)
```

### Tool Management

#### `get_tools`

Retrieves all tools from the system.

**Parameters:**
- `auth_token` (str): Bearer token for FastAPI backend authentication
- `company_id` (UUID, optional): Optional company ID to filter tools by company

**Returns:**
- Dictionary containing a list of tools
- Error dictionary if the operation fails

**Example:**
```python
result = await get_tools(
    auth_token="your_bearer_token",
    company_id="company-uuid"  # optional
)
```

#### `get_tool`

Retrieves a specific tool by its ID.

**Parameters:**
- `auth_token` (str): Bearer token for FastAPI backend authentication
- `tool_id` (UUID): The UUID of the tool to retrieve

**Returns:**
- Dictionary containing the tool details
- Error dictionary if the operation fails

**Example:**
```python
result = await get_tool(
    auth_token="your_bearer_token",
    tool_id="tool-uuid"
)
```

### Agent-Tool Associations

#### `assign_tool_to_agent`

Assigns a tool to an agent.

**Parameters:**
- `auth_token` (str): Bearer token for FastAPI backend authentication
- `agent_id` (int): The ID of the agent to assign the tool to
- `tool_id` (int): The ID of the tool to assign

**Returns:**
- Dictionary containing the assignment details
- Error dictionary if the operation fails

**Example:**
```python
result = await assign_tool_to_agent(
    auth_token="your_bearer_token",
    agent_id=123,
    tool_id=456
)
```

#### `get_agent_tools`

Retrieves all tools assigned to a specific agent.

**Parameters:**
- `auth_token` (str): Bearer token for FastAPI backend authentication
- `agent_id` (int): The ID of the agent to get tools for

**Returns:**
- Dictionary containing a list of tools assigned to the agent
- Error dictionary if the operation fails

**Example:**
```python
result = await get_agent_tools(
    auth_token="your_bearer_token",
    agent_id=123
)
```

#### `remove_tool_from_agent`

Removes a tool assignment from an agent.

**Parameters:**
- `auth_token` (str): Bearer token for FastAPI backend authentication
- `agent_id` (int): The ID of the agent to remove the tool from
- `tool_id` (int): The ID of the tool to remove

**Returns:**
- Dictionary containing the success message
- Error dictionary if the operation fails

**Example:**
```python
result = await remove_tool_from_agent(
    auth_token="your_bearer_token",
    agent_id=123,
    tool_id=456
)
```

## Authentication

All MCP tools require authentication via Bearer tokens:

1. **Token Format**: Bearer tokens are passed as the `auth_token` parameter
2. **Token Usage**: Tokens are included in HTTP headers as `Authorization: Bearer {token}`
3. **Token Source**: Tokens should be obtained from your authentication system

## Error Handling

All MCP tools implement comprehensive error handling:

### Error Types

1. **Request Errors**: Network-related issues when communicating with the FastAPI backend
2. **HTTP Status Errors**: 4xx/5xx responses from the FastAPI backend
3. **Unexpected Errors**: Any other exceptions that occur during execution

### Error Response Format

All errors are returned as dictionaries with an `error` key:

```python
{
    "error": "Error description here"
}
```

### Common Error Scenarios

- **Authentication Failures**: Invalid or expired auth tokens
- **Not Found**: Requesting non-existent agents or tools
- **Validation Errors**: Invalid UUIDs or missing required parameters
- **Permission Errors**: Insufficient permissions for the requested operation

## Usage Examples

### Complete Agent Creation Workflow

```python
# 1. Get available tools
tools_result = await get_tools(auth_token="your_token")
if "error" not in tools_result:
    available_tools = tools_result["tools"]
    
    # 2. Select relevant tools (example: first two tools)
    selected_tool_ids = [tool["id"] for tool in available_tools[:2]]
    
    # 3. Create agent with selected tools
    agent_result = await create_new_agent(
        auth_token="your_token",
        agent_name="Multi-Tool Agent",
        description="Agent with multiple capabilities",
        tools=selected_tool_ids
    )
    
    if "error" not in agent_result:
        print(f"Agent created successfully: {agent_result}")
    else:
        print(f"Error creating agent: {agent_result['error']}")
```

### Tool Management Workflow

```python
# 1. Get specific tool details
tool_result = await get_tool(
    auth_token="your_token",
    tool_id="specific-tool-uuid"
)

# 2. Assign tool to existing agent
if "error" not in tool_result:
    assignment_result = await assign_tool_to_agent(
        auth_token="your_token",
        agent_id=123,
        tool_id=456
    )
    
    # 3. Verify assignment
    agent_tools = await get_agent_tools(
        auth_token="your_token",
        agent_id=123
    )
    
    print(f"Agent tools: {agent_tools}")
```

## Running the MCP Server

To run the MCP server:

```bash
python app_mcp_agent.py
```

The server runs with stdio transport and can be integrated with any MCP-compatible client.

## Configuration

### Base URL Configuration

The FastAPI base URL is configured at the top of the file:

```python
FASTAPI_BASE_URL = "https://boilerplate-agent.dev.chiswarm.ai"
```

Update this URL to match your FastAPI backend deployment.

## Integration Notes

1. **UUID Handling**: The server automatically converts UUID objects to strings when making API calls
2. **Async Operations**: All tools are async and use httpx for HTTP requests
3. **Error Propagation**: Errors from the FastAPI backend are properly propagated to MCP clients
4. **Type Safety**: Full type hints are provided for all parameters and return values