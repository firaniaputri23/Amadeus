"""
SendGrid Webhook Database Operations

Database utilities for handling email storage and retrieval operations.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from supabase import Client
from datetime import datetime

from .models import (
    EmailRecord, 
    EmailCreateRequest, 
    EmailType, 
    ProcessingStatus,
    SubjectCheckResult,
    EmailProcessingResult
)

logger = logging.getLogger(__name__)


class EmailDatabaseService:
    """
    Service class for handling email database operations.
    """
    
    def __init__(self, supabase_client: Client):
        """
        Initialize the email database service.
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    async def check_subject_exists(self, subject: str) -> SubjectCheckResult:
        """
        Check if a subject exists in outbound emails (reply detection).
        Handles common reply prefixes like "Re:", "RE:", "Fwd:", etc.
        
        Args:
            subject: Email subject to check
            
        Returns:
            SubjectCheckResult with existence info and original email if found
        """
        try:
            # Clean the subject by removing common reply prefixes
            cleaned_subject = self._clean_subject_for_matching(subject)
            
            # Try exact match first
            response = self.supabase.rpc('check_subject_exists', {'subject_text': subject}).execute()
            subject_exists = response.data if response.data is not None else False
            original_subject_used = subject
            
            # If exact match fails, try with cleaned subject
            if not subject_exists and cleaned_subject != subject:
                response = self.supabase.rpc('check_subject_exists', {'subject_text': cleaned_subject}).execute()
                subject_exists = response.data if response.data is not None else False
                original_subject_used = cleaned_subject
            
            original_email = None
            if subject_exists:
                # Get the original email details
                original_response = self.supabase.rpc(
                    'get_original_email_by_subject',
                    {'subject_text': original_subject_used}
                ).execute()
                
                if original_response.data and len(original_response.data) > 0:
                    original_data = original_response.data[0]
                    original_email = EmailRecord(
                        id=original_data['id'],
                        email_type=EmailType.OUTBOUND,
                        from_email=original_data['from_email'],
                        to_email=original_data['to_email'],
                        subject=original_subject_used,
                        created_at=original_data['created_at']
                    )
            
            return SubjectCheckResult(
                subject_exists=subject_exists,
                original_email=original_email,
                should_process=subject_exists
            )
            
        except Exception as e:
            logger.error(f"Error checking subject existence: {str(e)}")
            return SubjectCheckResult(
                subject_exists=False,
                original_email=None,
                should_process=False
            )
    
    def _clean_subject_for_matching(self, subject: str) -> str:
        """
        Clean email subject by removing common reply/forward prefixes.
        
        Args:
            subject: Original email subject
            
        Returns:
            Cleaned subject for matching
        """
        if not subject:
            return subject
            
        # Common prefixes to remove (case insensitive)
        prefixes = [
            'Re:', 'RE:', 're:',
            'Fwd:', 'FWD:', 'fwd:', 'Fw:', 'FW:', 'fw:',
            'Reply:', 'REPLY:', 'reply:',
            'Forward:', 'FORWARD:', 'forward:'
        ]
        
        cleaned = subject.strip()
        
        # Remove prefixes iteratively (in case of multiple Re: Re: etc.)
        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
                    changed = True
                    break
        
        return cleaned
    
    async def store_email(self, email_data: EmailCreateRequest) -> Optional[EmailRecord]:
        """
        Store an email record in the database.
        
        Args:
            email_data: Email data to store
            
        Returns:
            EmailRecord if successful, None if failed
        """
        try:
            # Prepare data for insertion
            insert_data = {
                "email_type": email_data.email_type.value,
                "from_email": email_data.from_email,
                "to_email": email_data.to_email,
                "subject": email_data.subject,
                "text_content": email_data.text_content,
                "html_content": email_data.html_content,
                "message_id": email_data.message_id,
                "sendgrid_message_id": email_data.sendgrid_message_id,
                "processing_status": email_data.processing_status.value,
                "metadata": email_data.metadata or {}
            }
            
            # Insert into database
            response = self.supabase.table("emails").insert(insert_data).execute()
            
            if response.data and len(response.data) > 0:
                stored_data = response.data[0]
                return EmailRecord(
                    id=stored_data['id'],
                    email_type=EmailType(stored_data['email_type']),
                    from_email=stored_data['from_email'],
                    to_email=stored_data['to_email'],
                    subject=stored_data['subject'],
                    text_content=stored_data['text_content'],
                    html_content=stored_data['html_content'],
                    message_id=stored_data['message_id'],
                    sendgrid_message_id=stored_data['sendgrid_message_id'],
                    processing_status=ProcessingStatus(stored_data['processing_status']),
                    agent_processed=stored_data['agent_processed'],
                    created_at=stored_data['created_at'],
                    updated_at=stored_data['updated_at'],
                    metadata=stored_data['metadata']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error storing email: {str(e)}")
            return None
    
    async def update_processing_status(
        self, 
        email_id: UUID, 
        status: ProcessingStatus, 
        agent_processed: Optional[bool] = None
    ) -> bool:
        """
        Update the processing status of an email.
        
        Args:
            email_id: Email record ID
            status: New processing status
            agent_processed: Whether agent has processed the email
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the database function for better performance
            response = self.supabase.rpc(
                'update_email_processing_status',
                {
                    'email_id': str(email_id),
                    'new_status': status.value,
                    'agent_processed_flag': agent_processed
                }
            ).execute()
            
            return response.data if response.data is not None else False
            
        except Exception as e:
            logger.error(f"Error updating processing status: {str(e)}")
            return False
    
    async def get_email_by_id(self, email_id: UUID) -> Optional[EmailRecord]:
        """
        Get an email record by ID.
        
        Args:
            email_id: Email record ID
            
        Returns:
            EmailRecord if found, None otherwise
        """
        try:
            response = self.supabase.table("emails").select("*").eq("id", str(email_id)).execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                return EmailRecord(
                    id=data['id'],
                    email_type=EmailType(data['email_type']),
                    from_email=data['from_email'],
                    to_email=data['to_email'],
                    subject=data['subject'],
                    text_content=data['text_content'],
                    html_content=data['html_content'],
                    message_id=data['message_id'],
                    sendgrid_message_id=data['sendgrid_message_id'],
                    processing_status=ProcessingStatus(data['processing_status']),
                    agent_processed=data['agent_processed'],
                    created_at=data['created_at'],
                    updated_at=data['updated_at'],
                    metadata=data['metadata']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting email by ID: {str(e)}")
            return None
    
    async def get_emails_by_status(
        self, 
        status: ProcessingStatus, 
        limit: int = 100
    ) -> List[EmailRecord]:
        """
        Get emails by processing status.
        
        Args:
            status: Processing status to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of EmailRecord objects
        """
        try:
            response = (
                self.supabase.table("emails")
                .select("*")
                .eq("processing_status", status.value)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            
            emails = []
            if response.data:
                for data in response.data:
                    emails.append(EmailRecord(
                        id=data['id'],
                        email_type=EmailType(data['email_type']),
                        from_email=data['from_email'],
                        to_email=data['to_email'],
                        subject=data['subject'],
                        text_content=data['text_content'],
                        html_content=data['html_content'],
                        message_id=data['message_id'],
                        sendgrid_message_id=data['sendgrid_message_id'],
                        processing_status=ProcessingStatus(data['processing_status']),
                        agent_processed=data['agent_processed'],
                        created_at=data['created_at'],
                        updated_at=data['updated_at'],
                        metadata=data['metadata']
                    ))
            
            return emails
            
        except Exception as e:
            logger.error(f"Error getting emails by status: {str(e)}")
            return []
    
    async def store_inbound_email_from_webhook(
        self, 
        webhook_data: Dict[str, Any]
    ) -> Optional[EmailRecord]:
        """
        Store an inbound email from webhook data.
        
        Args:
            webhook_data: Raw webhook data from SendGrid
            
        Returns:
            EmailRecord if successful, None if failed
        """
        try:
            email_request = EmailCreateRequest(
                email_type=EmailType.INBOUND,
                from_email=webhook_data.get('from', ''),
                to_email=webhook_data.get('to', ''),
                subject=webhook_data.get('subject'),
                text_content=webhook_data.get('text'),
                html_content=webhook_data.get('html'),
                message_id=webhook_data.get('message_id'),
                sendgrid_message_id=webhook_data.get('sendgrid_message_id'),
                processing_status=ProcessingStatus.NEED_MORE_INFO,
                metadata={
                    'webhook_timestamp': datetime.utcnow().isoformat(),
                    'dkim': webhook_data.get('dkim'),
                    'spf': webhook_data.get('spf'),
                    'envelope': webhook_data.get('envelope'),
                    'cc': webhook_data.get('cc'),
                    'bcc': webhook_data.get('bcc'),
                    'reply_to': webhook_data.get('reply_to')
                }
            )
            
            return await self.store_email(email_request)
            
        except Exception as e:
            logger.error(f"Error storing inbound email from webhook: {str(e)}")
            return None
    
    async def store_outbound_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        text_content: Optional[str] = None,
        html_content: Optional[str] = None,
        message_id: Optional[str] = None,
        sendgrid_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[EmailRecord]:
        """
        Store an outbound email record.
        
        Args:
            from_email: Sender email address
            to_email: Recipient email address
            subject: Email subject
            text_content: Plain text content
            html_content: HTML content
            message_id: Message ID
            sendgrid_message_id: SendGrid message ID
            metadata: Additional metadata
            
        Returns:
            EmailRecord if successful, None if failed
        """
        try:
            email_request = EmailCreateRequest(
                email_type=EmailType.OUTBOUND,
                from_email=from_email,
                to_email=to_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content,
                message_id=message_id,
                sendgrid_message_id=sendgrid_message_id,
                processing_status=ProcessingStatus.WAITING_FOR_CONFIRMATION,
                metadata=metadata or {}
            )
            
            return await self.store_email(email_request)
            
        except Exception as e:
            logger.error(f"Error storing outbound email: {str(e)}")
            return None


def get_email_database_service(supabase_client: Client) -> EmailDatabaseService:
    """
    Factory function to create EmailDatabaseService instance.
    
    Args:
        supabase_client: Supabase client instance
        
    Returns:
        EmailDatabaseService instance
    """
    return EmailDatabaseService(supabase_client)