"""
ReAct Text-based Agent for models that output text-based tool calls (like Gemma).

This agent parses text outputs like:
Thought: I need to search for repositories
Action: search_repositories
Action Input: {"query": "owner:inventiner"}
Observation: [tool result]
"""

import re
import json
from typing import List, Dict, Any, AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from ..utils.get_llms import get_llms


class ReActTextAgent:
    """Agent that handles text-based ReAct format for models like Gemma."""
    
    def __init__(self, model_name: str, temperature: float, tools: List[BaseTool], memory=None):
        self.model = get_llms(model_name, temperature)
        self.tools = {tool.name: tool for tool in tools}
        self.memory = memory
        self.max_iterations = 10
        
        # Build tool descriptions for prompt
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])
        
        self.system_prompt = f"""You are a helpful AI assistant with access to tools. Use the following format:

Thought: Think about what you need to do
Action: tool_name
Action Input: {{"param1": "value1", "param2": "value2"}}
Observation: [tool result will be provided]
... (repeat Thought/Action/Observation as needed)
Thought: I now have enough information
Final Answer: Your response to the user

Available tools:
{tool_descriptions}

IMPORTANT:
- Always use the EXACT tool names shown above
- Action Input must be valid JSON
- You MUST use tools when they are relevant
- End with "Final Answer:" when you have the information"""

    def _parse_action(self, text: str) -> tuple[str | None, dict | None]:
        """Parse Action and Action Input from text."""
        # Match Action: tool_name
        action_match = re.search(r'Action:\s*(\w+)', text)
        if not action_match:
            return None, None
        
        tool_name = action_match.group(1).strip()
        
        # Match Action Input: {...}
        input_match = re.search(r'Action Input:\s*(\{[^}]*\})', text, re.DOTALL)
        if not input_match:
            # Try without braces
            input_match = re.search(r'Action Input:\s*(.+?)(?:\n|$)', text)
            if input_match:
                try:
                    tool_input = json.loads(input_match.group(1).strip())
                except:
                    tool_input = {"query": input_match.group(1).strip()}
            else:
                tool_input = {}
        else:
            try:
                tool_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                tool_input = {}
        
        return tool_name, tool_input
    
    def _check_final_answer(self, text: str) -> str | None:
        """Check if text contains Final Answer."""
        match = re.search(r'Final Answer:\s*(.+)', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    async def astream_events(self, query_input: Dict, config: Dict, version: str = "v2") -> AsyncIterator[Dict]:
        """
        Stream agent events in a format compatible with existing code.
        
        Args:
            query_input: {"messages": [HumanMessage(content="...")]}
            config: {"configurable": {"thread_id": "..."}, "callbacks": [...]}
            version: Event version (ignored, for compatibility)
        """
        # Extract query from messages
        messages = query_input.get("messages", [])
        if not messages:
            return
        
        query = messages[0].content if isinstance(messages[0], HumanMessage) else str(messages[0])
        
        # Build conversation history (NO SystemMessage for Gemma)
        conversation = []
        saved_state = None
        
        # Add memory if available
        thread_id = config.get("configurable", {}).get("thread_id")
        if self.memory and thread_id:
            # Get previous messages from memory
            saved_state = self.memory.get({"configurable": {"thread_id": thread_id}})
            if saved_state and "messages" in saved_state:
                conversation.extend(saved_state["messages"])
        
        # Inject instructions as part of the user query
        full_query = f"""{self.system_prompt}

USER QUERY: {query}"""
        
        # Add current query
        conversation.append(HumanMessage(content=full_query))
        
        # ReAct loop
        iteration = 0
        scratchpad = ""
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Yield thinking status
            yield {
                "event": "on_chat_model_start",
                "name": "ReActTextAgent",
                "data": {}
            }
            
            # Get model response
            current_messages = conversation + [HumanMessage(content=scratchpad)] if scratchpad else conversation
            
            # Stream tokens
            full_response = ""
            async for chunk in self.model.astream(current_messages):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += content
                
                yield {
                    "event": "on_chat_model_stream",
                    "name": "ReActTextAgent",
                    "data": {"chunk": chunk}
                }
            
            # Check for Final Answer
            final_answer = self._check_final_answer(full_response)
            if final_answer:
                # Yield final response
                yield {
                    "event": "on_chat_model_end",
                    "name": "ReActTextAgent",
                    "data": {"output": AIMessage(content=final_answer)}
                }
                
                # Save to memory (save only user query and final answer, not instructions)
                if self.memory and thread_id:
                    memory_messages = []
                    if saved_state and "messages" in saved_state:
                        memory_messages = saved_state["messages"]
                    memory_messages.append(HumanMessage(content=query))
                    memory_messages.append(AIMessage(content=final_answer))
                    self.memory.put(
                        {"configurable": {"thread_id": thread_id}},
                        {"messages": memory_messages}
                    )
                
                break
            
            # Parse action
            tool_name, tool_input = self._parse_action(full_response)
            
            if not tool_name or tool_name not in self.tools:
                # No valid action, treat as final answer
                yield {
                    "event": "on_chat_model_end",
                    "name": "ReActTextAgent",
                    "data": {"output": AIMessage(content=full_response)}
                }
                break
            
            # Execute tool
            tool = self.tools[tool_name]
            
            yield {
                "event": "on_tool_start",
                "name": tool_name,
                "data": {"input": tool_input}
            }
            
            try:
                # Execute tool
                if hasattr(tool, 'ainvoke'):
                    result = await tool.ainvoke(tool_input)
                else:
                    result = tool.invoke(tool_input)
                
                observation = str(result)
                
                yield {
                    "event": "on_tool_end",
                    "name": tool_name,
                    "data": {"output": observation}
                }
                
            except Exception as e:
                observation = f"Error: {str(e)}"
                yield {
                    "event": "on_tool_end",
                    "name": tool_name,
                    "data": {"output": observation}
                }
            
            # Add to scratchpad for next iteration
            scratchpad += f"\n{full_response}\nObservation: {observation}\n"
        
        # If max iterations reached, yield current state
        if iteration >= self.max_iterations:
            yield {
                "event": "on_chat_model_end",
                "name": "ReActTextAgent",
                "data": {"output": AIMessage(content="Max iterations reached. Please refine your query.")}
            }


def get_react_text_agent(model_name: str = "custom-vlm", temperature: float = 0, 
                         langchain_tools: List[BaseTool] = None, memory=None) -> ReActTextAgent:
    """
    Create a ReAct text-based agent for models like Gemma.
    
    Args:
        model_name: Model name (e.g., "google/gemma-3-12b-it:free")
        temperature: Temperature setting
        langchain_tools: List of LangChain tools
        memory: Memory checkpointer
        
    Returns:
        ReActTextAgent instance
    """
    return ReActTextAgent(model_name, temperature, langchain_tools or [], memory)
