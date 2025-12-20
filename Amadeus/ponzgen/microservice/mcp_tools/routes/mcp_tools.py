"""
MCP Tools Router

This module provides routes for MCP tools management.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os

from supabase import create_client, Client
from dotenv import load_dotenv

from ..utils._get_tools_supabase import get_all_tools
from ..utils._mcp_manager import MCPProxyManager
from ..utils._tool_args_converter import tool_args_converter
from .tools import get_free_port
# Import the check_after_adding function
try:
    from ..utils._check_tools_status import check_after_adding
except ImportError:
    # Define a fallback if import fails
    def check_after_adding():
        print("Warning: check_after_adding function not available")
from ..utils._check_tools_status import check_after_adding

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create router
router = APIRouter(
    prefix="/mcp-tools",
    tags=["mcp-tools"],
)

# Initialize the MCP manager
manager = MCPProxyManager()

# Response models
class StandardResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any] = None

# @router.post("/refresh", response_model=StandardResponse)
# Cache for tools to reduce Supabase calls - declare as global variables
# These need to be global to persist between function calls
_tools_cache = None
_last_cache_time = 0
_cache_ttl = 60  # Cache TTL in seconds

@router.get("/refresh", response_model=StandardResponse)
async def refresh_tools(force_refresh: bool = False):
    """
    Endpoint to refresh MCP tools.
    
    This endpoint:
    1. Gets all tools from Supabase
    2. Updates the MCP manager with the tools
    3. Returns the result of the update process
    
    Args:
        force_refresh: If True, bypass cache and force a refresh from Supabase
    """
    import time
    try:
        # Declare that we're using global variables
        global _tools_cache, _last_cache_time, _cache_ttl
        current_time = time.time()
        
        # Use cached data if available and not forced to refresh
        if not force_refresh and _tools_cache is not None and (current_time - _last_cache_time) < _cache_ttl:
            print(f"Using cached tools ({len(_tools_cache)} tools)")
            tools = _tools_cache
        else:
            # Get all tools from Supabase
            print("Fetching tools from Supabase...")
            tools = get_all_tools()
            
            # Update cache
            _tools_cache = tools
            _last_cache_time = current_time

        print(f"Processing {len(tools)} tools")
        
        # Filter out tools with specific offline statuses but preserve original statuses
        active_tools = []
        offline_tools = []
        
        for tool in tools:
            status = tool.get('on_status', '')
            if status == "Offline":
                offline_tools.append(tool)
            elif status == "Predefined":
                offline_tools.append(tool)
            else:
                active_tools.append(tool)
        
        print(f"After filtering, {len(active_tools)} active tools remain")
        
        # Track tools that need to be updated in Supabase
        tools_to_update = []
        
        # First, collect all used ports to check for duplicates
        used_ports = {}  # port -> [tool_ids]
        
        # Check each active tool for a port and track used ports
        for tool in active_tools:
            tool_name = tool.get('name', 'unknown')
            tool_id = tool.get('tool_id')
            
            if 'versions' in tool and tool['versions']:
                for version_index, version in enumerate(tool['versions']):
                    if 'released' in version and version['released']:
                        port = version['released'].get('port', '')
                        
                        if port:
                            if port not in used_ports:
                                used_ports[port] = []
                            used_ports[port].append({
                                'tool_id': tool_id,
                                'tool_name': tool_name,
                                'version_index': version_index
                            })
        
        # Check for duplicate ports and assign new ones
        for port, tools_with_port in used_ports.items():
            if len(tools_with_port) > 1:
                print(f"Found duplicate port {port} used by {len(tools_with_port)} tools")
                
                # Keep the first tool with this port, reassign others
                for i, tool_info in enumerate(tools_with_port):
                    if i == 0:
                        # Keep the first tool's port
                        continue
                    
                    # Find the tool in active_tools
                    for tool in active_tools:
                        if tool.get('tool_id') == tool_info['tool_id']:
                            # Assign a new port within the valid range
                            new_port = get_free_port()
                            version_index = tool_info['version_index']
                            
                            if new_port:
                                print(f"Reassigning port for tool {tool_info['tool_name']} from {port} to {new_port}")
                                
                                # Update the port in the tool's version
                                tool['versions'][version_index]['released']['port'] = new_port
                            else:
                                print(f"WARNING: Could not find a free port for tool {tool_info['tool_name']}. Port remains {port}")
                            
                            # Add to update list
                            tools_to_update.append({
                                "tool_id": tool_info['tool_id'],
                                "versions": tool['versions']
                            })
                            break
        
        # Now check for missing ports and assign them
        for tool in active_tools:
            tool_name = tool.get('name', 'unknown')
            tool_id = tool.get('tool_id')
                        
            port_updated = False
            
            if 'versions' in tool and tool['versions']:
                for version_index, version in enumerate(tool['versions']):
                    if 'released' in version and version['released']:
                        if 'port' in version['released'] and not version['released']['port']:
                            new_port = get_free_port()
                            if new_port:
                                version['released']['port'] = new_port
                                port_updated = True
                            else:
                                print(f"WARNING: Could not find a free port for tool {tool_name}. Port remains empty.")
                     
            # If a port was updated, add this tool to the list to update in Supabase
            if port_updated and tool_id and not any(update['tool_id'] == tool_id for update in tools_to_update):
                tools_to_update.append({
                    "tool_id": tool_id,
                    "versions": tool['versions']
                })
        
        # Update tools in Supabase if any ports were changed
        if tools_to_update:
            print(f"Updating {len(tools_to_update)} tools in Supabase with new port values")
            
            # Break updates into smaller batches to avoid timeouts
            batch_size = 5  # Process 5 tools at a time
            for i in range(0, len(tools_to_update), batch_size):
                batch = tools_to_update[i:i+batch_size]
                print(f"Processing batch {i//batch_size + 1} of {(len(tools_to_update) + batch_size - 1) // batch_size}")
                
                for tool_data in batch:
                    max_retries = 3
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            supabase.table("tools").update(
                                {"versions": tool_data["versions"]}
                            ).eq("tool_id", tool_data["tool_id"]).execute()
                            print(f"Updated tool {tool_data['tool_id']} in Supabase")
                            break  # Success, exit retry loop
                        except Exception as e:
                            retry_count += 1
                            if "timeout" in str(e).lower() and retry_count < max_retries:
                                print(f"Timeout updating tool {tool_data['tool_id']}, retrying ({retry_count}/{max_retries})...")
                                import time
                                time.sleep(1)  # Wait before retrying
                            else:
                                print(f"Error updating tool {tool_data['tool_id']} in Supabase: {str(e)}")
                                break  # Non-timeout error or max retries reached
        
        # Update the MCP manager with only the active tools
        arr_dict_tools_cmd = tool_args_converter(active_tools)
        result = manager.update_tools(arr_dict_tools_cmd)
        
        # Run an immediate check after updating tools in a non-blocking way
        try:
            # Use a separate thread to avoid blocking the API response
            def trigger_check():
                try:
                    check_after_adding()
                    print("Immediate status check triggered after tool refresh")
                except Exception as e:
                    print(f"Error running immediate status check: {e}")
            
            import threading
            check_thread = threading.Thread(target=trigger_check)
            check_thread.daemon = True
            check_thread.start()
        except Exception as e:
            print(f"Error scheduling immediate status check: {e}")
            
        return StandardResponse(
            status="success",
            message="Tools refreshed successfully",
            data={
                "total_tools": len(tools),
                "active_tools": len(active_tools),
                "offline_tools": len(offline_tools),
                "tools_updated_in_supabase": len(tools_to_update),
                "update_result": result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=StandardResponse)
async def get_status():
    """Get the status of running MCP processes."""
    try:
        # Create a dictionary to store status information
        status_info = {}
        
        # Check each process
        for port, process in manager._processes.items():
            is_running = manager._is_port_in_use(port)
            status_info[port] = {
                "running": is_running,
                "command": manager._commands.get(port, "Unknown")
            }
        
        return StandardResponse(
            status="success",
            message="Status retrieved successfully",
            data={
                "processes": status_info,
                "count": len(status_info)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))