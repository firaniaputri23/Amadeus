"""
Agent Boilerplate Module

This module handles agent creation, configuration loading, and invocation.
It is designed to be a standalone module that can be used by other modules
like agent_router.py for routing and management.

The module provides a central place for agent-related functionality, including:
- Memory management for agent conversations
- Input parsing and formatting
- Agent invocation with configurable model selection
- Tool integration
"""

from typing import Dict, Any, Tuple, List, Optional
import json
from pathlib import Path
import os
import sys
from datetime import datetime, timezone
from supabase import create_client, Client
import uuid

# Import from the current package
from .models import AgentInput
from .agent_templates.react_agent import get_react_agent
from .agent_templates.react_text_agent import get_react_text_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessageChunk, BaseMessage, AIMessage, ToolMessage
from langchain_core.callbacks import UsageMetadataCallbackHandler


class AgentBoilerplate:
    """
    Handles agent creation, configuration loading, and invocation.
    This class is responsible for the core agent functionality.
    """
    
    def __init__(self):
        """
        Initialize the AgentBoilerplate.
        
        Sets up the memory management system and tool manager reference.
        """
        # Dictionary to store agent-specific conversation memories
        self.agent_memories: Dict[str, MemorySaver] = {}
    
    def get_or_create_memory(self, agent_id: str) -> MemorySaver:
        """
        Get an existing memory for an agent or create a new one if it doesn't exist.
        
        This ensures each agent has its own persistent conversation memory.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            MemorySaver instance for the agent
        """
        if agent_id not in self.agent_memories:
            self.agent_memories[agent_id] = MemorySaver()
        return self.agent_memories[agent_id]
    
    def reset_memory(self, agent_id: str) -> MemorySaver:
        """
        Reset the memory for an agent.
        
        This clears the conversation history and starts fresh.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            New MemorySaver instance for the agent
        """
        self.agent_memories[agent_id] = MemorySaver()
        return self.agent_memories[agent_id]
    
    def parse_agent_input(self, agent_input: AgentInput, agent_config: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Parse agent input into a final message and config.
        
        Args:
            agent_input: The input for the agent
            agent_config: Optional agent configuration
            
        Returns:
            Tuple of (final_message, config)
        """
        # Extract configuration from input
        config = agent_input.config.configurable
        
        # Extract message components
        query = str(agent_input.input.messages)
        context = str(agent_input.input.context).strip()
        
        # Get agent style directly from agent_input
        agent_style_1 = str(agent_config.get("agent_style", ""))
        agent_style_2 = str(agent_input.metadata.agent_style).strip()

        # Construct the final message with all components
        final_message = f"You are agent that follow this instruction: \n Query: {query}."
        
        # Add optional components if they exist and are valid
        has_agent_style = False
        if agent_style_1 and agent_style_1 != "string":
            final_message += f"\nAgent Style or instruction: {agent_style_1}."
            has_agent_style = True
        if agent_style_2 and agent_style_2 != "string":
            final_message += f"\nAdditional Agent Style or instruction: {agent_style_2}."
            has_agent_style = True
        
        # Add default system prompt if no agent style is provided
        if not has_agent_style:
            final_message += "\nAgent Style or instruction: You are a helpful AI assistant. Provide clear, concise, and accurate responses to user queries."
        
        if context and context != "string":
            final_message += f"\nInformation / Context: {context}."
        
        return final_message, config
    
    def _parse_tools(self, agent_config_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Parse tool details from agent_config_data and create tool_list_mcp.
        
        Args:
            agent_config_data: The agent configuration data
            
        Returns:
            Tuple of (has_tools, mcp_config)
        """
        has_tools = False
        mcp_config = {}
        
        if agent_config_data.get("tool_details") and len(agent_config_data.get("tool_details", [])) > 0:
            for tool in agent_config_data.get("tool_details", []):
                if tool.get("versions") and len(tool.get("versions", [])) > 0:
                    # Get the latest version (last in the list)
                    latest_version = tool.get("versions", [])[-1]
                    
                    if latest_version.get("released"):
                        tool_name = tool.get("name", "unknown_tool")
                        released_config = latest_version.get("released", {})
                        port = released_config.get("port", "10001")
                        # Create tool configuration
                        mcp_config[tool_name] = {
                            "url": f"http://localhost:{port}/sse",
                            "transport": released_config.get("transport", "sse"),
                        }

                        # # Add or update all environment variables from the config's env
                        # if "env" in released_config:
                        #     # Create environment dictionary
                        #     env = os.environ.copy()
                        #     for key, value in released_config.get("env", {}).items():
                        #         env[key] = value
                        #     mcp_config[tool_name]["env"] = env

                        has_tools = True
        
        return has_tools, mcp_config
    
    async def _log_interaction(self, agent_id: str, thread_id: str, model_name: str, temperature: float,
                               prompt_tokens: int, completion_tokens: int, total_tokens: int,
                               messages: List[BaseMessage], final_response: Any, tools_used: bool, agent_input: AgentInput):
        """Helper function to prepare and log agent interaction data via HTTP POST."""
        print(f"\n--- Preparing Log for Agent: {agent_id}, Thread: {thread_id} ---")

        # 1. Format Chat History for Payload (List[Dict])
        chat_history_payload = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "agent"
            content = str(msg.content) if msg.content else ""
            if isinstance(msg, AIMessage) and msg.tool_calls:
                 content += f"\nTool Calls: {json.dumps(msg.tool_calls, default=str)}"
            elif isinstance(msg, ToolMessage):
                 content = f"Tool Result ({msg.name}): {msg.content}"

            chat_history_payload.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat() # Timestamp of formatting
            })

        # 3. Directly insert or update log data in Supabase
        supabase_url: str | None = os.getenv("SUPABASE_URL")
        supabase_key: str | None = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            print("--- Logging Failed: SUPABASE_URL or SUPABASE_KEY environment variables not set. ---", file=sys.stderr)
            return

        print(f"--- Interacting with Supabase at {supabase_url[:20]}... ---") # Truncate URL for logging
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # First, check if there's an existing log for this agent_id
            existing_log_response = (
                supabase.table("agent_logs")
                .select("*")
                .eq("agent_id", str(agent_id))
                .execute()
            )
            
            if existing_log_response.data:
                # Update existing log for this agent
                existing_log = existing_log_response.data[0]
                
                # Get existing chat history (array of thread objects)
                existing_chat_history = existing_log.get("chat_history", [])
                
                # Find if there's an existing thread with this thread_id
                thread_found = False
                for thread_obj in existing_chat_history:
                    if thread_obj.get("thread_id") == str(thread_id):
                        # Append new messages to this thread's messages array
                        thread_obj["messages"] = thread_obj.get("messages", []) + chat_history_payload
                        thread_found = True
                        break
                
                # If thread not found, create a new thread object
                if not thread_found:
                    existing_chat_history.append({
                        "thread_id": str(thread_id),
                        "messages": chat_history_payload
                    })
                
                # Update token counts and pricing
                updated_log_payload = {
                    "input_token": existing_log.get("input_token", 0) + prompt_tokens,
                    "output_token": existing_log.get("output_token", 0) + completion_tokens,
                    "embedding_token": existing_log.get("embedding_token", 0),
                    "pricing": existing_log.get("pricing", 0.0),
                    "chat_history": existing_chat_history,  # Store threads with messages
                    # Overwrite these fields
                    "model_protocol": "default",
                    "model_temperature": float(temperature) if temperature is not None else None,
                    "media_input": False,
                    "media_output": False,
                    "use_memory": True,
                    "use_tool": tools_used,
                }
                
                # Update the log for this agent
                response = (
                    supabase.table("agent_logs")
                    .update(updated_log_payload)
                    .eq("agent_id", str(agent_id))
                    .execute()
                )
                
                if hasattr(response, 'error') and response.error:
                    print(f"--- Logging Update Failed (Supabase API Error): {response.error} ---", file=sys.stderr)
                else:
                    print(f"--- Logging Update Successful (Supabase) ---")
                
            else:
                # Create new log for this agent with the first thread
                new_chat_history = [{
                    "thread_id": str(thread_id),
                    "messages": chat_history_payload
                }]
                
                new_log_payload = {
                    "agent_id": str(agent_id),  # Ensure UUID is string for JSON
                    "input_token": prompt_tokens,
                    "output_token": completion_tokens,
                    "embedding_token": 0,
                    "pricing": 0.0,
                    "chat_history": new_chat_history,  # Store thread with messages
                    "model_protocol": "default",
                    "model_temperature": float(temperature) if temperature is not None else None,
                    "media_input": False,
                    "media_output": False,
                    "use_memory": True,
                    "use_tool": tools_used,
                }
                new_log_payload = {k: v for k, v in new_log_payload.items() if v is not None}
                
                # Insert new log
                response = (
                    supabase.table("agent_logs")
                    .insert(new_log_payload)
                    .execute()
                )
                
                if hasattr(response, 'error') and response.error:
                    print(f"--- Logging Insert Failed (Supabase API Error): {response.error} ---", file=sys.stderr)
                elif not response.data:
                    print(f"--- Logging Insert Failed (Supabase Insert Error): No data returned. Response: {response} ---", file=sys.stderr)
                else:
                    print(f"--- Logging Insert Successful (Supabase) ---")

        except Exception as e:
            print(f"--- Logging Failed (Unexpected Supabase Error): {e} ---", file=sys.stderr)
    
    async def invoke_agent(self, agent_id: str, agent_input: AgentInput, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke an agent with the provided input.
        
        Args:
            agent_name: The name of the agent to invoke
            agent_input: The input for the agent, including optional model_name in metadata and agent_config
            agent_config: The agent configuration (from database, used as fallback if not provided in agent_input)
            
        Returns:
            Agent response
            
        Note:
            The model_name can be specified in agent_input.metadata.model_name.
            If not provided, it defaults to "custom-vlm".
        """
        # Step 1: Prepare the configuration and query
        query, config = self.parse_agent_input(agent_input, agent_config)
        print(query, config)
        
        # Step 2: Handle agent memory
        memory = self.get_or_create_memory(agent_id)
        if agent_input.metadata.reset_memory:
            memory = self.reset_memory(agent_id)
        
        # Step 3: Use agent_config from request if available, otherwise use the provided agent_config
        if agent_input.agent_config:
            print("Using agent_config from request")
            agent_config_data = agent_input.agent_config
        else:
            print("Using provided agent_config")
            agent_config_data = agent_config
        
        # Step 4: Parse tools from agent_config_data
        has_tools, mcp_config = self._parse_tools(agent_config_data)
        
        # Step 5: Get the model name from metadata
        model_name = agent_input.metadata.model_name
        temperature = agent_input.metadata.temperature if hasattr(agent_input.metadata, 'temperature') else 0
        
        # We'll log after the agent responds to avoid slowing down the app
        thread_id = config.get('thread_id', 'default')
        
        # Setup usage callback to track token usage
        usage_callback = UsageMetadataCallbackHandler()
        invoke_config_with_callbacks = {"configurable": config, "callbacks": [usage_callback]}
        
        # Step 6: Create and invoke the agent
        if has_tools:
            # Agent with tools
            print("Using agent with tools")
            print("MCP config:", mcp_config)
            async with MultiServerMCPClient(mcp_config) as client:
                langchain_tools = client.get_tools()
                agent = get_react_agent(
                    model_name=model_name,
                    temperature=temperature,
                    langchain_tools=langchain_tools,
                    memory=memory
                )
                response = await agent.ainvoke({"messages": [HumanMessage(content=query)]}, invoke_config_with_callbacks)
        else:
            # Agent without tools
            print("Using agent without tools")
            agent = get_react_agent(
                model_name=model_name,
                temperature=temperature,
                langchain_tools=[],
                memory=memory
            )
            response = await agent.ainvoke({"messages": [HumanMessage(content=query)]}, invoke_config_with_callbacks)
        
        # Extract token counts from usage metadata
        metadata = usage_callback.usage_metadata
        # Find usage for the specific model used, fallback to 0
        model_usage = metadata.get(model_name, {})  # Use the actual model_name variable
        prompt_tokens = model_usage.get("input_tokens", 0)
        completion_tokens = model_usage.get("output_tokens", 0)
        total_tokens = model_usage.get("total_tokens", 0)
        
        # Log both user input and agent response together
        user_message = [HumanMessage(content=str(agent_input.input.messages))]
        agent_messages = [msg for msg in response.get('messages', []) if not isinstance(msg, HumanMessage)]
        all_messages = user_message + agent_messages
        await self._log_interaction(agent_id=agent_id, thread_id=thread_id, model_name=model_name, temperature=temperature, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens, messages=all_messages, final_response=response, tools_used=has_tools, agent_input=agent_input)
        
        return response
    

    async def invoke_agent_stream(self, agent_id: str, agent_input: AgentInput, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke an agent with the provided input (stream mode).
        """
        # Step 1: Prepare query and configuration
        query, config = self.parse_agent_input(agent_input, agent_config)
        print(query, config)

        # Step 2: Handle agent memory
        memory = self.get_or_create_memory(agent_id)
        if agent_input.metadata.reset_memory:
            memory = self.reset_memory(agent_id)

        # Step 3: Determine agent configuration
        agent_config_data = agent_input.agent_config if agent_input.agent_config else agent_config
        print("Using agent_config from request" if agent_input.agent_config else "Using provided agent_config")

        # Step 4: Parse tools
        has_tools, mcp_config = self._parse_tools(agent_config_data)

        # Step 5: Get the model name from metadata
        model_name = agent_input.metadata.model_name
        temperature = agent_input.metadata.temperature if hasattr(agent_input.metadata, 'temperature') else 0

        # We'll log after the agent responds to avoid slowing down the app
        thread_id = config.get('thread_id', 'default')

        # Setup usage callback to track token usage
        usage_callback = UsageMetadataCallbackHandler()
        invoke_config_with_callbacks = {"configurable": config, "callbacks": [usage_callback]}

        # Step 6: Select agent type
        agent = None
        client = None  # Placeholder for MCP client
        tool_messages = []  # To collect tool messages for logging
        
        # Determine if we should use ReAct text agent (for Gemma models)
        use_react_text = "gemma" in model_name.lower()

        if has_tools:
            print("Using agent with tools")
            print("MCP config:", mcp_config)
            client = MultiServerMCPClient(mcp_config)
            await client.__aenter__()  # Manually entering async context
            langchain_tools = client.get_tools()
            
            if use_react_text:
                print(f"Using ReAct text-based agent for {model_name}")
                agent = get_react_text_agent(
                    model_name=model_name,
                    temperature=temperature,
                    langchain_tools=langchain_tools,
                    memory=memory
                )
            else:
                agent = get_react_agent(
                    model_name=model_name,
                    temperature=temperature,
                    langchain_tools=langchain_tools,
                    memory=memory
                )
        else:
            print("Using agent without tools")
            agent = get_react_agent(model_name=model_name, temperature=temperature, langchain_tools=[], memory=memory)

        try:
            # Step 7: Stream agent events
            query_input = {"messages": [HumanMessage(content=query)]}
            final_answer_content: str | None = None

            yield f"event: status\ndata: {json.dumps({'status': 'Processing your request'})}\n\n"

            async for event in agent.astream_events(query_input, invoke_config_with_callbacks, version="v2"):
                kind = event["event"]
                event_name = event.get("name", "unknown")

                if kind == "on_chat_model_start":
                    yield f"event: status\ndata: {json.dumps({'status': 'Thinking...'})}\n\n"

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    content = chunk.content if isinstance(chunk, AIMessageChunk) and hasattr(chunk, 'content') else None
                    if content:
                        yield f"event: token\ndata: {json.dumps({'token': content})}\n\n"

                elif kind == "on_llm_stream":
                    chunk = event.get("data", {}).get("chunk")
                    # For LLM stream, chunk is usually just the text string or a GenerationChunk
                    content = chunk.text if hasattr(chunk, 'text') else str(chunk)
                    if content:
                        yield f"event: token\ndata: {json.dumps({'token': content})}\n\n"

                elif kind == "on_chat_model_end":
                    yield f"event: status\ndata: {json.dumps({'status': 'Responding...'})}\n\n"
                    output_message = event.get("data", {}).get("output")
                    if output_message and hasattr(output_message, 'content'):
                        final_answer_content = output_message.content

                elif kind == "on_tool_start":
                    tool_input = event.get('data', {}).get('input')
                    tool_data = {
                      "tool_name": event_name,
                        "status": f"Start using MCP: {event_name}",
                        "is_start": 1,
                        "input": tool_input
                    }
                    yield f"event: tool_status\ndata: {json.dumps(tool_data, default=str)}\n\n"

                elif kind == "on_tool_end":
                    tool_output = event.get('data', {}).get('output')
                    tool_data = {
                        "tool_name": event_name,
                        "status": f"Finish using MCP: {event_name}",
                        "is_start": 0,
                        "output": tool_output
                    }
                    yield f"event: tool_status\ndata: {json.dumps(tool_data, default=str)}\n\n"
                    # Add tool message to tool_messages list
                    tool_messages.append(ToolMessage(content=str(tool_output), name=event_name, tool_call_id=uuid.uuid4()))

            # Signal end of execution
            end_data = {"status": "Agent Execution End"}
            if final_answer_content:
                end_data["final_answer"] = final_answer_content
            yield f"event: status\ndata: {json.dumps(end_data)}\n\n"

            # Extract token counts from usage metadata
            metadata = usage_callback.usage_metadata
            # Find usage for the specific model used, fallback to 0
            model_usage = metadata.get(model_name, {})  # Use the actual model_name variable
            prompt_tokens = model_usage.get("input_tokens", 0)
            completion_tokens = model_usage.get("output_tokens", 0)
            total_tokens = model_usage.get("total_tokens", 0)
            
            # Log both user input and agent response together
            user_message = [HumanMessage(content=str(agent_input.input.messages))]
            agent_messages = ([AIMessage(content=final_answer_content)] if final_answer_content else []) + tool_messages
            all_messages = user_message + agent_messages
            final_response = {"final_answer": final_answer_content} if final_answer_content else {}
            await self._log_interaction(agent_id=agent_id, thread_id=thread_id, model_name=model_name, temperature=temperature, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens, messages=all_messages, final_response=final_response, tools_used=has_tools, agent_input=agent_input)

        finally:
            # Step 8: Ensure proper cleanup
            if client:
                await client.__aexit__(None, None, None)  # Manually exiting async context




# Singleton instance for global use
agent_boilerplate = AgentBoilerplate()