"""
Database utility functions for the avatar bucket service.
"""
from typing import Optional, Dict, Any
from supabase import Client
import logging

logger = logging.getLogger(__name__)

def update_avatar_url(
    supabase: Client,
    table_name: str,
    id_column: str,
    entity_id: str,
    avatar_url: str
) -> Dict[str, Any]:
    """
    Update the avatar URL for an entity (agent or tool) in the database.
    
    Args:
        supabase: Supabase client instance
        table_name: Name of the table to update ('agents' or 'tools')
        id_column: Name of the ID column in the table
        entity_id: ID of the entity
        avatar_url: URL of the uploaded avatar
        
    Returns:
        Dict containing the update result or error information
    """
    try:
        response = supabase.table(table_name).update({
            'avatar_url': avatar_url
        }).eq(id_column, entity_id).execute()
        
        if hasattr(response, 'data') and response.data:
            return {
                'success': True,
                'data': response.data[0] if response.data else None
            }
        else:
            error_msg = f"Failed to update {table_name} {entity_id} with avatar URL: {avatar_url}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'details': str(response.error) if hasattr(response, 'error') else 'Unknown error'
            }
    except Exception as e:
        logger.error(f"Database update error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'details': 'Database update failed'
        }
            
    except Exception as e:
        error_msg = f"Error updating {entity_type} {entity_id} with avatar URL: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'details': str(e)
        }