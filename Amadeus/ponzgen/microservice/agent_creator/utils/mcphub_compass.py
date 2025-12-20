"""
MCPHUB Compass Utility

This module provides async utilities for interacting with the MCP Compass API
to get server/tool recommendations based on agent descriptions.
"""

import json
import urllib.parse
import aiohttp
import sys
from typing import Dict, List, Any, Optional

COMPASS_API_BASE = "https://registry.mcphub.io"

async def make_compass_request(query: str) -> List[Dict[str, Any]]:
    """
    Makes an async request to the MCP Compass API to get server recommendations.
    
    Args:
        query: Description of the MCP Server needed
        
    Returns:
        A list of recommended MCP servers
    """
    try:
        url = f"{COMPASS_API_BASE}/recommend?description={urllib.parse.quote(query)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Error from COMPASS API: Status {response.status}", file=sys.stderr)
                    return []
                data = await response.json()
                return data
    except Exception as error:
        print(f"Error fetching from COMPASS API: {error}", file=sys.stderr)
        return []

def _to_servers_text(servers: List[Dict[str, Any]]) -> str:
    """
    Formats a list of server data into readable text.
    
    Args:
        servers: List of server data from the MCP Compass API
        
    Returns:
        Formatted text representation of the servers
    """
    if not servers:
        return "No MCP servers found."

    result = []
    for i, server in enumerate(servers):
        # Handle missing keys gracefully
        title = server.get('title', 'No title available')
        description = server.get('description', 'No description available')
        github_url = server.get('github_url', 'No GitHub URL available')
        
        # Handle missing similarity or different format
        try:
            if 'similarity' in server:
                similarity_percentage = f"{server['similarity'] * 100:.1f}"
            else:
                similarity_percentage = "N/A"
        except (TypeError, ValueError):
            similarity_percentage = str(server.get('similarity', 'N/A'))
        
        server_text = [
            f"Server {i + 1}:",
            f"Title: {title}",
            f"Description: {description}",
            f"GitHub URL: {github_url}",
            f"Similarity: {similarity_percentage}%",
            ""
        ]
        result.append("\n".join(server_text))
    
    return "\n".join(result)

def _format_server_for_frontend(servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Formats server data from the MCP Compass API to match frontend expectations.
    
    Args:
        servers: List of server data from the MCP Compass API
        
    Returns:
        List of formatted server objects for frontend consumption
    """
    if not servers:
        return []
    
    formatted_servers = []
    for server in servers:
        # Extract the relevant fields
        title = server.get('title', '')
        description = server.get('description', '')
        github_url = server.get('github_url', '')
        
        # Create formatted server object
        formatted_server = {
            "name": title,
            "description": description,
            "url": github_url
        }
        
        # Add similarity if available
        if 'similarity' in server:
            try:
                formatted_server["similarity"] = float(server['similarity'])
            except (TypeError, ValueError):
                formatted_server["similarity"] = 0.0
        
        formatted_servers.append(formatted_server)
    
    return formatted_servers

async def get_recommended_tools(agent_name: str = "", agent_description: str = "", keywords: List[str] = None) -> List[Dict[str, Any]]:
    """
    Gets recommended MCP tools based on keywords.
    
    Args:
        agent_name: Name of the agent (kept for backward compatibility)
        agent_description: Description of the agent (kept for backward compatibility)
        keywords: List of keywords to use for tool recommendations
        
    Returns:
        List of recommended tools formatted for the frontend
    """
    # Only use keywords for the query
    if not keywords:
        keywords = ["automation", "helper", "assistant"]  # Default keywords if none provided
    
    # Join keywords with spaces for better semantic matching
    query = " ".join(keywords)
    
    # Make request to COMPASS API
    servers = await make_compass_request(query)
    
    # Format servers for frontend
    return _format_server_for_frontend(servers) 