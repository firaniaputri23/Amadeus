"""
Tools Router

This module provides routes for tool management.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4
from supabase import Client
import socket, json, os, time
from dotenv import load_dotenv

from microservice.agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ValidationError,
)

# Pydantic models for request and response
class VersionReleased(BaseModel):
    env: Dict[str, str] = {}
    args: str = ""
    port: str = ""
    method: str = "sse"
    required_env: List[str] = []

class ToolVersion(BaseModel):
    version: str
    released: VersionReleased

class ToolBase(BaseModel):
    """Base model for tools with methods to convert to dict."""
    name: str
    description: Optional[str] = None
    versions: List[ToolVersion] = []
    on_status: Optional[str] = "Online"

class ToolCreate(ToolBase):
    """
    Tool creation model with default version if none is provided.
    """
    company_id: Optional[UUID] = None
    on_status: Optional[str] = "Online"

    @validator('versions', pre=True, always=True)
    def set_default_version(cls, versions):
        if not versions:
            # Create a default version if none is provided
            return [
                {
                    "version": "1.0.0",
                    "released": {
                        "env": {},
                        "args": "",
                        "port": "10001",
                        "method": "sse",
                        "required_env": []
                    }
                }
            ]
        return versions

class ToolResponse(BaseModel):
    """Response model for tools."""
    tool_id: UUID
    name: str
    description: Optional[str] = None
    versions: List[Dict[str, Any]] = []
    on_status: Optional[str] = "Online"
    company_id: Optional[UUID] = None

# Create router
router = APIRouter(
    prefix="/tools",
    tags=["tools"],
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# Helper function to check write permissions
def check_write_permission(role_name: str):
    if role_name not in ['super admin', 'admin', 'staff']:
        raise HTTPException(status_code=403, detail="You don't have permission to perform this action")

# Function to retrieve available port
# Cache for port configuration and used ports
_port_config = None
_used_ports_cache = None
_last_used_ports_check = 0
_used_ports_cache_ttl = 30  # Cache TTL in seconds

def _load_port_config():
    """Load port configuration from environment variables and config file."""
    global _port_config
    
    # Return cached config if available
    if _port_config is not None:
        return _port_config
        
    # Load environment variables
    load_dotenv()
    
    # Default values
    host = "127.0.0.1"
    start_port = 10_000
    end_port = 11_999
    
    # Try to get port range from config file first
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    config_path = os.path.join(root_dir, 'config', 'port_range.json')
    
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            
        host = config.get('host', host)
        start_port = config.get('start_port', start_port)
        end_port = config.get('end_port', end_port)
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading config file: {e}, using default values")
    
    # Override with environment variables if provided
    if os.getenv("MCP_HOST"):
        host = os.getenv("MCP_HOST")
    if os.getenv("MCP_START_PORT"):
        try:
            start_port = int(os.getenv("MCP_START_PORT"))
        except ValueError:
            print(f"Invalid MCP_START_PORT value: {os.getenv('MCP_START_PORT')}, using {start_port}")
    if os.getenv("MCP_END_PORT"):
        try:
            end_port = int(os.getenv("MCP_END_PORT"))
        except ValueError:
            print(f"Invalid MCP_END_PORT value: {os.getenv('MCP_END_PORT')}, using {end_port}")
    
    # Cache the config
    _port_config = {
        "host": host,
        "start_port": start_port,
        "end_port": end_port,
        "port_range": range(start_port, end_port + 1)
    }
    
    print(f"Loaded port configuration: {host}:{start_port}-{end_port}")
    return _port_config

def get_free_port():
    """Get a free port that's not in use by the system or already assigned to a tool."""
    global _used_ports_cache, _last_used_ports_check
    
    # Load port configuration
    config = _load_port_config()
    host = config["host"]
    port_range = config["port_range"]
    
    current_time = time.time()
    
    # Check if we need to refresh the used ports cache
    if _used_ports_cache is None or (current_time - _last_used_ports_check) > _used_ports_cache_ttl:
        # Get all ports already assigned in Supabase
        _used_ports_cache = set()
        try:
            from ..utils._get_tools_supabase import get_all_tools
            tools = get_all_tools()
            
            for tool in tools:
                if 'versions' in tool and tool['versions']:
                    for version in tool['versions']:
                        if 'released' in version and version['released']:
                            port = version['released'].get('port', '')
                            if port:
                                try:
                                    port_int = int(port)
                                    # Only add to used_ports if it's within our range
                                    if port_int in port_range:
                                        _used_ports_cache.add(port_int)
                                    else:
                                        print(f"Warning: Port {port} for tool {tool.get('name', 'unknown')} is outside configured range")
                                except (ValueError, TypeError):
                                    print(f"Warning: Invalid port value: {port} for tool {tool.get('name', 'unknown')}")
            
            _last_used_ports_check = current_time
            print(f"Updated used ports cache with {len(_used_ports_cache)} ports")
        except Exception as e:
            print(f"Error getting used ports from Supabase: {e}")
            # If we have a cache, keep using it even if it's expired
            if _used_ports_cache is None:
                _used_ports_cache = set()
    
    # Use the cached used ports
    used_ports = _used_ports_cache
    
    # Try to find a free port that's not in use by the system or already assigned
    # Create a list of candidate ports (those not in used_ports)
    candidate_ports = [port for port in port_range if port not in used_ports]
    
    # If we have too many candidates, sample a subset to speed up checking
    if len(candidate_ports) > 100:
        import random
        # Try a random sample of 100 ports first
        sample_size = min(100, len(candidate_ports))
        sampled_ports = random.sample(candidate_ports, sample_size)
        # Add some ports from the beginning, middle and end of the range for better distribution
        sampled_ports.extend([candidate_ports[0],
                             candidate_ports[len(candidate_ports)//2],
                             candidate_ports[-1]])
        candidate_ports = sampled_ports
    
    # Try each candidate port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for port in candidate_ports:
        try:
            s.bind((host, port))
            free_port = s.getsockname()[1]
            s.close()
            
            # Double-check the port is within our range
            if free_port not in port_range:
                print(f"Warning: System assigned port {free_port} is outside our range")
                continue
                
            print(f"Found free port: {free_port}")
            return str(free_port)
        except socket.error:
            # Port is in use by the system, try next one
            continue
    
    # If we get here, no free ports were found in our sample
    # Try a full scan as a last resort
    if len(candidate_ports) < len(port_range):
        print("Trying full port range scan as a last resort...")
        remaining_ports = [p for p in port_range if p not in candidate_ports and p not in used_ports]
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for port in remaining_ports:
            try:
                s.bind((host, port))
                free_port = s.getsockname()[1]
                s.close()
                
                print(f"Found free port in full scan: {free_port}")
                return str(free_port)
            except socket.error:
                continue
    
    # If we get here, no free ports were found
    print("WARNING: No free ports available in the configured range!")
    return None

# CRUD operations
@router.post("/", response_model=ToolResponse, description="""
Create a new tool with the specified name, description, and versions.

Example request body:
```json
{
  "name": "example_tool",
  "description": "An example tool",
  "versions": [
    {
      "version": "1.0.0",
      "released": {
        "env": {
          "API_KEY": "your-api-key"
        },
        "args": "uvx mcp-server-fetch",
        "port": "10001",
        "method": "sse",
        "required_env": [
          "API_KEY"
        ]
      }
    }
  ],
  "on_status": "Online"
}
```
""")
async def create_tool(
    tool: ToolCreate, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # If company_id is provided, check user permission in that company
        if tool.company_id:
            user_company_response = (
                supabase.table("user_companies")
                .select("role_id")
                .eq("user_id", user_id)
                .eq("company_id", str(tool.company_id))
                .execute()
            )
            
            if not user_company_response.data:
                raise HTTPException(status_code=403, detail="You don't have access to this company")

            role_id = user_company_response.data[0]["role_id"]

            role_response = (
                supabase.table("roles")
                .select("role_name")
                .eq("role_id", role_id)
                .execute()
            )

            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise HTTPException(status_code=403, detail="You don't have permission to create tools for this company")
            
        # Check if a tool with the same name already exists
        name_check_response = (
            supabase.table("tools")
            .select("tool_id")
            .eq("name", tool.name)
            .execute()
        )
        
        if name_check_response.data:
            raise HTTPException(status_code=400, detail="A tool with this name already exists")
        
        # Convert versions to dict for Supabase
        versions_dict = []
        for version in tool.versions:
            version_data = version.dict()
            version_data["released"]["port"] = get_free_port() 
            versions_dict.append(version_data)
        
        # Insert tool into database
        print(f"Versions: {versions_dict}")

        insert_data = {
            "user_id": str(user_id),
            "company_id": str(tool.company_id) if tool.company_id else None,
            "name": tool.name,
            "description": tool.description,
            "versions": versions_dict,
            "on_status": tool.on_status
        }

        response = (
            supabase.table("tools")
            .insert(insert_data)
            .execute()
        )
        
        # Check if insert was successful
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create tool")
        
        # Refresh MCP tools after creating a new tool
        from .mcp_tools import refresh_tools
        try:
            await refresh_tools()
        except Exception as e:
            print(f"Warning: Failed to refresh MCP tools after creating a new tool: {e}")
        
        # Return the data as is (already in dict format from Supabase)
        return response.data[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/", response_model=List[ToolResponse])
async def get_tools(
    request: Request, 
    company_id: Optional[UUID] = Query(None, description="Company ID (optional)"),
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Build query
        query = supabase.table("tools_with_decrypted_keys").select("*")

        if company_id:
            # If company_id is provided, only filter by company_id
            query = query.eq("company_id", str(company_id))
        else:
            # Otherwise, filter by user_id
            user_id = request.state.user_id
            query = query.eq("user_id", user_id)

        # Execute query
        try:
            response = query.execute()
        except Exception as e:
            raise InternalServerError(f"Error fetching agents: {str(e)}")
        
        return response.data
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    # Get tool by ID
    response = (
        supabase.table("tools_with_decrypted_keys")
        .select("*")
        .eq("tool_id", str(tool_id))
        .execute()
    )
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Return the data as is (already in dict format from Supabase)
    return response.data[0]

@router.put("/{tool_id}", response_model=ToolResponse, description="""
Update an existing tool with the specified name, description, and versions.

Example request body:
```json
{
  "name": "updated_tool",
  "description": "An updated tool",
  "versions": [
    {
      "version": "1.0.0",
      "released": {
        "env": {
          "API_KEY": "your-api-key",
          "DEBUG": "true"
        },
        "args": "uvx mcp-server-fetch",
        "port": "10001",
        "method": "sse",
        "required_env": [
          "API_KEY"
        ]
      }
    }
  ],
  "on_status": "Online"
}
```
""")
async def update_tool(
    tool_id: UUID, 
    tool: ToolCreate, 
    request: Request, 
    company_id: Optional[UUID] = Query(None, description="Company ID (optional)"),
    supabase: Client = Depends(get_supabase_client)
):
    # If company_id is provided, check if user has write access
    if company_id:
        if request.state.role_name not in ['super admin', 'admin', 'staff']:
            raise HTTPException(status_code=403, detail="You don't have permission to update tools for this company")
    
    # Check if a tool with the same name already exists (excluding this tool)
    name_check_response = (
        supabase.table("tools")
        .select("tool_id")
        .eq("name", tool.name)
        .neq("tool_id", str(tool_id))
        .execute()
    )
    
    if name_check_response.data:
        raise HTTPException(status_code=400, detail="A tool with this name already exists")
    
    # Convert versions to dict for Supabase
    versions_dict = [version.dict() for version in tool.versions]
    
    # Update tool
    response = (
        supabase.table("tools")
        .update({
            "name": tool.name,
            "description": tool.description,
            "versions": versions_dict,
            "on_status": tool.on_status
        })
        .eq("tool_id", str(tool_id))
        .execute()
    )
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Refresh MCP tools after updating a tool
    from .mcp_tools import refresh_tools
    try:
        await refresh_tools()
    except Exception as e:
        print(f"Warning: Failed to refresh MCP tools after updating a tool: {e}")
    
    # Return the data as is (already in dict format from Supabase)
    return response.data[0]

@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: UUID, 
    request: Request, 
    company_id: Optional[UUID] = Query(None, description="Company ID (optional)"),
    supabase: Client = Depends(get_supabase_client)
):
    # If company_id is provided, check if user has admin access
    if company_id:
        if request.state.role_name not in ['super admin', 'admin']:
            raise HTTPException(status_code=403, detail="You don't have permission to delete tools for this company")
    
    # Check if the tool is used by any agents
    agents_response = (
        supabase.table("agents")
        .select("agent_id, agent_name")
        .contains("tools", [str(tool_id)])
        .execute()
    )
    
    if agents_response.data:
        agent_names = [agent["agent_name"] for agent in agents_response.data]
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete tool as it is used by the following agents: {', '.join(agent_names)}"
        )
    
    # Delete tool
    response = (
        supabase.table("tools")
        .delete()
        .eq("tool_id", str(tool_id))
        .execute()
    )
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Refresh MCP tools after deleting a tool
    from .mcp_tools import refresh_tools
    try:
        await refresh_tools()
    except Exception as e:
        print(f"Warning: Failed to refresh MCP tools after deleting a tool: {e}")
    
    return {"message": "Tool deleted successfully"}

@router.get("/check-name/{tool_name}", description="Check if a tool name already exists")
async def check_tool_name(
    tool_name: str,
    request: Request,
    tool_id: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Check if a tool name already exists in the database.
    
    Args:
        tool_name: The name to check
        tool_id: Optional tool ID to exclude from the check (for update operations)
        
    Returns:
        A dictionary with exists field indicating if the name exists
    """
    # Query the database for tools with the same name
    query = (
        supabase.table("tools")
        .select("tool_id")
        .eq("name", tool_name)
    )
    
    # If tool_id is provided, exclude it from the check
    if tool_id:
        try:
            uuid_obj = UUID(tool_id)
            query = query.neq("tool_id", str(uuid_obj))
        except ValueError:
            pass  # Invalid UUID, ignore
    
    # Execute the query
    response = query.execute()
    
    # Return whether the name exists
    return {"exists": len(response.data) > 0}

# Clone tool endpoint
@router.post("/{tool_id}/clone", response_model=ToolResponse)
async def clone_tool(
    tool_id: UUID, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    """
    Clone an existing tool with a new ID and name prefixed with 'Clone of'.
    
    Args:
        tool_id: The ID of the tool to clone
        company_id: Optional company ID for the cloned tool
        
    Returns:
        The newly created tool
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the existing tool to clone
        existing_tool_response = (
            supabase.table("tools")
            .select("*")
            .eq("tool_id", str(tool_id))
            .execute()
        )
        
        if not existing_tool_response.data:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        existing_tool = existing_tool_response.data[0]
        company_id = existing_tool.get("company_id")

        # Check if user has access to the company
        if company_id:
            user_company_response = (
                supabase.table("user_companies")
                .select("role_id")
                .eq("user_id", user_id)
                .eq("company_id", company_id)
                .execute()
            )

            if not user_company_response.data:
                raise HTTPException(status_code=403, detail="You don't have access to this company")

            role_id = user_company_response.data[0]["role_id"]

            role_response = (
                supabase.table("roles")
                .select("role_name")
                .eq("role_id", role_id)
                .execute()
            )

            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise HTTPException(status_code=403, detail="You don't have permission to clone tools for this company")

        # Generate new name with auto-increment if needed
        base_name = f"Clone of {existing_tool['name']}"
        clone_name = base_name
        count = 1
        
        while True:
            name_check_response = (
                supabase.table("tools")
                .select("tool_id")
                .eq("name", clone_name)
                .execute()
            )
            if not name_check_response.data:
                break
            count += 1
            clone_name = f"{base_name} ({count})"

        # Clone versions with new port numbers
        cloned_versions = []
        if existing_tool.get("versions"):
            for version in existing_tool["versions"]:
                version_data = version.copy()
                if "released" in version_data and version_data["released"]:
                    # Get a new port for the cloned version
                    version_data["released"]["port"] = get_free_port()
                    
                    # Replace credential values in environment variables with placeholders
                    if "env" in version_data["released"] and isinstance(version_data["released"]["env"], dict):
                        for key in version_data["released"]["env"]:
                            # Replace the actual value with a placeholder
                            version_data["released"]["env"][key] = "[Insert Your ENV]"
                
                cloned_versions.append(version_data)

        # Create the cloned tool
        clone_data = {
            "name": clone_name,
            "description": existing_tool.get("description"),
            "versions": cloned_versions,
            "company_id": company_id,
            "user_id": user_id,
            "on_status": existing_tool.get("on_status", "Online")
        }

        # Insert cloned tool into database
        response = (
            supabase.table("tools")
            .insert(clone_data)
            .execute()
        )

        # Check if insert was successful
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to clone tool")
        
        # Refresh MCP tools after creating the clone
        from .mcp_tools import refresh_tools
        try:
            await refresh_tools()
        except Exception as e:
            print(f"Warning: Failed to refresh MCP tools after cloning a tool: {e}")
        
        # Return the newly created tool
        return response.data[0]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")