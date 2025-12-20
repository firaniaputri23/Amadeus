"""
Chat Recommendation Generator

This module handles generating chat recommendations using LLMs.
It analyzes user input and conversation history to provide up to 4 actionable suggestions.
"""

from typing import List, Optional, AsyncGenerator, Dict
import os
import json
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from ..agent_boilerplate.boilerplate.utils.get_llms import get_llms

from .utils.recommendation_utils import generate_recommendations_impl, parse_recommendation_response, validate_recommendations
from ..agent_boilerplate.boilerplate.errors import (
    BadRequestError, InternalServerError, ServiceUnavailableError
)

class ChatRecommendationGenerator:
    """
    Handles chat recommendation generation using LLMs.
    This class generates up to 4 chat recommendations based on user input and chat history.
    """

    def __init__(self):
        """Initialize the ChatRecommendationGenerator."""
        pass

    async def initialize(self):
        """No-op initialization."""
        pass

    async def generate_recommendations(
        self,
        agent_id: str,
        user_input: str,
        chat_history: List[Dict] = None,
        model_name: str = "custom-vlm",
        temperature: float = 0,
    ) -> List[str]:
        """
        Generate chat recommendations based on user input and chat history.
        """
        # Handle image-only messages: use assistant's VLM response as context
        if not user_input or user_input.strip() == '':
            # Check if we have an assistant message with VLM analysis
            if chat_history and len(chat_history) > 0:
                last_message = chat_history[-1]
                if isinstance(last_message, dict) and last_message.get('role') == 'assistant':
                    user_input = last_message.get('content', '')
                elif hasattr(last_message, 'role') and last_message.role == 'assistant':
                    user_input = last_message.content
            
            # If still empty, skip recommendations
            if not user_input or user_input.strip() == '':
                return []

        try:
            # Extract messages from chat history if provided
            chat_history_messages = []
            if chat_history:
                for msg in chat_history:
                    if isinstance(msg, dict):
                        chat_history_messages.append(msg.get('content', ''))
                    else:
                        chat_history_messages.append(msg.content)

            # Generate recommendations using the utility function
            recommendations = await generate_recommendations_impl(
                user_input=user_input,
                chat_history_messages=chat_history_messages,
                model_name=model_name,
                temperature=temperature
            )

            if not recommendations or len(recommendations) < 2:
                raise InternalServerError("Failed to generate sufficient recommendations")

            return recommendations
        except Exception as e:
            print(f"Error in generate_recommendations: {str(e)}")
            raise InternalServerError(f"Failed to generate chat recommendations: {str(e)}")

    async def generate_recommendations_stream(
        self,
        agent_id: str,
        user_input: str,
        chat_history: List[Dict] = None,
        model_name: str = "custom-vlm",
        temperature: float = 0,
    ) -> AsyncGenerator[str, None]:
        """
        Generate chat recommendations with a streaming response.
        """
        if not user_input:
            raise BadRequestError("User input cannot be empty")

        try:
            # Extract messages from chat history if provided
            chat_history_messages = []
            if chat_history:
                for msg in chat_history:
                    if isinstance(msg, dict):
                        chat_history_messages.append(msg.get('content', ''))
                    else:
                        chat_history_messages.append(msg.content)

            validated_recommendations = await generate_recommendations_impl(
                user_input=user_input,
                chat_history_messages=chat_history_messages,
                model_name=model_name,
                temperature=temperature,
                streaming=True
            )
            yield json.dumps(validated_recommendations)
        except Exception as e:
            raise InternalServerError(f"Failed to stream chat recommendations: {str(e)}")

    def generate_summary(self, conversation_text: str, topics: List[str]) -> str:
        """
        Generate a summary of the conversation based on the text and topics.
        """
        summary = f"Conversation about: {', '.join(topics)}. "
        if len(conversation_text) > 100:
            summary += conversation_text[:100] + "..."
        else:
            summary += conversation_text
        return summary

    def get_relevant_logs(self, summary: str, num_recommendations: int = 5) -> List[Dict]:
        """
        Stub for compatibility (returns empty list, no logs).
        """
        return []

    def _calculate_relevance_score(self, log: Dict, summary: str) -> float:
        """
        Stub for compatibility (returns 0.0, no logs).
        """
        return 0.0