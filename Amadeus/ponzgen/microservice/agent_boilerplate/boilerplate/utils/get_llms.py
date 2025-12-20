from .custom_vlm_model import get_custom_vlm_model

def get_llms(model_name: str="custom-vlm", temperature=0):
    """
    Helper function to get LLM instance.
    
    Uses the custom VLM model (Gemma-2 + CLIP) by default.
    
    Args:
        model_name: The name of the model to use
                   - "custom-vlm" (default) for local Gemma-2 + CLIP model
                   - Any other name also uses custom VLM (for compatibility)
        temperature: Temperature setting for the model (note: custom VLM has fixed temperature)
        
    Returns:
        A configured LLM instance (CustomVLMLLM)
    """
    # Always use custom VLM model
    return get_custom_vlm_model()