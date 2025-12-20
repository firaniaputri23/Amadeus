from fastapi import APIRouter, Request, Depends, Query
from pydantic import BaseModel, Field, condecimal
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from supabase import Client

from microservice.agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ValidationError, ERROR_RESPONSES
)

# Pydantic models for request and response
class AgentLogBase(BaseModel):
    agent_id: UUID
    input_token: Optional[int] = Field(default=0, ge=0)
    output_token: Optional[int] = Field(default=0, ge=0)
    embedding_token: Optional[int] = Field(default=0, ge=0)
    pricing: Optional[condecimal(max_digits=10, decimal_places=4)] = Field(default=0)
    chat_history: List[Dict[str, Any]] = []
    model_protocol: Optional[str] = None
    model_temperature: Optional[condecimal(max_digits=3, decimal_places=2)] = Field(None, ge=0, le=1)
    media_input: bool = False
    media_output: bool = False
    use_memory: bool = False
    use_tool: bool = False

class AgentLogCreate(AgentLogBase):
    pass

class AgentLogResponse(AgentLogBase):
    agent_log_id: UUID
    date: datetime

# Create router
router = APIRouter(
    prefix="/agent-logs",
    tags=["agent-logs"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# CRUD operations
@router.post("/", response_model=AgentLogResponse)
async def create_agent_log(
    agent_log: AgentLogCreate, 
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Verify that the agent exists and belongs to the current user or user's company
        try:
            agent_response = (
                supabase.table("agents")
                .select("*")
                .eq("agent_id", str(agent_log.agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(f"Agent with ID '{agent_log.agent_id}' not found")
        
        agent = agent_response.data[0]
        
        # Check if agent belongs to the user
        if agent["user_id"] != user_id:
            # If not, check if agent belongs to a company the user has access to
            if not agent.get("company_id"):
                raise ForbiddenError("You don't have permission to access this agent")
            
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
                raise ForbiddenError("You don't have access to this company")
        
        # Insert agent log
        try:
            response = (
                supabase.table("agent_logs")
                .insert({
                    "agent_id": str(agent_log.agent_id),
                    "input_token": agent_log.input_token,
                    "output_token": agent_log.output_token,
                    "embedding_token": agent_log.embedding_token,
                    "pricing": float(agent_log.pricing) if agent_log.pricing is not None else 0,
                    "chat_history": agent_log.chat_history,
                    "model_protocol": agent_log.model_protocol,
                    "model_temperature": float(agent_log.model_temperature) if agent_log.model_temperature else None,
                    "media_input": agent_log.media_input,
                    "media_output": agent_log.media_output,
                    "use_memory": agent_log.use_memory,
                    "use_tool": agent_log.use_tool
                })
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error creating agent log: {str(e)}")
        
        # Check if insert was successful
        if not response.data:
            raise InternalServerError("Failed to create agent log")
        
        return response.data[0]
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/agent/{agent_id}", response_model=List[AgentLogResponse])
async def get_agent_logs(
    agent_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Verify that the agent exists and belongs to the current user or user's company
        try:
            agent_response = (
                supabase.table("agents")
                .select("*")
                .eq("agent_id", str(agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(f"Agent with ID '{agent_id}' not found")
        
        agent = agent_response.data[0]
        
        # Check if agent belongs to the user
        if agent["user_id"] != user_id:
            # If not, check if agent belongs to a company the user has access to
            if not agent.get("company_id"):
                raise ForbiddenError(
                    "You don't have permission to access this agent",
                    additional_info={"agent_id": str(agent_id)}
                )
            
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
        
        # Get all logs for this agent
        try:
            response = (
                supabase.table("agent_logs")
                .select("*")
                .eq("agent_id", str(agent_id))
                .order("date", desc=True)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent logs: {str(e)}")
        
        return response.data
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/{agent_id}", response_model=AgentLogResponse)
async def get_agent_log(
    agent_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the most recent log for this agent
        try:
            log_response = (
                supabase.table("agent_logs")
                .select("*")
                .eq("agent_id", str(agent_id))
                .order("date", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent log: {str(e)}")
        
        if not log_response.data:
            raise NotFoundError(f"Log not found for agent with ID '{agent_id}'")
        
        log = log_response.data[0]
        
        # Get the agent to verify ownership
        agent_id_from_log = log["agent_id"]
        try:
            agent_response = (
                supabase.table("agents")
                .select("*")
                .eq("agent_id", agent_id_from_log)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent information: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(f"Agent with ID '{agent_id_from_log}' not found")
        
        agent = agent_response.data[0]
        
        # Check if agent belongs to the user
        if agent["user_id"] != user_id:
            # If not, check if agent belongs to a company the user has access to
            if not agent.get("company_id"):
                raise ForbiddenError(
                    "You don't have permission to access this log",
                    additional_info={"agent_id": agent_id_from_log}
                )
            
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
        
        return log
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.delete("/{agent_id}")
async def delete_agent_log(
    agent_id: UUID,
    request: Request, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Verify that the agent exists and belongs to the current user or user's company
        try:
            agent_response = (
                supabase.table("agents")
                .select("*")
                .eq("agent_id", str(agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(f"Agent with ID '{agent_id}' not found")
        
        agent = agent_response.data[0]
        
        # Check if agent belongs to the user
        if agent["user_id"] != user_id:
            # If not, check if agent belongs to a company the user has access to
            if not agent.get("company_id"):
                raise ForbiddenError(
                    "You don't have permission to delete logs for this agent",
                    additional_info={"agent_id": str(agent_id)}
                )
            
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
            
            # Check if user has admin or write role
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
            
            if not role_response.data or role_response.data[0]["role_name"] not in ["admin", "write"]:
                raise ForbiddenError(
                    "You don't have permission to delete logs for this company",
                    additional_info={"required_role": "admin or write", "current_role": role_response.data[0]["role_name"] if role_response.data else "unknown"}
                )
        
        # Delete all logs for this agent
        try:
            delete_response = (
                supabase.table("agent_logs")
                .delete()
                .eq("agent_id", str(agent_id))
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error deleting agent logs: {str(e)}")
        
        return {"message": "All logs for this agent deleted successfully"}
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")