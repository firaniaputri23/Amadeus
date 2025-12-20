
from typing import List, Dict
from datetime import datetime
from supabase import Client

class ChatDatabaseService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def get_chat_history(self, agent_id: str) -> List[Dict]:
        """
        Get chat history for a specific agent from agent_logs table.
        Args:
            agent_id: The ID of the agent
        Returns:
            List of chat messages (from chat_history JSON field)
        """
        try:
            response = self.supabase.table('agent_logs') \
                .select('chat_history') \
                .eq('agent_id', agent_id) \
                .limit(1) \
                .execute()
            data = response.data
            if data and 'chat_history' in data[0]:
                chat_history_json = data[0]['chat_history']
                # If chat_history is a dict with 'messages' key, return that
                if isinstance(chat_history_json, dict) and 'messages' in chat_history_json:
                    return chat_history_json['messages']
                # If chat_history is a list of messages
                if isinstance(chat_history_json, list):
                    return chat_history_json
            return []
        except Exception as e:
            print(f"Error fetching chat history: {str(e)}")
            return [] 
