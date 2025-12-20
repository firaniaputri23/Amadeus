"""
Agent API Router

This module provides routes for agent API endpoints.
"""

from fastapi import APIRouter, Request, Depends
from typing import Dict, Any, List
from uuid import UUID
from supabase import Client

from ..boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ERROR_RESPONSES
)

# Create router
router = APIRouter(
    prefix="/agent-api",
    tags=["agent-api"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase


@router.get("/agents", response_model=List[Dict[str, Any]])
async def get_available_agents(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get all agents available to the current user.
    
    This endpoint returns all agents that the user has access to,
    including personal agents and agents from companies the user belongs to.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get all personal agents for the user
        try:
            personal_agents_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("user_id", user_id)
                .eq("on_status", True)
                .is_("company_id", "null")
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching personal agents: {str(e)}")
        
        personal_agents = personal_agents_response.data
        
        # Get all companies the user belongs to
        try:
            user_companies_response = (
                supabase.table("user_companies")
                .select("company_id")
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching user companies: {str(e)}")
        
        company_agents = []
        for company in user_companies_response.data:
            company_id = company["company_id"]
            
            # Get all agents for this company
            try:
                company_agents_response = (
                    supabase.table("agents")
                    .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                    .eq("company_id", company_id)
                    .eq("on_status", True)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error fetching company agents: {str(e)}")
            
            company_agents.extend(company_agents_response.data)
        
        # Combine personal and company agents
        all_agents = personal_agents + company_agents
        
        # Convert to response format
        return [
            {
                "agent_id": agent["agent_id"],
                "agent_name": agent["agent_name"],
                "description": agent.get("description"),
                "agent_style": agent.get("agent_style"),
                "on_status": agent.get("on_status", True),
                "company_id": agent.get("company_id"),
                "tools_count": len(agent.get("tools", []))
            }
            for agent in all_agents
        ]
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")


@router.get("/agents/{agent_id}", response_model=Dict[str, Any])
async def get_agent_details(
    agent_id: UUID,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get detailed information about an agent.
    
    This endpoint returns detailed information about an agent,
    including its tools and configuration.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get agent by ID, excluding route_path
        try:
            agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found",
                additional_info={"agent_id": str(agent_id)}
            )
        
        agent_config = agent_response.data[0]
        
        # Check if the user has access to the agent
        if agent_config.get("company_id"):
            # If agent belongs to a company, check if user has access to the company
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", agent_config["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this agent",
                    additional_info={"company_id": agent_config["company_id"]}
                )
        elif agent_config.get("user_id") != user_id:
            # If agent is personal, check if it belongs to the user
            raise ForbiddenError(
                "You don't have access to this agent",
                additional_info={"agent_id": str(agent_id)}
            )
        
        # Get tool details
        tool_details = []
        for tool_id in agent_config.get("tools", []):
            try:
                tool_response = (
                    supabase.table("tools")
                    .select("*")
                    .eq("tool_id", tool_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error fetching tool details: {str(e)}")
            
            if tool_response.data:
                tool_details.append(tool_response.data[0])
        
        # Return agent details with tools
        return {
            "agent_id": agent_config["agent_id"],
            "agent_name": agent_config["agent_name"],
            "description": agent_config.get("description"),
            "agent_style": agent_config.get("agent_style"),
            "on_status": agent_config.get("on_status", True),
            "company_id": agent_config.get("company_id"),
            "tools": tool_details
        }
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")