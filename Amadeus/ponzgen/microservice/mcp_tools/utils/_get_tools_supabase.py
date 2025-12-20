import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client

def get_all_tools() -> List[Dict[str, Any]]:
    """
    Simple function to get all tools from Supabase.
    
    Returns:
        List of tool dictionaries from the database with decrypted API keys
    """
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and key must be provided in environment variables")
    
    # Initialize Supabase client
    supabase = create_client(supabase_url, supabase_key)
    
    # Get all tools from the database with decrypted API keys
    response = (
        supabase.table("tools_with_decrypted_keys")
        .select("*")
        .execute()
    )
    
    # Return the data
    return response.data

# Example usage
if __name__ == "__main__":

    tools = get_all_tools()
    

    for i, tool in enumerate(tools):
        print(f"Tool {i+1}:")
        print(tool)
        print("\n")