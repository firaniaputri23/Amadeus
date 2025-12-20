# In your MCP server.py file

import httpx
from mcp.server.fastmcp import FastMCP
from typing import List, Optional, Dict, Any
from uuid import UUID # For type hinting UUIDs

import os

# Initialize your MCP server
mcp = FastMCP("Agent Management Tools")

# Assuming your FastAPI application is running at this base URL
FASTAPI_BASE_URL = "https://boilerplate-agent.dev.chiswarm.ai" # Adjust this to your actual FastAPI URL

@mcp.tool()
async def create_new_agent(
    auth_token: str, # This token would be for your FastAPI backend
    agent_name: str,
    description: Optional[str] = None,
    agent_style: Optional[str] = None,
    on_status: Optional[bool] = True,
    tools: Optional[List[UUID]] = None, # List of tool UUIDs
    company_id: Optional[UUID] = None # Optional company ID
    # You'll need a way to pass the authentication token.
    # This is a simplified example; in a real scenario, you might``
    # get this from an environment variable or a more secure context.
    
) -> dict:
    """
    Creates a new agent in the system.

    Args:
        agent_name: The name of the agent.
        description: A description for the agent.
        agent_style: The style of the agent (e.g., "formal", "casual").
        on_status: Whether the agent is active.
        tools: A list of UUIDs for tools associated with the agent.
        company_id: The UUID of the company the agent belongs to (if any).
        auth_token: The authentication token for the FastAPI backend.

    Returns:
        A dictionary containing the details of the newly created agent, or an error message.
    """
    endpoint = f"{FASTAPI_BASE_URL}/agents/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}" # Assuming Bearer token authentication
    }
    payload = {
        "agent_name": agent_name,
        "description": description,
        "agent_style": agent_style,
        "on_status": on_status,
        "tools": [str(t) for t in tools] if tools else [], # Convert UUIDs to strings
        "company_id": str(company_id) if company_id else None # Convert UUID to string
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            return response.json()
    except httpx.RequestError as exc:
        return {"error": f"An error occurred while requesting {exc.request.url!r}: {exc}"}
    except httpx.HTTPStatusError as exc:
        return {"error": f"Error response {exc.response.status_code} from {exc.request.url!r}: {exc.response.text}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

# Tools CRUD Operations

@mcp.tool()
async def get_tools(
    auth_token: str,
    company_id: Optional[UUID] = None
) -> dict:
    """
    Retrieves all tools from the system.

    Args:
        auth_token: The authentication token for the FastAPI backend.
        company_id: Optional company ID to filter tools by company.

    Returns:
        A dictionary containing a list of tools, or an error message.
    """
    endpoint = f"{FASTAPI_BASE_URL}/tools/"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    
    params = {}
    if company_id:
        params["company_id"] = str(company_id)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            return {"tools": response.json()}
    except httpx.RequestError as exc:
        return {"error": f"An error occurred while requesting {exc.request.url!r}: {exc}"}
    except httpx.HTTPStatusError as exc:
        return {"error": f"Error response {exc.response.status_code} from {exc.request.url!r}: {exc.response.text}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_tool(
    auth_token: str,
    tool_id: UUID
) -> dict:
    """
    Retrieves a specific tool by its ID.

    Args:
        auth_token: The authentication token for the FastAPI backend.
        tool_id: The UUID of the tool to retrieve.

    Returns:
        A dictionary containing the tool details, or an error message.
    """
    endpoint = f"{FASTAPI_BASE_URL}/tools/{tool_id}"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as exc:
        return {"error": f"An error occurred while requesting {exc.request.url!r}: {exc}"}
    except httpx.HTTPStatusError as exc:
        return {"error": f"Error response {exc.response.status_code} from {exc.request.url!r}: {exc.response.text}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

# Agent-Tools Management Operations

@mcp.tool()
async def assign_tool_to_agent(
    auth_token: str,
    agent_id: int,
    tool_id: int
) -> dict:
    """
    Assigns a tool to an agent.

    Args:
        auth_token: The authentication token for the FastAPI backend.
        agent_id: The ID of the agent to assign the tool to.
        tool_id: The ID of the tool to assign.

    Returns:
        A dictionary containing the assignment details, or an error message.
    """
    endpoint = f"{FASTAPI_BASE_URL}/agent-tools/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    payload = {
        "agent_id": agent_id,
        "tool_id": tool_id
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as exc:
        return {"error": f"An error occurred while requesting {exc.request.url!r}: {exc}"}
    except httpx.HTTPStatusError as exc:
        return {"error": f"Error response {exc.response.status_code} from {exc.request.url!r}: {exc.response.text}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_agent_tools(
    auth_token: str,
    agent_id: int
) -> dict:
    """
    Retrieves all tools assigned to a specific agent.

    Args:
        auth_token: The authentication token for the FastAPI backend.
        agent_id: The ID of the agent to get tools for.

    Returns:
        A dictionary containing a list of tools assigned to the agent, or an error message.
    """
    endpoint = f"{FASTAPI_BASE_URL}/agent-tools/agent/{agent_id}/tools"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            return {"agent_tools": response.json()}
    except httpx.RequestError as exc:
        return {"error": f"An error occurred while requesting {exc.request.url!r}: {exc}"}
    except httpx.HTTPStatusError as exc:
        return {"error": f"Error response {exc.response.status_code} from {exc.request.url!r}: {exc.response.text}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def remove_tool_from_agent(
    auth_token: str,
    agent_id: int,
    tool_id: int
) -> dict:
    """
    Removes a tool assignment from an agent.

    Args:
        auth_token: The authentication token for the FastAPI backend.
        agent_id: The ID of the agent to remove the tool from.
        tool_id: The ID of the tool to remove.

    Returns:
        A dictionary containing the success message, or an error message.
    """
    endpoint = f"{FASTAPI_BASE_URL}/agent-tools/{agent_id}/{tool_id}"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(endpoint, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as exc:
        return {"error": f"An error occurred while requesting {exc.request.url!r}: {exc}"}
    except httpx.HTTPStatusError as exc:
        return {"error": f"Error response {exc.response.status_code} from {exc.request.url!r}: {exc.response.text}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

# You would define similar tools for get_agents, get_agent, update_agent, delete_agent, etc.

if __name__ == "__main__":
    mcp.run(transport='stdio')