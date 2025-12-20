from uuid import UUID
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from supabase import Client

from microservice.agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ERROR_RESPONSES
)

# Pydantic models for request and response
class AgentToolBase(BaseModel):
    agent_id: UUID
    tool_id: UUID

class AgentToolCreate(AgentToolBase):
    pass

class AgentToolResponse(AgentToolBase):
    pass

# Create router
router = APIRouter(
    prefix="/agent-tools",
    tags=["agent-tools"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# CRUD operations
@router.post("/", response_model=AgentToolResponse)
async def assign_tool_to_agent(
    agent_tool: AgentToolCreate, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id  # This is now a string (UUID)
        
        # Verify that the agent belongs to the current user
        try:
            agent_response = (
                supabase.table("agent_collection")
                .select("agent_id")
                .eq("agent_id", agent_tool.agent_id)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID {agent_tool.agent_id} not found or you don't have permission",
                additional_info={"agent_id": agent_tool.agent_id}
            )
        
        # Verify that the tool exists
        try:
            tool_response = (
                supabase.table("tool_collection")
                .select("tool_id")
                .eq("tool_id", agent_tool.tool_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching tool: {str(e)}")
        
        if not tool_response.data:
            raise NotFoundError(
                f"Tool with ID {agent_tool.tool_id} not found",
                additional_info={"tool_id": agent_tool.tool_id}
            )
        
        # Check if the relationship already exists
        try:
            existing_response = (
                supabase.table("agent_tool")
                .select("*")
                .eq("agent_id", agent_tool.agent_id)
                .eq("tool_id", agent_tool.tool_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error checking existing relationship: {str(e)}")
        
        if existing_response.data:
            raise BadRequestError(
                "This tool is already assigned to the agent",
                additional_info={
                    "agent_id": agent_tool.agent_id,
                    "tool_id": agent_tool.tool_id
                }
            )
        
        # Insert agent-tool relationship
        try:
            response = (
                supabase.table("agent_tool")
                .insert({
                    "agent_id": agent_tool.agent_id,
                    "tool_id": agent_tool.tool_id
                })
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error assigning tool to agent: {str(e)}")
        
        # Check if insert was successful
        if not response.data:
            raise InternalServerError("Failed to assign tool to agent")
        
        return response.data[0]
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/agent/{agent_id}/tools", response_model=List[Dict[str, Any]])
async def get_agent_tools(
    agent_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id  # This is now a string (UUID)
        
        # Verify that the agent belongs to the current user
        try:
            agent_response = (
                supabase.table("agent_collection")
                .select("agent_id")
                .eq("agent_id", agent_id)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID {agent_id} not found or you don't have permission",
                additional_info={"agent_id": agent_id}
            )
        
        # Get all tools for this agent
        try:
            agent_tools_response = (
                supabase.table("agent_tool")
                .select("*")
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent tools: {str(e)}")
        
        if not agent_tools_response.data:
            return []
        
        # Get tool details for each tool_id
        result = []
        for item in agent_tools_response.data:
            # Get tool details
            try:
                tool_response = (
                    supabase.table("tool_collection")
                    .select("*")
                    .eq("tool_id", item["tool_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error fetching tool details: {str(e)}")
            
            if tool_response.data:
                result.append({
                    "agent_id": agent_id,
                    "tool_id": item["tool_id"],
                    "tool_details": tool_response.data[0]
                })
        
        return result
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.delete("/{agent_id}/{tool_id}")
async def remove_tool_from_agent(
    agent_id: UUID,
    tool_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id  # This is now a string (UUID)
        
        # Verify that the agent belongs to the current user
        try:
            agent_response = (
                supabase.table("agent_collection")
                .select("agent_id")
                .eq("agent_id", agent_id)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID {agent_id} not found or you don't have permission",
                additional_info={"agent_id": agent_id}
            )
        
        # Delete the agent-tool relationship
        try:
            response = (
                supabase.table("agent_tool")
                .delete()
                .eq("agent_id", agent_id)
                .eq("tool_id", tool_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error removing tool from agent: {str(e)}")
        
        if not response.data:
            raise NotFoundError(
                f"Tool with ID {tool_id} not assigned to agent with ID {agent_id}",
                additional_info={"agent_id": agent_id, "tool_id": tool_id}
            )
        
        return {"message": "Tool removed from agent successfully"}
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")