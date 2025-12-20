"""
SendGrid Webhook Route Handler

Enhanced webhook endpoint to receive, process, and store SendGrid inbound parser data.
Implements reply detection and agent processing workflow.
"""

from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import logging
import json
import os
from datetime import datetime, timezone
from supabase import Client

from ..models import WebhookResponse, EmailProcessingResult, ProcessingStatus
from ..database import get_email_database_service, EmailDatabaseService

# Import agent boilerplate components for agent invocation
from microservice.agent_boilerplate.boilerplate.models import (
    AgentInput, AgentInputMessage, AgentInputConfig, AgentInputMetadata
)
from microservice.agent_boilerplate.boilerplate.agent_boilerplate import agent_boilerplate

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/sendgrid", tags=["SendGrid Webhook"])


# Dependency to get Supabase client
def get_supabase_client(request: Request) -> Client:
    """Get Supabase client from app state."""
    return request.app.state.supabase


# Dependency to get email database service
def get_email_db_service(
    supabase: Client = Depends(get_supabase_client)
) -> EmailDatabaseService:
    """Get email database service."""
    return get_email_database_service(supabase)


async def process_with_agent(webhook_data: Dict[str, Any], email_id: str) -> Dict[str, Any]:
    """
    Process email with agent using SendGrid tools.
    
    This function integrates with the existing agent system to process incoming emails.
    It uses the agent invocation patterns and SendGrid MCP tools.
    
    Args:
        webhook_data: Email data from webhook
        email_id: Email record ID
        
    Returns:
        Agent processing result
    """
    try:
        # Prepare email data for agent processing
        email_content = {
            "from": webhook_data.get('from', ''),
            "to": webhook_data.get('to', ''),
            "subject": webhook_data.get('subject', ''),
            "text": webhook_data.get('text', ''),
            "html": webhook_data.get('html', ''),
            "email_id": email_id
        }
        
        # Real agent invocation implementation
        agent_id = "966dcbb6-2553-494f-ba15-af5dba258c6d"
        
        try:
            # Format email content for agent processing
            formatted_message = f"""Process this incoming email and provide an appropriate response:

From: {email_content['from']}
To: {email_content['to']}
Subject: {email_content['subject']}
Content: {email_content['text']}

Please analyze this email and determine the appropriate action to take."""

            # Create agent input structure
            agent_input = AgentInput(
                input=AgentInputMessage(
                    messages=formatted_message,
                    context="Email processing and response generation"
                ),
                config=AgentInputConfig(
                    configurable={"thread_id": f"email_{email_id}"}
                ),
                metadata=AgentInputMetadata(
                    model_name="custom-vlm",
                    reset_memory=False
                )
            )
            
            # Get Supabase client for agent configuration
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                raise Exception("Supabase credentials not configured")
            
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            
            # Fetch agent configuration from database
            agent_response = (
                supabase.table("agents")
                .select("agent_id, agent_name, description, agent_style, on_status, company_id, user_id, tools, share_editor_with")
                .eq("agent_id", agent_id)
                .eq("on_status", True)
                .execute()
            )
            
            if not agent_response.data:
                raise Exception(f"Agent with ID '{agent_id}' not found or inactive")
            
            agent_config = agent_response.data[0]
            
            # Get tool details for the agent
            tool_details = []
            for tool_id in agent_config.get("tools", []):
                try:
                    tool_response = (
                        supabase.table("tools_with_decrypted_keys")
                        .select("tool_id, name, description, versions")
                        .eq("tool_id", tool_id)
                        .execute()
                    )
                    if tool_response.data:
                        tool_details.append(tool_response.data[0])
                except Exception as e:
                    logger.warning(f"Error fetching tool details for {tool_id}: {str(e)}")
            
            # Add tool details to agent config
            agent_config["tool_details"] = tool_details
            
            # Invoke the agent using the boilerplate system
            result = await agent_boilerplate.invoke_agent(
                agent_id=agent_id,
                agent_input=agent_input,
                agent_config=agent_config
            )
            
            # Process the agent response
            if result and result.get("messages"):
                # Extract the final message from the agent response
                final_message = ""
                for message in result.get("messages", []):
                    if hasattr(message, 'content') and message.content:
                        final_message += str(message.content) + " "
                
                agent_response = {
                    "status": "processed",
                    "response": final_message.strip() or "Email processed successfully by agent",
                    "action_taken": "agent_processed",
                    "agent_output": result,
                    "email_data": email_content,
                    "processing_time": datetime.now(timezone.utc).isoformat(),
                    "agent_id": agent_id,
                    "tools_available": len(tool_details)
                }
                
                return agent_response
            else:
                raise Exception("Agent returned empty or invalid response")
                
        except Exception as e:
            logger.error(f"Error invoking agent {agent_id}: {str(e)}")
            return {
                "status": "error",
                "error": f"Agent processing failed: {str(e)}",
                "processing_time": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "email_data": email_content
            }
        
    except Exception as e:
        logger.error(f"Error processing email with agent: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "processing_time": datetime.utcnow().isoformat()
        }


