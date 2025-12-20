from .custom_vlm_model import get_custom_vlm_model
from langchain_openai import ChatOpenAI
import os
import logging

logger = logging.getLogger(__name__)

def get_llms(model_name: str="custom-vlm", temperature=0):
    """
    Helper function to get LLM instance.
    
    Supports multiple model providers:
    - "custom-vlm": Local Gemma-2 + CLIP model (for vision tasks)
    - OpenRouter models: Cloud models with tool calling support
    - OpenAI models: Direct OpenAI API access
    
    Args:
        model_name: The name of the model to use
                   - "custom-vlm" (default) for local Gemma-2 + CLIP model
                   - "google/gemma-2-9b-it" for Gemma 2 9B via OpenRouter
                   - "google/gemma-2-27b-it" for Gemma 2 27B via OpenRouter
                   - "openai/gpt-4o-mini" for GPT-4o mini via OpenRouter
                   - "anthropic/claude-3-haiku" for Claude Haiku via OpenRouter
                   - "gpt-3.5-turbo", "gpt-4" for direct OpenAI access
        temperature: Temperature setting for the model
        
    Returns:
        A configured LLM instance
    """
    # Local custom VLM for vision tasks
    if model_name == "custom-vlm":
        return get_custom_vlm_model()
    
    # OpenRouter models (supports tool calling)
    elif "/" in model_name or model_name in ["gemma-2-9b-it", "gemma-2-27b-it"]:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            print("WARNING: OPENROUTER_API_KEY not found. Falling back to custom VLM.")
            print("To use OpenRouter models, add OPENROUTER_API_KEY to your .env file")
            return get_custom_vlm_model()
        
        # Format model name for OpenRouter
        if not "/" in model_name:
            model_name = f"google/{model_name}"
        
        print(f"Using OpenRouter model: {model_name}")
        
        # Check if using free model and provide helpful message
        if ":free" in model_name:
            print("💡 Using FREE OpenRouter model")
            print("⚠️  If you get 404 error, configure privacy settings:")
            print("   https://openrouter.ai/settings/privacy")
        
        return ChatOpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            model=model_name,
            temperature=temperature,
            streaming=True,
            model_kwargs={
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/yourusername/ponzgen",
                    "X-Title": "Ponzgen Agent System"
                }
            }
        )
    
    # Direct OpenAI access
    elif model_name.startswith("gpt-"):
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("WARNING: OPENAI_API_KEY not found. Falling back to custom VLM.")
            return get_custom_vlm_model()
        
        print(f"Using OpenAI model: {model_name}")
        return ChatOpenAI(
            api_key=openai_key,
            model=model_name,
            temperature=temperature,
            streaming=True
        )
    
    # Fallback to custom VLM
    else:
        print(f"Unknown model: {model_name}. Falling back to custom VLM.")
        return get_custom_vlm_model()