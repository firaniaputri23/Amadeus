from fastapi import APIRouter, Request, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4
from supabase import Client

from microservice.agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ValidationError, ERROR_RESPONSES
)

# Pydantic models for request and response
class AgentBase(BaseModel):
    agent_name: str
    description: Optional[str] = None
    agent_style: Optional[str] = None
    on_status: Optional[bool] = True
    tools: Optional[List[UUID]] = []  # List of tool UUIDs

class AgentCreate(AgentBase):
    company_id: Optional[UUID] = None  # Optional company ID

class AgentResponse(AgentBase):
    agent_id: UUID
    user_id: UUID
    company_id: Optional[UUID] = None
    created_at: Optional[str] = None

class AgentWithToolDetails(AgentResponse):
    tool_details: Optional[List[Dict[str, Any]]] = []

# Create router
router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# Helper function to check write permissions
def check_write_permission(role_name: str):
    if role_name not in ['super admin', 'admin', 'staff']:
        raise ForbiddenError(
            "You don't have permission to perform this action",
            additional_info={"required_role": "super admin, admin, or staff"}
        )

# CRUD operations
@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent: AgentCreate, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # If company_id is provided, check if user has write access to the company
        if agent.company_id:
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", str(agent.company_id))
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company",
                    additional_info={"company_id": str(agent.company_id)}
                )
            
            role_id = user_company_response.data[0]["role_id"]
            
            try:
                role_response = (
                    supabase.table("roles")
                    .select("role_name")
                    .eq("role_id", role_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking role permissions: {str(e)}")
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise ForbiddenError(
                    "You don't have permission to create agents for this company",
                    additional_info={"required_role": "super admin, admin, or staff"}
                )
        
        # Verify that all tools exist if provided
        if agent.tools:
            for tool_id in agent.tools:
                try:
                    tool_response = (
                        supabase.table("tools")
                        .select("tool_id")
                        .eq("tool_id", str(tool_id))
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error checking tool existence: {str(e)}")
                
                if not tool_response.data:
                    raise NotFoundError(
                        f"Tool with ID {tool_id} not found",
                        additional_info={"tool_id": str(tool_id)}
                    )
        
        # Convert UUID objects to strings for Supabase
        tools_str = [str(tool_id) for tool_id in agent.tools] if agent.tools else []
        
        # Insert agent into database
        try:
            response = (
                supabase.table("agents")
                .insert({
                    "user_id": user_id,
                    "company_id": str(agent.company_id) if agent.company_id else None,
                    "agent_name": agent.agent_name,
                    "description": agent.description,
                    "agent_style": agent.agent_style,
                    "on_status": agent.on_status,
                    "tools": tools_str
                })
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error creating agent: {str(e)}")
        
        # Check if insert was successful
        if not response.data:
            raise InternalServerError("Failed to create agent")
        
        return response.data[0]
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/", response_model=List[AgentResponse])
async def get_agents(
    request: Request, 
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Build query
        query = supabase.table("agents").select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools, created_at")

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


@router.get("/{agent_id}", response_model=AgentWithToolDetails)
async def get_agent(
    agent_id: UUID, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get agent by ID (ensuring it belongs to the current user)
        try:
            response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        agent = response.data[0]
        
        # If agent belongs to a company, check if user has access to the company
        if agent.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", agent["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company", 
                    additional_info={"company_id": agent["company_id"]}
                )
        
        # Get tool details for each tool_id in the tools array
        tool_details = []
        if agent.get("tools"):
            for tool_id in agent["tools"]:
                try:
                    tool_response = (
                        supabase.table("tools_with_decrypted_keys")
                        .select("*")
                        .eq("tool_id", tool_id)
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error fetching tool details: {str(e)}")
                
                if tool_response.data:
                    tool_details.append(tool_response.data[0])
        
        # Add tool details to the response
        agent["tool_details"] = tool_details
        
        return agent
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID, 
    agent: AgentCreate, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the existing agent to check ownership and company
        try:
            existing_agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not existing_agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        existing_agent = existing_agent_response.data[0]
        
        # Check company permissions if the agent belongs to a company
        if existing_agent.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", existing_agent["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company", 
                    additional_info={"company_id": existing_agent["company_id"]}
                )
            
            role_id = user_company_response.data[0]["role_id"]
            
            try:
                role_response = (
                    supabase.table("roles")
                    .select("role_name")
                    .eq("role_id", role_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking role permissions: {str(e)}")
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise ForbiddenError(
                    "You don't have permission to update agents for this company",
                    additional_info={
                        "required_role": "super admin, admin, or staff",
                        "current_role": role_response.data[0]["role_name"] if role_response.data else "unknown"
                    }
                )
        
        # Check if trying to change company_id
        if agent.company_id and str(agent.company_id) != existing_agent.get("company_id"):
            # Check if user has access to the new company
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", str(agent.company_id))
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking new company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to the specified company", 
                    additional_info={"company_id": str(agent.company_id)}
                )
            
            role_id = user_company_response.data[0]["role_id"]
            
            try:
                role_response = (
                    supabase.table("roles")
                    .select("role_name")
                    .eq("role_id", role_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking role permissions: {str(e)}")
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise ForbiddenError(
                    "You don't have permission to move agents to this company",
                    additional_info={
                        "required_role": "super admin, admin, or staff",
                        "current_role": role_response.data[0]["role_name"] if role_response.data else "unknown"
                    }
                )
        
        # Verify that all tools exist if provided
        if agent.tools:
            for tool_id in agent.tools:
                try:
                    tool_response = (
                        supabase.table("tools")
                        .select("tool_id")
                        .eq("tool_id", str(tool_id))
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error checking tool existence: {str(e)}")
                
                if not tool_response.data:
                    raise NotFoundError(
                        f"Tool with ID {tool_id} not found",
                        additional_info={"tool_id": str(tool_id)}
                    )
        
        # Convert UUID objects to strings for Supabase
        tools_str = [str(tool_id) for tool_id in agent.tools] if agent.tools else []
        
        # Update agent
        try:
            response = (
                supabase.table("agents")
                .update({
                    "company_id": str(agent.company_id) if agent.company_id else None,
                    "agent_name": agent.agent_name,
                    "description": agent.description,
                    "agent_style": agent.agent_style,
                    "on_status": agent.on_status,
                    "tools": tools_str
                })
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating agent: {str(e)}")
        
        if not response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        return response.data[0]
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the existing agent to check ownership and company
        try:
            existing_agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not existing_agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        existing_agent = existing_agent_response.data[0]
        
        # Check company permissions if the agent belongs to a company
        if existing_agent.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", existing_agent["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company", 
                    additional_info={"company_id": existing_agent["company_id"]}
                )
            
            role_id = user_company_response.data[0]["role_id"]
            
            try:
                role_response = (
                    supabase.table("roles")
                    .select("role_name")
                    .eq("role_id", role_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking role permissions: {str(e)}")
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin"]:
                raise ForbiddenError(
                    "Only company admins can delete company agents",
                    additional_info={
                        "required_role": "super admin or admin",
                        "current_role": role_response.data[0]["role_name"] if role_response.data else "unknown"
                    }
                )
        
        
        # Delete related logs first to avoid Foreign Key violations
        try:
            # We ignore the result of this operation as logs might not exist
            supabase.table("agent_logs").delete().eq("agent_id", str(agent_id)).execute()
        except Exception as e:
            # Log specific error but try to proceed (or fail if strict)
            print(f"Warning: Failed to cleanup logs for agent {agent_id}: {e}")
            # Depending on DB constraints, we might want to fail here, but let's try to proceed
        
        # Delete agent
        try:
            response = (
                supabase.table("agents")
                .delete()
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error deleting agent: {str(e)}")
        
        if not response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        return {"message": "Agent deleted successfully"}
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

# Tool management endpoints
@router.post("/{agent_id}/tools/{tool_id}")
async def add_tool_to_agent(
    agent_id: UUID,
    tool_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the existing agent to check ownership and company
        try:
            existing_agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not existing_agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        existing_agent = existing_agent_response.data[0]
        
        # Check company permissions if the agent belongs to a company
        if existing_agent.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", existing_agent["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company", 
                    additional_info={"company_id": existing_agent["company_id"]}
                )
            
            role_id = user_company_response.data[0]["role_id"]
            
            try:
                role_response = (
                    supabase.table("roles")
                    .select("role_name")
                    .eq("role_id", role_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking role permissions: {str(e)}")
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise ForbiddenError(
                    "You don't have permission to modify agents for this company",
                    additional_info={
                        "required_role": "super admin, admin, or staff",
                        "current_role": role_response.data[0]["role_name"] if role_response.data else "unknown"
                    }
                )
        
        # Verify that the tool exists
        try:
            tool_response = (
                supabase.table("tools")
                .select("tool_id")
                .eq("tool_id", str(tool_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error checking tool existence: {str(e)}")
        
        if not tool_response.data:
            raise NotFoundError(
                f"Tool with ID '{tool_id}' not found",
                additional_info={"tool_id": str(tool_id)}
            )
        
        # Get current tools array
        tools = existing_agent.get("tools", [])
        
        # Check if tool is already in the array
        if str(tool_id) in tools:
            raise BadRequestError(
                "Tool already assigned to this agent",
                additional_info={
                    "agent_id": str(agent_id),
                    "tool_id": str(tool_id)
                }
            )
        
        # Add tool_id to the tools array
        tools.append(str(tool_id))
        
        # Update the agent with the new tools array
        try:
            update_response = (
                supabase.table("agents")
                .update({"tools": tools})
                .eq("agent_id", str(agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error adding tool to agent: {str(e)}")
        
        if not update_response.data:
            raise InternalServerError("Failed to add tool to agent")
        
        return {"message": "Tool added to agent successfully"}
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.delete("/{agent_id}/tools/{tool_id}")
async def remove_tool_from_agent(
    agent_id: UUID,
    tool_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the existing agent to check ownership and company
        try:
            existing_agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not existing_agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        existing_agent = existing_agent_response.data[0]
        
        # Check company permissions if the agent belongs to a company
        if existing_agent.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", existing_agent["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company", 
                    additional_info={"company_id": existing_agent["company_id"]}
                )
            
            role_id = user_company_response.data[0]["role_id"]
            
            try:
                role_response = (
                    supabase.table("roles")
                    .select("role_name")
                    .eq("role_id", role_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking role permissions: {str(e)}")
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise ForbiddenError(
                    "You don't have permission to modify agents for this company",
                    additional_info={
                        "required_role": "super admin, admin, or staff",
                        "current_role": role_response.data[0]["role_name"] if role_response.data else "unknown"
                    }
                )
        
        # Get current tools array
        tools = existing_agent.get("tools", [])
        
        # Check if tool is in the array
        if str(tool_id) not in tools:
            raise NotFoundError(
                f"Tool with ID '{tool_id}' not assigned to this agent",
                additional_info={
                    "agent_id": str(agent_id), 
                    "tool_id": str(tool_id)
                }
            )
        
        # Remove tool_id from the tools array
        tools.remove(str(tool_id))
        
        # Update the agent with the new tools array
        try:
            update_response = (
                supabase.table("agents")
                .update({"tools": tools})
                .eq("agent_id", str(agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error removing tool from agent: {str(e)}")
        
        if not update_response.data:
            raise InternalServerError("Failed to remove tool from agent")
        
        return {"message": "Tool removed from agent successfully"}
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/{agent_id}/tools", response_model=List[Dict[str, Any]])
async def get_agent_tools(
    agent_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the existing agent to check ownership and company
        try:
            existing_agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not existing_agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        existing_agent = existing_agent_response.data[0]
        
        # Check company permissions if the agent belongs to a company
        if existing_agent.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", existing_agent["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company", 
                    additional_info={"company_id": existing_agent["company_id"]}
                )
        
        # Get tools array
        tools = existing_agent.get("tools", [])
        
        # Get tool details for each tool_id
        tool_details = []
        for tool_id in tools:
            try:
                tool_response = (
                    supabase.table("tools_with_decrypted_keys")
                    .select("*")
                    .eq("tool_id", tool_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error fetching tool details: {str(e)}")
            
            if tool_response.data:
                tool_details.append(tool_response.data[0])
        
        return tool_details
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

# Clone agent endpoint
@router.post("/{agent_id}/clone", response_model=AgentResponse)
async def clone_agent(
    agent_id: UUID, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the existing agent to check ownership and clone it
        try:
            existing_agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools")
                .eq("agent_id", str(agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not existing_agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found", 
                additional_info={"agent_id": str(agent_id)}
            )
        
        existing_agent = existing_agent_response.data[0]
        
        # Check company permissions if the agent belongs to a company
        if existing_agent.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", existing_agent["company_id"])
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
            
            if not user_company_response.data:
                raise ForbiddenError(
                    "You don't have access to this company", 
                    additional_info={"company_id": existing_agent["company_id"]}
                )
            
            role_id = user_company_response.data[0]["role_id"]
            
            try:
                role_response = (
                    supabase.table("roles")
                    .select("role_name")
                    .eq("role_id", role_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error checking role permissions: {str(e)}")
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["super admin", "admin", "staff"]:
                raise ForbiddenError(
                    "You don't have permission to clone agents for this company",
                    additional_info={
                        "required_role": "super admin, admin, or staff",
                        "current_role": role_response.data[0]["role_name"] if role_response.data else "unknown"
                    }
                )
        
        # Create a new agent with the same properties as the existing one
        clone_data = {
            "user_id": user_id,
            "company_id": existing_agent.get("company_id"),
            "agent_name": f"Clone of {existing_agent['agent_name']}",
            "description": existing_agent.get("description"),
            "agent_style": existing_agent.get("agent_style"),
            "on_status": existing_agent.get("on_status", True),
            "tools": existing_agent.get("tools", [])
        }
        
        # Insert cloned agent into database
        try:
            response = (
                supabase.table("agents")
                .insert(clone_data)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error cloning agent: {str(e)}")
        
        # Check if insert was successful
        if not response.data:
            raise InternalServerError("Failed to clone agent")
        
        return response.data[0]
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")