from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: str

class ConversationInput(BaseModel):
    agent_id: str
    messages: List[Message]
    user_input: str
    conversation_id: Optional[str] = None

class Recommendation(BaseModel):
    text: str
    confidence: float = Field(default=1.0)
    context: Optional[Dict[str, Any]] = None

class RecommendationResponse(BaseModel):
    recommendations: List[Recommendation] = Field(default_factory=list)
    summary: Optional[str] = None
    relevant_logs: Optional[List[Dict]] = None

class RecommendationInvocation(BaseModel):
    """
    Model for invoking a chosen recommendation.
    """
    agent_id: str
    recommendation_text: str