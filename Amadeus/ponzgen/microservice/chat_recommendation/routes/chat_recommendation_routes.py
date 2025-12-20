from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from typing import List, Dict
from ..chat_recommendation_generator import ChatRecommendationGenerator
from ..models import ConversationInput, RecommendationResponse, Recommendation, RecommendationInvocation
from ..utils.recommendation_utils import extract_topics, generate_recommendations_impl
import logging
import traceback
import json
import asyncio
from ...agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ValidationError, 
    InternalServerError, handle_pydantic_validation_error, ERROR_RESPONSES
)

router = APIRouter(
    prefix="/chat-recommendation",
    tags=["chat-recommendation"],
    responses={**ERROR_RESPONSES}
)

@router.post("/generate-recommendations", response_model=RecommendationResponse)
async def generate_recommendations(conversation: ConversationInput, request: Request):
    """
    Process conversation and generate relevant recommendations based on chat history.
    """
    try:
        print("Starting recommendation generation...")
        print(f"Received conversation: {conversation}")
        
        # Initialize generator
        generator = ChatRecommendationGenerator()
        await generator.initialize()
        print("Initialized generator")
        
        # Extract topics from the conversation
        topics = extract_topics(conversation.user_input)
        print(f"Extracted topics: {topics}")
        
        # Process conversation to extract key topics and context
        conversation_summary = generator.generate_summary(
            conversation_text=conversation.user_input,
            topics=topics
        )
        print(f"Generated summary: {conversation_summary}")
        
        print("Generating recommendations...")
        # Generate recommendations with chat history
        recommendations = await generator.generate_recommendations(
            agent_id=conversation.agent_id,
            user_input=conversation.user_input,
            chat_history=conversation.messages,
            model_name="custom-vlm",
            temperature=0
        )
        print(f"Generated recommendations: {recommendations}")
        
        if not recommendations:
            raise InternalServerError("Failed to generate recommendations")
        
        # Create recommendation objects with higher confidence for generated recommendations
        recommendation_objects = [
            Recommendation(
                text=rec,
                confidence=0.95,  # High confidence for generated recommendations
                context={"source": "generated", "model": "custom-vlm"}
            ) 
            for rec in recommendations
        ]
        
        # Create response
        response = RecommendationResponse(
            recommendations=recommendation_objects,
            summary=conversation_summary,
            relevant_logs=[]
        )
        print("Created response object")
        
        return response
            
    except Exception as e:
        print(f"Error in route handler: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        print(f"Traceback: {traceback.format_exc()}")
        raise InternalServerError(f"Failed to process request: {str(e)}")

@router.post("/invoke-recommendation")
async def invoke_recommendation(invocation: RecommendationInvocation, request: Request):
    """
    Directly invoke a chosen recommendation.
    """
    try:
        print("Starting recommendation invocation...")
        print(f"Received invocation: {invocation}")
        
        # Return success response
        return {"status": "success", "message": "Recommendation invoked successfully"}
        
    except Exception as e:
        print(f"Error in recommendation invocation: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        print(f"Traceback: {traceback.format_exc()}")
        raise InternalServerError(f"Failed to invoke recommendation: {str(e)}")

@router.post("/stream")
async def stream_chat(
    request: Request,
    agent_input: ConversationInput
):
    """
    Stream chat responses and recommendations with Server-Sent Events (SSE).
    """
    try:
        print("Starting streaming response...")
        print(f"Received request body: {agent_input}")
        
        async def event_generator():
            try:
                # Initialize generator
                generator = ChatRecommendationGenerator()
                await generator.initialize()
                
                # First yield a status event
                status_data = {
                    "status": "Processing your message..."
                }
                yield f"event: status\ndata: {json.dumps(status_data)}\n\n"
                
                # Then yield the initial chat response
                chat_response = {
                    "content": f"I'm thinking about your message: '{agent_input.user_input}'"
                }
                yield f"event: content\ndata: {json.dumps(chat_response)}\n\n"
                
                await asyncio.sleep(1)  # Small delay to simulate thinking
                
                # Generate recommendations
                recommendations = await generator.generate_recommendations(
                    agent_id=agent_input.agent_id,
                    user_input=agent_input.user_input,
                    chat_history=agent_input.messages,
                    model_name="custom-vlm",
                    temperature=0
                )
                
                # Update status
                status_data = {
                    "status": "Generating recommendations..."
                }
                yield f"event: status\ndata: {json.dumps(status_data)}\n\n"
                
                # Yield each recommendation
                for rec in recommendations:
                    recommendation_data = {
                        "content": rec
                    }
                    yield f"event: recommendation\ndata: {json.dumps(recommendation_data)}\n\n"
                    await asyncio.sleep(0.5)  # Small delay between recommendations
                
                # Final status update
                status_data = {
                    "status": "Complete"
                }
                yield f"event: status\ndata: {json.dumps(status_data)}\n\n"
                
                # Signal completion
                yield "event: done\ndata: [DONE]\n\n"
                    
            except Exception as e:
                print(f"Error in stream: {str(e)}")
                error_data = {
                    "error": str(e)
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": request.headers.get("origin", "http://127.0.0.1:5500"),
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        print(f"Error in stream setup: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        print(f"Traceback: {traceback.format_exc()}")
        raise InternalServerError(f"Failed to setup streaming: {str(e)}")