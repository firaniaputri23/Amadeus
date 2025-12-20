"""
Feature Sharing Routes

This module provides endpoints for sharing agents and threads with other users.
"""

from fastapi import APIRouter, Request, Depends, Body
from typing import Dict, Any, List
from supabase import Client
import uuid
import json

from ...agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ERROR_RESPONSES
)
# Create router
router = APIRouter(
    prefix="/feature-sharing",
    tags=["feature_sharing"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# Agent Sharing Endpoints

@router.post("/agent/share-editor-with/{agent_id}/", response_model=Dict[str, Any])
async def share_agent_with_editor(
    agent_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    emails: List[str] = Body(..., embed=True)
):
    """
    Share an agent with specific users as editors (read-write access).
    
    This endpoint adds the provided email addresses to the agent's share_editor_with list.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get agent by agent_id
        try:
            agent_response = (
                supabase.table("agents")
                .select("agent_id, user_id, company_id, share_editor_with")
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found",
                additional_info={
                    "agent_id": agent_id
                }
            )
        
        agent = agent_response.data[0]
        
        # Check if the user has permission to share the agent
        if agent.get("user_id") != user_id:
            # Check if the user belongs to the agent's company
            if agent.get("company_id"):
                try:
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id")
                        .eq("user_id", user_id)
                        .eq("company_id", agent["company_id"])
                        .execute()
                    )
                    
                    if not user_company_response.data:
                        raise ForbiddenError(
                            "You don't have permission to share this agent",
                            additional_info={
                                "agent_id": agent_id
                            }
                        )
                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            else:
                raise ForbiddenError(
                    "You don't have permission to share this agent",
                    additional_info={
                        "agent_id": agent_id
                    }
                )
        
        # Update the share_editor_with list
        current_editors = agent.get("share_editor_with", [])
        
        # Add new emails, avoiding duplicates
        for email in emails:
            if email not in current_editors:
                current_editors.append(email)
        
        # Update the agent in the database
        try:
            update_response = (
                supabase.table("agents")
                .update({"share_editor_with": current_editors})
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating agent: {str(e)}")
        
        return {
            "success": True,
            "message": f"Agent shared with {len(emails)} editor(s)",
            "share_editor_with": current_editors
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")


@router.post("/agent/share-visitor-with/{agent_id}/", response_model=Dict[str, Any])
async def share_agent_with_visitor(
    agent_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    emails: List[str] = Body(..., embed=True)
):
    """
    Share an agent with specific users as visitors (read-only access).
    
    This endpoint adds the provided email addresses to the agent's share_visitor_with list.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get agent by agent_id
        try:
            agent_response = (
                supabase.table("agents")
                .select("agent_id, user_id, company_id, share_visitor_with")
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found",
                additional_info={
                    "agent_id": agent_id
                }
            )
        
        agent = agent_response.data[0]
        
        # Check if the user has permission to share the agent
        if agent.get("user_id") != user_id:
            # Check if the user belongs to the agent's company
            if agent.get("company_id"):
                try:
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id")
                        .eq("user_id", user_id)
                        .eq("company_id", agent["company_id"])
                        .execute()
                    )
                    
                    if not user_company_response.data:
                        raise ForbiddenError(
                            "You don't have permission to share this agent",
                            additional_info={
                                "agent_id": agent_id
                            }
                        )
                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            else:
                raise ForbiddenError(
                    "You don't have permission to share this agent",
                    additional_info={
                        "agent_id": agent_id
                    }
                )
        
        # Update the share_visitor_with list
        current_visitors = agent.get("share_visitor_with", [])
        
        # Add new emails, avoiding duplicates
        for email in emails:
            if email not in current_visitors:
                current_visitors.append(email)
        
        # Update the agent in the database
        try:
            update_response = (
                supabase.table("agents")
                .update({"share_visitor_with": current_visitors})
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating agent: {str(e)}")
        
        return {
            "success": True,
            "message": f"Agent shared with {len(emails)} visitor(s)",
            "share_visitor_with": current_visitors
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")


@router.post("/agent/share-anyone-with-link/{agent_id}/", response_model=Dict[str, Any])
async def share_agent_with_anyone(
    agent_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Generate a public link for an agent that can be accessed by anyone.
    
    This endpoint sets the agent's is_public flag to True and generates a public_hash.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the current authenticated user's email for editor checks
        current_user_email = None
        if hasattr(request.state, 'user') and isinstance(request.state.user, dict):
            current_user_email = request.state.user.get('email')
        elif hasattr(request.state, 'email'): # Fallback
             current_user_email = request.state.email
        
        # Get agent by agent_id
        try:
            agent_response = (
                supabase.table("agents")
                .select("agent_id, user_id, company_id, is_public, public_hash")
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent: {str(e)}")
        
        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id}' not found",
                additional_info={
                    "agent_id": agent_id
                }
            )
        
        agent = agent_response.data[0]
        
        # Check if the user has permission to share the agent
        is_agent_owner = agent.get("user_id") == user_id
        is_company_member_with_rights = False
        
        editors_list = agent.get("share_editor_with") or []
        is_agent_editor = False
        if current_user_email:
            is_agent_editor = current_user_email in editors_list

        if not is_agent_owner:
            if agent.get("company_id"):
                try:
                    company_id_str = str(agent["company_id"])
                    user_id_str = str(user_id) # user_id (UUID) is correct for user_companies table
                    
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id") # Role could be used for finer control, e.g. only admins
                        .eq("user_id", user_id_str)
                        .eq("company_id", company_id_str)
                        .execute()
                    )
                    
                    if user_company_response.data:
                        is_company_member_with_rights = True
                        # Potentially check role here if needed: 
                        # e.g., role = user_company_response.data[0]["role_id"]

                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            
            # If not owner, and not a company member with rights, check if they are an editor
            if not is_company_member_with_rights and not is_agent_editor:
                raise ForbiddenError(
                    "You don't have permission to make this agent public.",
                    additional_info={"agent_id": agent_id}
                )
        
        # If we reach here, permission is granted (owner, or company member, or editor)
        # Generate a public hash if one doesn't exist
        public_hash = agent.get("public_hash")
        
        if not public_hash:
            # Generate a unique hash for the public link
            public_hash = str(uuid.uuid4()).replace("-", "")[:16]
        
        # Update the agent in the database
        try:
            update_response = (
                supabase.table("agents")
                .update({
                    "is_public": True,
                    "public_hash": public_hash
                })
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating agent: {str(e)}")
        
        return {
            "success": True,
            "message": "Agent is now publicly accessible",
            "public_hash": public_hash,
            "is_public": True
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")



# Thread Sharing Endpoints
@router.post("/thread/share-editor-with/{agent_id}/{thread_id}", response_model=Dict[str, Any])
async def share_thread_with_editor(
    agent_id: str,
    thread_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    emails: List[str] = Body(..., embed=True)
):
    """
    Share a thread with specific users as editors (read-write access).
    
    This endpoint adds the provided email addresses to the thread's share_editor_with list.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the current authenticated user's email for editor checks
        current_user_email = None
        if hasattr(request.state, 'user') and isinstance(request.state.user, dict):
            current_user_email = request.state.user.get('email')
        # Fallback if request.state directly has an email attribute (less likely based on logs)
        elif hasattr(request.state, 'email'):
             current_user_email = request.state.email

        # Get agent log by thread_id
        try:
            log_response = (
                supabase.table("agent_logs")
                .select("agent_log_id, agent_id, chat_history")
                .eq("agent_log_id", thread_id)
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent log: {str(e)}")
        
        if not log_response.data:
            raise NotFoundError(
                f"Thread with ID '{thread_id}' not found for agent '{agent_id}'",
                additional_info={
                    "agent_id": agent_id,
                    "thread_id": thread_id
                }
            )
        
        log = log_response.data[0]
        
        # Permission Check: User must have rights to the agent associated with this thread.
        agent_id_from_log = log.get("agent_id")
        
        if not agent_id_from_log:
            raise ForbiddenError(
                "Thread is not linked to a valid agent, cannot determine permissions.",
                additional_info={"thread_id": thread_id}
            )

        try:
            agent_response = (
                supabase.table("agents")
                .select("user_id, company_id, share_editor_with")
                .eq("agent_id", agent_id_from_log)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent for permission check: {str(e)}")

        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id_from_log}' (associated with thread '{thread_id}') not found.",
                additional_info={"agent_id": agent_id_from_log, "thread_id": thread_id}
            )
            
        agent = agent_response.data[0]
        
        # Check 1: Is the current user the owner of the agent? (UUID vs UUID)
        is_agent_owner = agent.get("user_id") == user_id
        
        # Check 2: Is the current user (by email) in the agent's list of shared editors?
        editors_list = agent.get("share_editor_with") or [] # This is a list of emails
        is_agent_editor = False
        if current_user_email and editors_list: 
            is_agent_editor = current_user_email in editors_list
        
        # Check 3: Company membership (relies on user_id for user_companies table)
        is_company_member_with_rights = False
        if not is_agent_owner and agent.get("company_id"): 
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id") # Role might be used for finer-grained access in future
                    .eq("user_id", user_id)
                    .eq("company_id", agent["company_id"])
                    .execute()
                )
                if user_company_response.data:
                    is_company_member_with_rights = True 
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")

        if not (is_agent_owner or is_company_member_with_rights or is_agent_editor):
            raise ForbiddenError(
                "You don't have permission to share this thread.",
                additional_info={"agent_id": agent_id_from_log, "thread_id": thread_id}
            )

        # If we reach here, permission is granted. Proceed with sharing logic.
        # Get the current chat_history and process it
        raw_chat_history_data = log.get("chat_history")

        # Initialize the standard inner object structure
        chat_history_inner_obj = {
            "messages": [],
            "share_info": {
                "share_visitor_with": [],
                "share_editor_with": [],
                "public_hash": None,
                "is_public": False
            }
        }
        
        # Temporary variables to hold parsed messages and share_info
        parsed_messages_list = []
        parsed_share_info_dict = {}

        # Try to process raw_chat_history_data
        data_to_process = raw_chat_history_data
        if isinstance(raw_chat_history_data, str):
            try:
                data_to_process = json.loads(raw_chat_history_data)
            except json.JSONDecodeError:
                data_to_process = None # Indicate bad JSON, defaults will be used

        if data_to_process is None: # Bad JSON string case
            pass # messages and share_info remain default
        elif isinstance(data_to_process, list):
            # Case 1: Data is a list
            if data_to_process and isinstance(data_to_process[0], dict) and \
               ("messages" in data_to_process[0] or "share_info" in data_to_process[0]):
                # It looks like the new format `[{"messages": ..., "share_info": ...}]`
                # Use the content of the first element.
                source_dict = data_to_process[0]
                parsed_messages_list = source_dict.get("messages", [])
                if isinstance(source_dict.get("share_info"), dict):
                    parsed_share_info_dict = source_dict["share_info"]
            else:
                # It's an old list of messages, e.g., [{msg1}, {msg2}] or []
                parsed_messages_list = data_to_process
        elif isinstance(data_to_process, dict):
            # Case 2: Data is a dictionary
            if "messages" in data_to_process:
                parsed_messages_list = data_to_process.get("messages", [])
            elif data_to_process and not ("share_info" in data_to_process and len(data_to_process) == 1):
                 parsed_messages_list = [data_to_process]
            
            if "share_info" in data_to_process and isinstance(data_to_process.get("share_info"), dict):
                parsed_share_info_dict = data_to_process["share_info"]

        # Assign parsed components to the inner object
        chat_history_inner_obj["messages"] = parsed_messages_list if isinstance(parsed_messages_list, list) else []
        
        default_share_info_copy = {
            "share_visitor_with": [], "share_editor_with": [],
            "public_hash": None, "is_public": False
        }
        default_share_info_copy.update(parsed_share_info_dict)
        chat_history_inner_obj["share_info"] = default_share_info_copy

        for key_to_be_list in ["share_visitor_with", "share_editor_with"]:
            if not isinstance(chat_history_inner_obj["share_info"].get(key_to_be_list), list):
                chat_history_inner_obj["share_info"][key_to_be_list] = []
        
        # Update the share_editor_with list
        current_editors = chat_history_inner_obj["share_info"]["share_editor_with"] # Already a list
        
        for email in emails:
            if email not in current_editors:
                current_editors.append(email)
        
        chat_history_inner_obj["share_info"]["share_editor_with"] = current_editors
        
        # The data to be stored in the database
        final_chat_history_to_save = [chat_history_inner_obj]

        # Update the agent log in the database
        try:
            update_response = (
                supabase.table("agent_logs")
                .update({"chat_history": final_chat_history_to_save}) 
                .eq("agent_log_id", thread_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating agent log: {str(e)}")
        
        return {
            "success": True,
            "message": f"Thread shared with {len(emails)} editor(s)",
            "share_editor_with": chat_history_inner_obj["share_info"]["share_editor_with"]
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")



@router.post("/thread/share-visitor-with/{agent_id}/{thread_id}", response_model=Dict[str, Any])
async def share_thread_with_visitor(
    agent_id: str,
    thread_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    emails: List[str] = Body(..., embed=True)
):
    """
    Share a thread with specific users as visitors (read-only access).
    
    This endpoint adds the provided email addresses to the thread's share_visitor_with list.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the current authenticated user's email for editor checks
        current_user_email = None
        if hasattr(request.state, 'user') and isinstance(request.state.user, dict):
            current_user_email = request.state.user.get('email')
        # Fallback if request.state directly has an email attribute (less likely based on logs)
        elif hasattr(request.state, 'email'):
             current_user_email = request.state.email

        # Get agent log by thread_id
        try:
            log_response = (
                supabase.table("agent_logs")
                .select("agent_log_id, agent_id, chat_history")
                .eq("agent_log_id", thread_id)
                .eq("agent_id", agent_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent log: {str(e)}")
        
        if not log_response.data:
            raise NotFoundError(
                f"Thread with ID '{thread_id}' not found for agent '{agent_id}'",
                additional_info={
                    "agent_id": agent_id,
                    "thread_id": thread_id
                }
            )
        
        log = log_response.data[0]
        
        # Permission Check: User must have rights to the agent associated with this thread.
        agent_id_from_log = log.get("agent_id")
        
        if not agent_id_from_log:
            raise ForbiddenError(
                "Thread is not linked to a valid agent, cannot determine permissions.",
                additional_info={"thread_id": thread_id}
            )

        try:
            agent_response = (
                supabase.table("agents")
                .select("user_id, company_id, share_editor_with")
                .eq("agent_id", agent_id_from_log)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent for permission check: {str(e)}")

        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id_from_log}' (associated with thread '{thread_id}') not found.",
                additional_info={"agent_id": agent_id_from_log, "thread_id": thread_id}
            )
            
        agent = agent_response.data[0]
        
        # Check 1: Is the current user the owner of the agent? (UUID vs UUID)
        is_agent_owner = agent.get("user_id") == user_id
        
        # Check 2: Is the current user (by email) in the agent's list of shared editors?
        editors_list = agent.get("share_editor_with") or [] # This is a list of emails
        is_agent_editor = False
        if current_user_email and editors_list: 
            is_agent_editor = current_user_email in editors_list
        
        # Check 3: Company membership (relies on user_id for user_companies table)
        is_company_member_with_rights = False
        if not is_agent_owner and agent.get("company_id"): 
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id") # Role might be used for finer-grained access in future
                    .eq("user_id", user_id)
                    .eq("company_id", agent["company_id"])
                    .execute()
                )
                if user_company_response.data:
                    is_company_member_with_rights = True 
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")

        if not (is_agent_owner or is_company_member_with_rights or is_agent_editor):
            raise ForbiddenError(
                "You don't have permission to share this thread.",
                additional_info={"agent_id": agent_id_from_log, "thread_id": thread_id}
            )

        # If we reach here, permission is granted. Proceed with sharing logic.
        # Get the current chat_history
        raw_chat_history_data = log.get("chat_history")
        
        # Initialize the standard inner object structure
        chat_history_inner_obj = {
            "messages": [],
            "share_info": {
                "share_visitor_with": [],
                "share_editor_with": [],
                "public_hash": None,
                "is_public": False
            }
        }
        
        # Temporary variables to hold parsed messages and share_info
        parsed_messages_list = []
        parsed_share_info_dict = {}

        # Try to process raw_chat_history_data
        data_to_process = raw_chat_history_data
        if isinstance(raw_chat_history_data, str):
            try:
                data_to_process = json.loads(raw_chat_history_data)
            except json.JSONDecodeError:
                data_to_process = None # Indicate bad JSON, defaults will be used

        if data_to_process is None: # Bad JSON string case
            pass # messages and share_info remain default
        elif isinstance(data_to_process, list):
            # Case 1: Data is a list
            if data_to_process and isinstance(data_to_process[0], dict) and \
               ("messages" in data_to_process[0] or "share_info" in data_to_process[0]):
                # It looks like the new format `[{"messages": ..., "share_info": ...}]`
                # Use the content of the first element.
                source_dict = data_to_process[0]
                parsed_messages_list = source_dict.get("messages", [])
                if isinstance(source_dict.get("share_info"), dict):
                    parsed_share_info_dict = source_dict["share_info"]
            else:
                # It's an old list of messages, e.g., [{msg1}, {msg2}] or []
                parsed_messages_list = data_to_process
        elif isinstance(data_to_process, dict):
            # Case 2: Data is a dictionary
            if "messages" in data_to_process:
                parsed_messages_list = data_to_process.get("messages", [])
            elif data_to_process and not ("share_info" in data_to_process and len(data_to_process) == 1):
                 parsed_messages_list = [data_to_process]
            
            if "share_info" in data_to_process and isinstance(data_to_process.get("share_info"), dict):
                parsed_share_info_dict = data_to_process["share_info"]

        # Assign parsed components to the inner object
        chat_history_inner_obj["messages"] = parsed_messages_list if isinstance(parsed_messages_list, list) else []
        
        default_share_info_copy = {
            "share_visitor_with": [], "share_editor_with": [],
            "public_hash": None, "is_public": False
        }
        default_share_info_copy.update(parsed_share_info_dict)
        chat_history_inner_obj["share_info"] = default_share_info_copy

        for key_to_be_list in ["share_visitor_with", "share_editor_with"]:
            if not isinstance(chat_history_inner_obj["share_info"].get(key_to_be_list), list):
                chat_history_inner_obj["share_info"][key_to_be_list] = []
        
        # Update the share_visitor_with list
        current_visitors = chat_history_inner_obj["share_info"]["share_visitor_with"] # Already a list
        
        # Add new emails, avoiding duplicates
        for email in emails:
            if email not in current_visitors:
                current_visitors.append(email)
        
        chat_history_inner_obj["share_info"]["share_visitor_with"] = current_visitors
        
        # The data to be stored in the database
        final_chat_history_to_save = [chat_history_inner_obj]

        # Update the agent log in the database
        try:
            update_response = (
                supabase.table("agent_logs")
                .update({"chat_history": final_chat_history_to_save})
                .eq("agent_log_id", thread_id)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating agent log: {str(e)}")
        
        return {
            "success": True,
            "message": f"Thread shared with {len(emails)} visitor(s)",
            "share_visitor_with": chat_history_inner_obj["share_info"]["share_visitor_with"]
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")


@router.post("/thread/share-anyone-with-link/{agent_id}/{thread_id}", response_model=Dict[str, Any])
async def share_thread_with_anyone(
    agent_id: str,
    thread_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Generate a public link for a thread that can be accessed by anyone.
    
    This endpoint sets the thread's is_public flag to True and generates a public_hash.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get the current authenticated user's email for editor checks
        current_user_email = None
        if hasattr(request.state, 'user') and isinstance(request.state.user, dict):
            current_user_email = request.state.user.get('email')
        # Fallback if request.state directly has an email attribute (less likely based on logs)
        elif hasattr(request.state, 'email'):
             current_user_email = request.state.email

        # Get agent log by thread_id
        try:
            thread_id_str = str(thread_id)
            agent_id_str_param = str(agent_id) # Renamed to avoid conflict later
            
            log_response = (
                supabase.table("agent_logs")
                .select("agent_log_id, agent_id, chat_history")
                .eq("agent_log_id", thread_id_str)
                .eq("agent_id", agent_id_str_param)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent log: {str(e)}")
        
        if not log_response.data:
            raise NotFoundError(
                f"Thread with ID '{thread_id}' not found for agent '{agent_id}'",
                additional_info={
                    "agent_id": agent_id,
                    "thread_id": thread_id
                }
            )
        
        log = log_response.data[0]
        
        # Permission Check: User must have rights to the agent associated with this thread.
        agent_id_from_log = log.get("agent_id")
        
        if not agent_id_from_log:
            raise ForbiddenError(
                "Thread is not linked to a valid agent, cannot determine permissions.",
                additional_info={"thread_id": thread_id}
            )

        try:
            agent_response = (
                supabase.table("agents")
                .select("user_id, company_id, share_editor_with")
                .eq("agent_id", agent_id_from_log)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching agent for permission check: {str(e)}")

        if not agent_response.data:
            raise NotFoundError(
                f"Agent with ID '{agent_id_from_log}' (associated with thread '{thread_id}') not found.",
                additional_info={"agent_id": agent_id_from_log, "thread_id": thread_id}
            )
            
        agent = agent_response.data[0]
        
        # Check if the user has permission to share the agent
        is_agent_owner = agent.get("user_id") == user_id
        is_company_member_with_rights = False
        
        editors_list = agent.get("share_editor_with") or []
        is_agent_editor = False
        if current_user_email:
            is_agent_editor = current_user_email in editors_list

        if not is_agent_owner:
            if agent.get("company_id"):
                try:
                    company_id_str = str(agent["company_id"])
                    user_id_str = str(user_id) # user_id (UUID) is correct for user_companies table
                    
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id") # Role could be used for finer control, e.g. only admins
                        .eq("user_id", user_id_str)
                        .eq("company_id", company_id_str)
                        .execute()
                    )
                    
                    if user_company_response.data:
                        is_company_member_with_rights = True
                        # Potentially check role here if needed: 
                        # e.g., role = user_company_response.data[0]["role_id"]

                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            
            # If not owner, and not a company member with rights, check if they are an editor
            if not is_company_member_with_rights and not is_agent_editor:
                raise ForbiddenError(
                    "You don't have permission to make this agent public.",
                    additional_info={"agent_id": agent_id}
                )
        
        # If we reach here, permission is granted (owner, or company member, or editor)
        # Get the current chat_history and process it
        raw_chat_history_data = log.get("chat_history")

        # Initialize the standard inner object structure
        chat_history_inner_obj = {
            "messages": [],
            "share_info": {
                "share_visitor_with": [],
                "share_editor_with": [],
                "public_hash": None,
                "is_public": False
            }
        }
        
        # Temporary variables to hold parsed messages and share_info
        parsed_messages_list = []
        parsed_share_info_dict = {}

        # Try to process raw_chat_history_data
        data_to_process = raw_chat_history_data
        if isinstance(raw_chat_history_data, str):
            try:
                data_to_process = json.loads(raw_chat_history_data)
            except json.JSONDecodeError:
                data_to_process = None # Indicate bad JSON, defaults will be used

        if data_to_process is None: # Bad JSON string case
            pass # messages and share_info remain default
        elif isinstance(data_to_process, list):
            # Case 1: Data is a list
            if data_to_process and isinstance(data_to_process[0], dict) and \
               ("messages" in data_to_process[0] or "share_info" in data_to_process[0]):
                # It looks like the new format `[{"messages": ..., "share_info": ...}]`
                # Use the content of the first element.
                source_dict = data_to_process[0]
                parsed_messages_list = source_dict.get("messages", [])
                if isinstance(source_dict.get("share_info"), dict):
                    parsed_share_info_dict = source_dict["share_info"]
            else:
                # It's an old list of messages, e.g., [{msg1}, {msg2}] or []
                parsed_messages_list = data_to_process
        elif isinstance(data_to_process, dict):
            # Case 2: Data is a dictionary
            if "messages" in data_to_process:
                parsed_messages_list = data_to_process.get("messages", [])
            elif data_to_process and not ("share_info" in data_to_process and len(data_to_process) == 1):
                 parsed_messages_list = [data_to_process]
            
            if "share_info" in data_to_process and isinstance(data_to_process.get("share_info"), dict):
                parsed_share_info_dict = data_to_process["share_info"]

        # Assign parsed components to the inner object
        chat_history_inner_obj["messages"] = parsed_messages_list if isinstance(parsed_messages_list, list) else []
        
        default_share_info_copy = {
            "share_visitor_with": [], "share_editor_with": [],
            "public_hash": None, "is_public": False
        }
        default_share_info_copy.update(parsed_share_info_dict)
        chat_history_inner_obj["share_info"] = default_share_info_copy

        for key_to_be_list in ["share_visitor_with", "share_editor_with"]:
            if not isinstance(chat_history_inner_obj["share_info"].get(key_to_be_list), list):
                chat_history_inner_obj["share_info"][key_to_be_list] = []
        
        # Generate a public hash if one doesn't exist in share_info
        public_hash = chat_history_inner_obj["share_info"].get("public_hash")
        if not public_hash:
            public_hash = str(uuid.uuid4()).replace("-", "")[:16]
        
        chat_history_inner_obj["share_info"]["public_hash"] = public_hash
        chat_history_inner_obj["share_info"]["is_public"] = True
        
        # The data to be stored in the database
        final_chat_history_to_save = [chat_history_inner_obj]

        # Update the agent log in the database
        try:
            update_response = (
                supabase.table("agent_logs")
                .update({"chat_history": final_chat_history_to_save})
                .eq("agent_log_id", thread_id_str)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error updating agent log: {str(e)}")
        
        return {
            "success": True,
            "message": "Thread is now publicly accessible",
            "public_hash": chat_history_inner_obj["share_info"]["public_hash"],
            "is_public": chat_history_inner_obj["share_info"]["is_public"], 
            "share_info": chat_history_inner_obj["share_info"]
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")