@router.post("/webhook", response_model=WebhookResponse)
async def sendgrid_webhook(
    request: Request,
    email_db: EmailDatabaseService = Depends(get_email_db_service)
):
    """
    Enhanced SendGrid inbound parser webhook endpoint.
    
    This endpoint:
    1. Receives parsed email data from SendGrid
    2. Checks if the subject exists in outbound emails (reply detection)
    3. Stores inbound emails if they are replies
    4. Processes emails with agent if they are replies
    5. Updates processing status accordingly
    
    Returns:
        WebhookResponse: Processing result with details
    """
    try:
        # Get the raw request body for debugging
        body = await request.body()
        
        # Parse form data
        form_data = await request.form()
        
        # Convert form data to dictionary
        webhook_data = {}
        for key, value in form_data.items():
            webhook_data[key] = value
        
        # Log the received data
        logger.info("=== SendGrid Webhook Received ===")
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info(f"Content-Type: {request.headers.get('content-type', 'Unknown')}")
        logger.info(f"User-Agent: {request.headers.get('user-agent', 'Unknown')}")
        
        # Extract key email fields
        subject = webhook_data.get('subject', '')
        from_email = webhook_data.get('from', '')
        to_email = webhook_data.get('to', '')
        
        # Log key email fields
        logger.info(f"From: {from_email}")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        
        if 'text' in webhook_data:
            logger.info(f"Text Body Length: {len(str(webhook_data['text']))} characters")
        if 'html' in webhook_data:
            logger.info(f"HTML Body Length: {len(str(webhook_data['html']))} characters")
        
        # Step 1: Check if subject exists in database (reply detection)
        logger.info("=== Checking Subject for Reply Detection ===")
        logger.info(f"Original subject: '{subject}'")
        
        subject_check = await email_db.check_subject_exists(subject)
        
        if not subject_check.should_process:
            logger.info(f"Subject '{subject}' not found in outbound emails - skipping processing")
            logger.info("=== End SendGrid Webhook (Skipped) ===")
            
            return WebhookResponse(
                status="skipped",
                message="Email is not a reply to our outbound email - processing skipped",
                data={
                    "subject": subject,
                    "from_email": from_email,
                    "reason": "subject_not_found",
                    "fields_received": list(webhook_data.keys())
                }
            )
        
        logger.info(f"Subject '{subject}' found - this is a reply, proceeding with processing")
        if subject_check.original_email:
            logger.info(f"Original email from: {subject_check.original_email.from_email}")
            logger.info(f"Original email to: {subject_check.original_email.to_email}")
            logger.info(f"Original email created: {subject_check.original_email.created_at}")
        
        # Step 2: Store inbound email in database
        logger.info("=== Storing Inbound Email ===")
        stored_email = await email_db.store_inbound_email_from_webhook(webhook_data)
        
        if not stored_email:
            logger.error("Failed to store inbound email in database")
            return WebhookResponse(
                status="error",
                message="Failed to store email in database",
                data={
                    "subject": subject,
                    "from_email": from_email,
                    "error": "database_storage_failed"
                }
            )
        
        logger.info(f"Inbound email stored with ID: {stored_email.id}")
        
        # Step 3: Process with agent
        logger.info("=== Processing with Agent ===")
        agent_result = await process_with_agent(webhook_data, str(stored_email.id))
        
        # Step 4: Update processing status based on agent result
        if agent_result.get("status") == "processed":
            # Agent processed successfully
            success = await email_db.update_processing_status(
                stored_email.id,
                ProcessingStatus.RESOLVED,
                agent_processed=True
            )
            
            if success:
                logger.info("Email processing completed successfully")
                final_status = "resolved"
                final_message = "Email reply processed successfully by agent"
            else:
                logger.error("Failed to update processing status to resolved")
                final_status = "processed_but_update_failed"
                final_message = "Agent processed email but failed to update status"
        else:
            # Agent processing failed
            success = await email_db.update_processing_status(
                stored_email.id,
                ProcessingStatus.NEED_MORE_INFO,
                agent_processed=False
            )
            
            final_status = "agent_processing_failed"
            final_message = f"Agent processing failed: {agent_result.get('error', 'Unknown error')}"
        
        logger.info("=== End SendGrid Webhook (Processed) ===")
        
        # Return success response with processing details
        return WebhookResponse(
            status=final_status,
            message=final_message,
            data={
                "email_id": str(stored_email.id),
                "subject": subject,
                "from_email": from_email,
                "to_email": to_email,
                "processing_status": stored_email.processing_status.value,
                "agent_processed": agent_result.get("status") == "processed",
                "agent_response": agent_result.get("response"),
                "original_email_id": str(subject_check.original_email.id) if subject_check.original_email else None,
                "fields_received": list(webhook_data.keys()),
                "total_fields": len(webhook_data)
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing SendGrid webhook: {str(e)}")
        logger.error(f"Request headers: {dict(request.headers)}")
        
        # Return error response but still acknowledge receipt
        return WebhookResponse(
            status="error",
            message=f"Webhook received but processing failed: {str(e)}",
            data={
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/outbound", response_model=WebhookResponse)
async def store_outbound_email(
    request: Request,
    email_db: EmailDatabaseService = Depends(get_email_db_service)
):
    """
    Store outbound email for reply tracking.
    
    This endpoint should be called when sending emails to track them
    for reply detection in the webhook.
    
    Expected JSON body:
    {
        "from_email": "support@company.com",
        "to_email": "customer@example.com",
        "subject": "Your Support Request #12345",
        "text_content": "Email text content...",
        "html_content": "<p>Email HTML content...</p>",
        "message_id": "unique_message_id",
        "sendgrid_message_id": "sendgrid_msg_id",
        "metadata": {"additional": "data"}
    }
    
    Returns:
        WebhookResponse: Storage result
    """
    try:
        # Parse JSON body
        body = await request.json()
        
        # Validate required fields
        required_fields = ["from_email", "to_email", "subject"]
        missing_fields = [field for field in required_fields if not body.get(field)]
        
        if missing_fields:
            return WebhookResponse(
                status="error",
                message=f"Missing required fields: {', '.join(missing_fields)}",
                data={"missing_fields": missing_fields}
            )
        
        # Store outbound email
        stored_email = await email_db.store_outbound_email(
            from_email=body["from_email"],
            to_email=body["to_email"],
            subject=body["subject"],
            text_content=body.get("text_content"),
            html_content=body.get("html_content"),
            message_id=body.get("message_id"),
            sendgrid_message_id=body.get("sendgrid_message_id"),
            metadata=body.get("metadata", {})
        )
        
        if stored_email:
            logger.info(f"Outbound email stored with ID: {stored_email.id}")
            logger.info(f"Subject: {stored_email.subject}")
            logger.info(f"From: {stored_email.from_email} To: {stored_email.to_email}")
            
            return WebhookResponse(
                status="success",
                message="Outbound email stored successfully for reply tracking",
                data={
                    "email_id": str(stored_email.id),
                    "subject": stored_email.subject,
                    "from_email": stored_email.from_email,
                    "to_email": stored_email.to_email,
                    "processing_status": stored_email.processing_status.value
                }
            )
        else:
            return WebhookResponse(
                status="error",
                message="Failed to store outbound email",
                data={"error": "database_storage_failed"}
            )
            
    except json.JSONDecodeError:
        return WebhookResponse(
            status="error",
            message="Invalid JSON in request body",
            data={"error": "invalid_json"}
        )
    except Exception as e:
        logger.error(f"Error storing outbound email: {str(e)}")
        return WebhookResponse(
            status="error",
            message=f"Failed to store outbound email: {str(e)}",
            data={"error": str(e)}
        )


@router.get("/emails/{email_id}")
async def get_email(
    email_id: str,
    email_db: EmailDatabaseService = Depends(get_email_db_service)
):
    """
    Get email record by ID.
    
    Args:
        email_id: Email record UUID
        
    Returns:
        Email record details
    """
    try:
        from uuid import UUID
        email_uuid = UUID(email_id)
        
        email_record = await email_db.get_email_by_id(email_uuid)
        
        if email_record:
            return {
                "status": "success",
                "data": {
                    "id": str(email_record.id),
                    "email_type": email_record.email_type.value,
                    "from_email": email_record.from_email,
                    "to_email": email_record.to_email,
                    "subject": email_record.subject,
                    "text_content": email_record.text_content,
                    "html_content": email_record.html_content,
                    "processing_status": email_record.processing_status.value,
                    "agent_processed": email_record.agent_processed,
                    "created_at": email_record.created_at,
                    "updated_at": email_record.updated_at,
                    "metadata": email_record.metadata
                }
            }
        else:
            raise HTTPException(status_code=404, detail="Email not found")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email ID format")
    except Exception as e:
        logger.error(f"Error getting email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails/status/{status}")
async def get_emails_by_status(
    status: str,
    limit: int = 100,
    email_db: EmailDatabaseService = Depends(get_email_db_service)
):
    """
    Get emails by processing status.
    
    Args:
        status: Processing status (need_more_info, waiting_for_confirmation, resolved)
        limit: Maximum number of records to return
        
    Returns:
        List of email records
    """
    try:
        from ..models import ProcessingStatus
        
        # Validate status
        try:
            processing_status = ProcessingStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in ProcessingStatus]}"
            )
        
        emails = await email_db.get_emails_by_status(processing_status, limit)
        
        return {
            "status": "success",
            "data": {
                "emails": [
                    {
                        "id": str(email.id),
                        "email_type": email.email_type.value,
                        "from_email": email.from_email,
                        "to_email": email.to_email,
                        "subject": email.subject,
                        "processing_status": email.processing_status.value,
                        "agent_processed": email.agent_processed,
                        "created_at": email.created_at,
                        "updated_at": email.updated_at
                    }
                    for email in emails
                ],
                "count": len(emails),
                "status_filter": status,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting emails by status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/emails/{email_id}/status")
async def update_email_status(
    email_id: str,
    request: Request,
    email_db: EmailDatabaseService = Depends(get_email_db_service)
):
    """
    Update email processing status.
    
    Expected JSON body:
    {
        "status": "resolved",
        "agent_processed": true
    }
    
    Args:
        email_id: Email record UUID
        
    Returns:
        Update result
    """
    try:
        from uuid import UUID
        from ..models import ProcessingStatus
        
        email_uuid = UUID(email_id)
        body = await request.json()
        
        # Validate status
        status_value = body.get("status")
        if not status_value:
            raise HTTPException(status_code=400, detail="Status is required")
        
        try:
            new_status = ProcessingStatus(status_value)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in ProcessingStatus]}"
            )
        
        agent_processed = body.get("agent_processed")
        
        success = await email_db.update_processing_status(
            email_uuid,
            new_status,
            agent_processed
        )
        
        if success:
            return {
                "status": "success",
                "message": "Email status updated successfully",
                "data": {
                    "email_id": email_id,
                    "new_status": status_value,
                    "agent_processed": agent_processed
                }
            }
        else:
            raise HTTPException(status_code=404, detail="Email not found or update failed")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email ID format")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        logger.error(f"Error updating email status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/test", response_model=WebhookResponse)
async def test_webhook():
    """
    Test endpoint to verify the webhook is accessible.
    
    Returns:
        WebhookResponse: Test response
    """
    return WebhookResponse(
        status="success",
        message="SendGrid webhook endpoint is accessible",
        data={"endpoint": "/sendgrid/webhook", "method": "POST"}
    )


@router.post("/webhook/simple")
async def simple_webhook(request: Request):
    """
    Ultra-simple webhook endpoint that just returns 200 OK.
    
    Use this if you just need to acknowledge receipt without processing.
    """
    try:
        # Log basic info
        logger.info(f"Simple webhook called at {datetime.utcnow().isoformat()}")
        
        # Return simple 200 response
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error in simple webhook: {str(e)}")
        return {"status": "error", "message": str(e)}