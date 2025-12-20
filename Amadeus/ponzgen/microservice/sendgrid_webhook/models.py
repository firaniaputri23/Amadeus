"""
SendGrid Webhook Models

Pydantic models for handling SendGrid inbound parser webhook data and email storage.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class EmailType(str, Enum):
    """Email type enumeration."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""
    NEED_MORE_INFO = "need_more_info"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    RESOLVED = "resolved"


class SendGridWebhookData(BaseModel):
    """
    Model for SendGrid inbound parser webhook data.
    
    SendGrid sends parsed email data as multipart/form-data.
    This model represents the key fields that are commonly sent.
    """
    # Email headers
    to: Optional[str] = Field(None, description="Recipient email address")
    from_email: Optional[str] = Field(None, alias="from", description="Sender email address")
    subject: Optional[str] = Field(None, description="Email subject")
    
    # Email content
    text: Optional[str] = Field(None, description="Plain text version of email body")
    html: Optional[str] = Field(None, description="HTML version of email body")
    
    # Additional headers
    cc: Optional[str] = Field(None, description="CC recipients")
    bcc: Optional[str] = Field(None, description="BCC recipients")
    reply_to: Optional[str] = Field(None, description="Reply-to address")
    
    # SendGrid specific fields
    dkim: Optional[str] = Field(None, description="DKIM validation result")
    spf: Optional[str] = Field(None, description="SPF validation result")
    envelope: Optional[str] = Field(None, description="SMTP envelope information")
    
    # Attachments info (simplified)
    attachment_info: Optional[Dict[str, Any]] = Field(None, description="Information about attachments")
    
    # Raw data for debugging
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw webhook data for debugging")


class EmailRecord(BaseModel):
    """
    Model for email records stored in the database.
    """
    id: Optional[UUID] = Field(None, description="Email record ID")
    email_type: EmailType = Field(..., description="Type of email (inbound/outbound)")
    from_email: str = Field(..., description="Sender email address")
    to_email: str = Field(..., description="Recipient email address")
    subject: Optional[str] = Field(None, description="Email subject")
    text_content: Optional[str] = Field(None, description="Plain text email content")
    html_content: Optional[str] = Field(None, description="HTML email content")
    message_id: Optional[str] = Field(None, description="Unique message identifier")
    sendgrid_message_id: Optional[str] = Field(None, description="SendGrid specific message ID")
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.NEED_MORE_INFO, description="Processing status")
    agent_processed: bool = Field(default=False, description="Whether agent has processed this email")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class EmailCreateRequest(BaseModel):
    """
    Model for creating new email records.
    """
    email_type: EmailType = Field(..., description="Type of email (inbound/outbound)")
    from_email: str = Field(..., description="Sender email address")
    to_email: str = Field(..., description="Recipient email address")
    subject: Optional[str] = Field(None, description="Email subject")
    text_content: Optional[str] = Field(None, description="Plain text email content")
    html_content: Optional[str] = Field(None, description="HTML email content")
    message_id: Optional[str] = Field(None, description="Unique message identifier")
    sendgrid_message_id: Optional[str] = Field(None, description="SendGrid specific message ID")
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.NEED_MORE_INFO, description="Processing status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class EmailProcessingResult(BaseModel):
    """
    Model for email processing results.
    """
    email_id: UUID = Field(..., description="Email record ID")
    processing_status: ProcessingStatus = Field(..., description="Processing status")
    agent_processed: bool = Field(..., description="Whether agent processed the email")
    agent_response: Optional[str] = Field(None, description="Agent response if processed")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class WebhookResponse(BaseModel):
    """
    Standard response model for webhook endpoints.
    """
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")


class SubjectCheckResult(BaseModel):
    """
    Model for subject existence check results.
    """
    subject_exists: bool = Field(..., description="Whether the subject exists in outbound emails")
    original_email: Optional[EmailRecord] = Field(None, description="Original outbound email if found")
    should_process: bool = Field(..., description="Whether the email should be processed")