from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
import sys
import os

# Fix the import path
from ..utils.get_llms import get_llms

def get_react_agent(model_name="custom-vlm", temperature=0, langchain_tools=[], memory=None):
    """
    Create a ReAct agent with the specified model, tools, and memory.
    
    Args:
        model_name: The name of the LLM to use
        temperature: The temperature setting for the model (0-1)
        langchain_tools: List of LangChain tools to provide to the agent
        memory: Memory instance for maintaining conversation state
        
    Returns:
        A configured ReAct agent
    """
    # model_name = "anthropic/claude-3.5-sonnet" # for tools, one of the most general model
    model = get_llms(model_name, temperature)
    
    # Create system prompt that encourages tool usage
    if langchain_tools:
        system_message = SystemMessage(content="""You are a helpful AI assistant with access to tools. 
When a user asks you to do something that requires using a tool, you MUST call the appropriate tool function immediately.
Do NOT just describe what you would do or say you'll call a function - actually invoke the tool by using the function calling mechanism.
After receiving tool results, provide them to the user in a clear, helpful format.""")
    else:
        system_message = SystemMessage(content="You are a helpful AI assistant.")
    
    return create_react_agent(model, langchain_tools, checkpointer=memory, state_modifier=system_message)
# Example usage
if __name__ == "__main__":
    from langgraph.checkpoint.memory import MemorySaver
    
    # Create memory and agent
    memory = MemorySaver()
    agent = get_react_agent(model_name="custom-vlm", memory=memory)
    
    # First interaction
    query = "My name is firania"
    config = {'thread_id': "1"}
    try:
        response = agent.invoke({"messages": query}, {"configurable": config})
        ai_message = response['messages'][-1].content
        print(ai_message)
    except Exception as e:
        print(f"Error: {e}")
    
    # Follow up question (demonstrates memory persistence)
    query = "What is my name?"
    config = {'thread_id': "1"}
    try:
        response = agent.invoke({"messages": query}, {"configurable": config})
        ai_message = response['messages'][-1].content
        print(ai_message)
    except Exception as e:
        print(f"Error: {e}")