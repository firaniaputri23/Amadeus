"""
Agent Invoke Router

This module provides routes for agent invocation.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Tuple, Optional
from uuid import UUID
from supabase import Client

# Optional import for legacy gemma_model
try:
    from microservice.agent_backend.services import gemma_model
except ImportError:
    gemma_model = None

from ..boilerplate.agent_boilerplate import agent_boilerplate
from ..boilerplate.models import AgentInput
from ..boilerplate.errors import (
    BadRequestError, NotFoundError, ForbiddenError, 
    InternalServerError, ERROR_RESPONSES
)

# Create router
router = APIRouter(
    prefix="/agent-invoke",
    tags=["agent-invoke"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

# --- Helper Function for Multimodal ---
async def _maybe_handle_multimodal_and_augment(agent_input, max_new_tokens=None, model_name=None) -> Tuple[AgentInput, Optional[str]]:
    """
    Helper: jika agent_input berisi image_path (atau image) dan prompt_text,
    panggil VLM model dan kembalikan AgentInput yang sama tetapi dengan 'input_text' 
    di-augment/diisi dengan caption VLM.
    
    Returns:
        Tuple[AgentInput, Optional[str]]: The updated agent input and the generated caption (if any).
    """
    try:
        inp_dict = agent_input.dict() if hasattr(agent_input, "dict") else dict(agent_input)
    except Exception:
        # fallback very defensive conversion
        inp_dict = {k: getattr(agent_input, k) for k in dir(agent_input) if not k.startswith("_")}
    
    # cari kemungkinan lokasi image & prompt
    # Note: Logic pengecekan ini disesuaikan dengan struktur AgentInput yang mungkin bersarang
    # Helper to safely get value from dict or object
    def safe_get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    input_obj = inp_dict.get("input")
    
    # cari kemungkinan lokasi image & prompt
    image_path = inp_dict.get("image_path") or inp_dict.get("image")
    if not image_path and input_obj:
        image_path = safe_get(input_obj, "image_path")

    prompt_text = inp_dict.get("prompt_text") or inp_dict.get("prompt")
    if not prompt_text and input_obj:
        prompt_text = safe_get(input_obj, "prompt_text")

    if not image_path:
        return agent_input, None  # nothing to do

    # gunakan prompt_text jika ada, kalau tidak gunakan existing text (input_text)
    vlm_prompt = prompt_text or inp_dict.get("input_text")
    if not vlm_prompt and input_obj:
        vlm_prompt = safe_get(input_obj, "text") or safe_get(input_obj, "messages")

    if not vlm_prompt:
        # jika tidak ada prompt untuk VLM, kita gunakan fallback sederhana
        vlm_prompt = "Tolong jelaskan gambar ini secara singkat."

    caption = None
    try:
        # Use custom VLM if model_name is "custom-vlm", otherwise use legacy gemma_model
        if model_name and model_name.lower() == "custom-vlm":
            from microservice.agent_boilerplate.boilerplate.utils.custom_vlm_model import get_custom_vlm_model
            vlm = get_custom_vlm_model()
            caption = vlm.invoke_with_image(image_path, vlm_prompt, max_new_tokens=max_new_tokens or 64)
        elif gemma_model is not None:
            # Fallback to legacy gemma_model if available
            caption = gemma_model.generate_from_image(vlm_prompt, image_path, max_new_tokens=max_new_tokens or 64)
        else:
            # If no VLM available, use custom VLM as default
            from microservice.agent_boilerplate.boilerplate.utils.custom_vlm_model import get_custom_vlm_model
            vlm = get_custom_vlm_model()
            caption = vlm.invoke_with_image(image_path, vlm_prompt, max_new_tokens=max_new_tokens or 64)
    except FileNotFoundError as e:
        raise BadRequestError(str(e))
    except Exception as e:
        raise InternalServerError(f"VLM inference error: {str(e)}")

    # augmentasikan input_text: gabungkan caption ke existing text agar agent tetap menerima konteks text
    # Fix: Update 'context' instead of 'text' because agent_boilerplate reads 'context'
    if isinstance(inp_dict.get("input"), dict):
        current_context = inp_dict["input"].get("context", "")
        inp_dict["input"]["context"] = f"{current_context}\n\n[Image Description]: {caption}"
    
    # Fix: Reset model_name to a standard LLM if it was 'custom-vlm', 
    # because the agent execution needs a valid LLM (not the VLM itself).
    if model_name and model_name.lower() == "custom-vlm":
        if isinstance(inp_dict.get("metadata"), dict):
            # Ensure we continue using custom-vlm for the text generation phase
            inp_dict["metadata"]["model_name"] = "custom-vlm"

    # kembalikan kembali ke tipe AgentInput
    # Menggunakan parse_obj atau konstruktor tergantung versi Pydantic, di sini asumsi parse_obj/konstruktor standar
    return AgentInput.parse_obj(inp_dict), caption


@router.post("/{agent_id}/invoke", response_model=Dict[str, Any])
async def invoke_agent(
    agent_id: str,
    agent_input: AgentInput,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Invoke an agent by its agent_id.
    
    This endpoint matches the agent_id to an agent and invokes it with the provided input.
    If agent_config is provided in the request body, it will be used directly.
    Otherwise, the agent configuration will be fetched from the database.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if agent_config is provided in the request
        if agent_input.agent_config:
            print("Using agent_config from request")
            agent_config = agent_input.agent_config
            
            # Verify that the agent_id matches
            if agent_config.get("agent_id") != agent_id:
                raise BadRequestError(
                    f"agent_id in URL ({agent_id}) does not match agent_id in agent_config ({agent_config.get('agent_id')})",
                    additional_info={
                        "url_agent_id": agent_id,
                        "config_agent_id": agent_config.get("agent_id")
                    }
                )
            
            # Check if the user has access to the agent
            has_access = False
            
            # Check if the user is the owner of the agent
            if agent_config.get("user_id") == user_id:
                has_access = True
            # Check if the agent belongs to a company the user has access to
            elif agent_config.get("company_id"):
                try:
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id")
                        .eq("user_id", user_id)
                        .eq("company_id", agent_config["company_id"])
                        .execute()
                    )
                    if user_company_response.data:
                        has_access = True
                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            
            # If no access yet, check if the user's email has editor access
            if not has_access:
                # Get the user's email
                try:
                    user_response = (
                        supabase.table("users")
                        .select("email")
                        .eq("user_id", user_id)
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error fetching user email: {str(e)}")
                
                if user_response.data:
                    user_email = user_response.data[0].get("email")
                    # Check if the email is in the share_editor_with list
                    if user_email in agent_config.get("share_editor_with", []):
                        has_access = True
            
            # If still no access, deny permission
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this agent",
                    additional_info={
                        "agent_id": agent_id
                    }
                )
        else:
            print("Fetching agent_config from database")
            # Get agent by agent_id
            try:
                agent_response = (
                    supabase.table("agents")
                    .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools, share_editor_with")
                    .eq("agent_id", agent_id)
                    .eq("on_status", True)
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
            
            agent_config = agent_response.data[0]
            
            # Check if the user has access to the agent
            has_access = False
            
            # Check if the user is the owner of the agent
            if agent_config.get("user_id") == user_id:
                has_access = True
            # Check if the agent belongs to a company the user has access to
            elif agent_config.get("company_id"):
                try:
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id")
                        .eq("user_id", user_id)
                        .eq("company_id", agent_config["company_id"])
                        .execute()
                    )
                    if user_company_response.data:
                        has_access = True
                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            
            # If no access yet, check if the user's email has editor access
            if not has_access:
                # Get the user's email
                try:
                    user_response = (
                        supabase.table("users")
                        .select("email")
                        .eq("user_id", user_id)
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error fetching user email: {str(e)}")
                
                if user_response.data:
                    user_email = user_response.data[0].get("email")
                    # Check if the email is in the share_editor_with list
                    if user_email in agent_config.get("share_editor_with", []):
                        has_access = True
            
            # If still no access, deny permission
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this agent",
                    additional_info={
                        "agent_id": agent_id
                    }
                )
        
        # Invoke the agent
        try:
            # --- multimodal handling: jika request punya image -> panggil VLM lokal dan augment input_text ---
            # Ambil optional max_new_tokens dari agent_input jika tersedia
            max_new_tokens = getattr(agent_input, "max_new_tokens", None) or (getattr(agent_input, "input", {}) or {}).get("max_new_tokens", None)
            model_name = agent_input.metadata.model_name if hasattr(agent_input, "metadata") and hasattr(agent_input.metadata, "model_name") else None
            
            # Updated to unpack the tuple
            agent_input, _ = await _maybe_handle_multimodal_and_augment(agent_input, max_new_tokens=max_new_tokens, model_name=model_name)

            response = await agent_boilerplate.invoke_agent(
                agent_id=agent_id,
                agent_input=agent_input,
                agent_config=agent_config
            )
            return response
        except Exception as e:
            raise InternalServerError(f"Error invoking agent: {str(e)}")
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")


@router.post("/{agent_id}/invoke-stream", response_model=Dict[str, Any])
async def invoke_agent_stream(
    agent_id: str,
    agent_input: AgentInput,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Invoke an agent by its agent_id with streaming response.
    
    This endpoint matches the agent_id to an agent and invokes it with the provided input.
    If agent_config is provided in the request body, it will be used directly.
    Otherwise, the agent configuration will be fetched from the database.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Check if agent_config is provided in the request
        if agent_input.agent_config:
            print("Using agent_config from request")
            agent_config = agent_input.agent_config
            
            # Verify that the agent_id matches
            if agent_config.get("agent_id") != agent_id:
                raise BadRequestError(
                    f"agent_id in URL ({agent_id}) does not match agent_id in agent_config ({agent_config.get('agent_id')})",
                    additional_info={
                        "url_agent_id": agent_id,
                        "config_agent_id": agent_config.get("agent_id")
                    }
                )
            
            # Check if the user has access to the agent
            has_access = False
            
            # Check if the user is the owner of the agent
            if agent_config.get("user_id") == user_id:
                has_access = True
            # Check if the agent belongs to a company the user has access to
            elif agent_config.get("company_id"):
                try:
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id")
                        .eq("user_id", user_id)
                        .eq("company_id", agent_config["company_id"])
                        .execute()
                    )
                    if user_company_response.data:
                        has_access = True
                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            
            # If no access yet, check if the user's email has editor access
            if not has_access:
                # Get the user's email
                try:
                    user_response = (
                        supabase.table("users")
                        .select("email")
                        .eq("user_id", user_id)
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error fetching user email: {str(e)}")
                
                if user_response.data:
                    user_email = user_response.data[0].get("email")
                    # Check if the email is in the share_editor_with list
                    if user_email in agent_config.get("share_editor_with", []):
                        has_access = True
            
            # If still no access, deny permission
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this agent",
                    additional_info={
                        "agent_id": agent_id
                    }
                )
        else:
            print("Fetching agent_config from database")
            # Get agent by agent_id
            try:
                agent_response = (
                    supabase.table("agents")
                    .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools, share_editor_with")
                    .eq("agent_id", agent_id)
                    .eq("on_status", True)
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
            
            agent_config = agent_response.data[0]
            
            # Check if the user has access to the agent
            has_access = False
            
            # Check if the user is the owner of the agent
            if agent_config.get("user_id") == user_id:
                has_access = True
            # Check if the agent belongs to a company the user has access to
            elif agent_config.get("company_id"):
                try:
                    user_company_response = (
                        supabase.table("user_companies")
                        .select("role_id")
                        .eq("user_id", user_id)
                        .eq("company_id", agent_config["company_id"])
                        .execute()
                    )
                    if user_company_response.data:
                        has_access = True
                except Exception as e:
                    raise InternalServerError(f"Error checking company access: {str(e)}")
            
            # If no access yet, check if the user's email has editor access
            if not has_access:
                # Get the user's email
                try:
                    user_response = (
                        supabase.table("users")
                        .select("email")
                        .eq("user_id", user_id)
                        .execute()
                    )
                except Exception as e:
                    raise InternalServerError(f"Error fetching user email: {str(e)}")
                
                if user_response.data:
                    user_email = user_response.data[0].get("email")
                    # Check if the email is in the share_editor_with list
                    if user_email in agent_config.get("share_editor_with", []):
                        has_access = True
            
            # If still no access, deny permission
            if not has_access:
                raise ForbiddenError(
                    "You don't have access to this agent",
                    additional_info={
                        "agent_id": agent_id
                    }
                )
        
        # Invoke the agent (streaming)
        # If multimodal: generate caption first then stream the regular pipeline
        try:
            print("DEBUG: invoke_agent_stream endpoint hit!")
            
            async def stream_with_vlm():
                import json
                
                # handle multimodal augmentation before streaming
                max_new_tokens = getattr(agent_input, "max_new_tokens", None) or (getattr(agent_input, "input", {}) or {}).get("max_new_tokens", None)
                model_name = agent_input.metadata.model_name if hasattr(agent_input, "metadata") and hasattr(agent_input.metadata, "model_name") else None
                
                # Check if there's an image before showing VLM status
                image_path = None
                if hasattr(agent_input, 'input'):
                    if hasattr(agent_input.input, 'dict') and callable(agent_input.input.dict):
                        input_dict = agent_input.input.dict()
                    else:
                        input_dict = agent_input.input if isinstance(agent_input.input, dict) else dict(agent_input.input)
                    image_path = input_dict.get('image_path')
                
                if image_path:
                    # Yield initial status only if there's an image
                    yield f"event: status\ndata: {json.dumps({'status': 'Analyzing image...'})}\n\n"
                
                # Call helper, now unpacking the tuple
                updated_agent_input, caption = await _maybe_handle_multimodal_and_augment(agent_input, max_new_tokens=max_new_tokens, model_name=model_name)
                
                # Use the returned caption directly
                if caption:
                    # Yield the caption as a special event or just info
                    yield f"event: status\ndata: {json.dumps({'status': 'Image analyzed'})}\n\n"
                    
                    # --- CRITICAL CHANGE: Stream caption as 'token' events so it shows in chat ---
                    vlm_prefix = "**[VLM Analysis]**:"
                    yield f"event: token\ndata: {json.dumps({'token': f'{vlm_prefix} {caption}'})}\n\n"
                    
                    separator = "\n\n---\n\n"
                    yield f"event: token\ndata: {json.dumps({'token': separator})}\n\n"
                    # --------------------------------------------------------------------------
                    
                    # Check if the user query is empty or just a placeholder dot
                    input_msg = ""
                    # Robust extraction of messages
                    try:
                        raw_msg = None
                        if isinstance(agent_input.input, dict):
                            raw_msg = agent_input.input.get('messages')
                        else:
                            raw_msg = getattr(agent_input.input, 'messages', None)
                        
                        input_msg = str(raw_msg).strip() if raw_msg is not None else ""
                    except Exception as e:
                        print(f"DEBUG: Error extracting input messages: {e}")
                        input_msg = ""
                    
                    print(f"DEBUG: VLM Check - Input msg: '{input_msg}'")

                    # If query is empty or just ".", we treat this as "Image Description Only" task
                    if not input_msg or input_msg == "." or input_msg == "None":
                        print("DEBUG: Empty query with image. Skipping agent execution and returning VLM caption only.")
                        yield f"event: status\ndata: {json.dumps({'status': 'Agent Execution End', 'final_answer': caption})}\n\n"
                        return

                # Now stream the agent execution
                print("DEBUG: Starting agent stream...")
                async for chunk in agent_boilerplate.invoke_agent_stream(
                    agent_id=agent_id,
                    agent_input=updated_agent_input,
                    agent_config=agent_config
                ):
                    print(f"DEBUG: Yielding chunk: {chunk[:100]}...")
                    yield chunk

            return StreamingResponse(
                stream_with_vlm(),
                media_type="text/event-stream"
            )
        except Exception as e:
            raise InternalServerError(f"Unexpected error while streaming: {str(e)}")
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")
    

@router.get("/{agent_id}/info")
async def get_agent_info(
    agent_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get information about an agent.
    
    This endpoint returns basic information about an agent, such as its name,
    description, and style. It does not include sensitive information.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Get agent by agent_id
        try:
            agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools, share_editor_with, share_visitor_with")
                .eq("agent_id", agent_id)
                .eq("on_status", True)
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
        
        agent_config = agent_response.data[0]
        
        # Check if the user has access to the agent
        has_access = False
        access_level = "none"
        
        # Check if the user is the owner of the agent
        if agent_config.get("user_id") == user_id:
            has_access = True
            access_level = "owner"
        # Check if the agent belongs to a company the user has access to
        elif agent_config.get("company_id"):
            try:
                user_company_response = (
                    supabase.table("user_companies")
                    .select("role_id")
                    .eq("user_id", user_id)
                    .eq("company_id", agent_config["company_id"])
                    .execute()
                )
                if user_company_response.data:
                    has_access = True
                    access_level = "company"
            except Exception as e:
                raise InternalServerError(f"Error checking company access: {str(e)}")
        
        # If no access yet, check if the user's email has editor or visitor access
        if not has_access:
            # Get the user's email
            try:
                user_response = (
                    supabase.table("users")
                    .select("email")
                    .eq("user_id", user_id)
                    .execute()
                )
            except Exception as e:
                raise InternalServerError(f"Error fetching user email: {str(e)}")
            
            if user_response.data:
                user_email = user_response.data[0].get("email")
                # Check if the email is in the share_editor_with list
                if user_email in agent_config.get("share_editor_with", []):
                    has_access = True
                    access_level = "editor"
                # Check if the email is in the share_visitor_with list
                elif user_email in agent_config.get("share_visitor_with", []):
                    has_access = True
                    access_level = "visitor"
        
        # If still no access, deny permission
        if not has_access:
            raise ForbiddenError(
                "You don't have access to this agent",
                additional_info={
                    "agent_id": agent_id
                }
            )
        
        # Return basic information about the agent
        return {
            "agent_name": agent_config["agent_name"],
            "description": agent_config.get("description"),
            "agent_style": agent_config.get("agent_style"),
            "on_status": agent_config.get("on_status", True),
            "tools_count": len(agent_config.get("tools", [])),
            "access_level": access_level
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")


@router.get("/shared-agent/{agent_hash}")
async def get_shared_agent(
    agent_hash: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get a shared agent by its public hash.
    This endpoint can be accessed without JWT authentication.
    """
    try:
        # Search for the agent with this hash
        try:
            # Look for agents with a matching public_hash
            print(f"Looking up agent with public_hash: {agent_hash}")
            agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, tools, share_editor_with, share_visitor_with, is_public, public_hash")
                .eq("public_hash", agent_hash)
                .eq("is_public", True)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching shared agent: {str(e)}")
        
        if not agent_response.data:
            print(f"No agent found for public_hash: {agent_hash}. agent_response: {agent_response}")
            # If we didn't find the agent in the agents table, return a not found error
            raise NotFoundError(f"Shared agent with hash '{agent_hash}' not found or not public")
        
        agent = agent_response.data[0]
        
        # Get tool details
        tool_details = []
        for tool_id in agent.get("tools", []):
            print(f"Looking up tool_id: {tool_id}")
            try:
                tool_response = (
                    supabase.table("tools_with_decrypted_keys")
                    .select("tool_id, name, description, versions")
                    .eq("tool_id", tool_id)
                    .execute()
                )
                print(f"tool_response for {tool_id}: {tool_response}")
            except Exception as e:
                print(f"Error fetching tool details for {tool_id}: {str(e)}")
                raise InternalServerError(f"Error fetching tool details: {str(e)}")
            
            if tool_response.data:
                tool_details.append(tool_response.data[0])
        
        # Fetch the latest chat_history from agent_logs
        chat_history = []
        try:
            log_response = (
                supabase.table("agent_logs")
                .select("chat_history")
                .eq("agent_id", agent["agent_id"])
                .order("date", desc=True)
                .limit(1)
                .execute()
            )
            if log_response.data and "chat_history" in log_response.data[0]:
                chat_history = log_response.data[0]["chat_history"] or []
        except Exception as e:
            print(f"Error fetching chat history for agent {agent['agent_id']}: {str(e)}")
            chat_history = []

        return {
            "agent_id": agent["agent_id"],
            "agent_name": agent["agent_name"],
            "description": agent.get("description"),
            "agent_style": agent.get("agent_style"),
            "on_status": agent.get("on_status", True),
            "company_id": agent.get("company_id"),
            "tools": tool_details,
            "chat_history": chat_history,
            "is_shared": True,
            "read_only": True
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.get("/shared-thread/{thread_hash}")
async def get_shared_thread(
    thread_hash: str,
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get a shared thread by its public hash.
    This endpoint can be accessed without JWT authentication.
    """
    try:
        # Search for the thread with this hash
        try:
            logs_response = (
                supabase.table("agent_logs")
                .select("agent_log_id, date, chat_history, agent_id")
                .eq(f"chat_history->0->share_info->>public_hash", thread_hash)
                .eq(f"chat_history->0->share_info->>is_public", "true") # JSON boolean true becomes text "true" via ->>
                .order("date", desc=True)  # Get the latest if multiple (should be unique by hash)
                .limit(1)
                .execute()
            )
        except Exception as e:
            raise InternalServerError(f"Error fetching shared thread: {str(e)}")
        
        if not logs_response.data:
            raise NotFoundError(f"Shared thread with hash '{thread_hash}' not found or not public")
        
        found_log = logs_response.data[0]
        chat_history_payload = found_log.get("chat_history")
        
        # Get agent info if available
        agent_info = {}
        if found_log.get("agent_id"):
            try:
                agent_response = (
                    supabase.table("agents")
                    .select("agent_id, agent_name, description, agent_style")
                    .eq("agent_id", found_log["agent_id"])
                    .execute()
                )
                
                if agent_response.data:
                    agent_info = {
                        "agent_id": agent_response.data[0]["agent_id"],
                        "agent_name": agent_response.data[0]["agent_name"],
                        "description": agent_response.data[0].get("description"),
                        "agent_style": agent_response.data[0].get("agent_style")
                    }
            except Exception as e:
                # Just log the error, we can still return the thread without agent info
                print(f"Error fetching agent info: {str(e)}")
        
        return {
            "agent_log_id": found_log.get("agent_log_id"),
            "date": found_log.get("date"),
            "chat_history": chat_history_payload,  # Return chat_history payload
            "agent": agent_info,
            "is_shared": True,
            "read_only": True
        }
    
    except (BadRequestError, NotFoundError, ForbiddenError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")