from dotenv import load_dotenv
import os
import torch
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from transformers import AutoTokenizer, CLIPModel, AutoProcessor
import numpy as np
from PIL import Image

load_dotenv()

class EmbedderService:
    """
    Embedding service using CLIP model for both text and image embeddings.
    Uses the full CLIP model to support both modalities.
    """
    
    def __init__(self):
        self._init_embedding_model()

    def _init_embedding_model(self):
        """Initialize the CLIP model for embeddings."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Use ViT-Large to match 768-dimensional embeddings in database
        self.clip_model_id = "openai/clip-vit-large-patch14"
        
        print("Initializing CLIP model for embeddings...")
        self.processor = AutoProcessor.from_pretrained(self.clip_model_id)
        self.image_processor = self.processor.image_processor
        self.tokenizer = self.processor.tokenizer
        
        # Use full CLIP model (not just vision)
        self.clip_model = CLIPModel.from_pretrained(
            self.clip_model_id, 
            torch_dtype=torch.bfloat16
        ).to(self.device)
        
        self.clip_model.eval()
        print(f"✅ CLIP embedding model ready on device: {self.device}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple documents using CLIP text encoder.
        
        Args:
            texts: List of text documents to embed
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        embeddings = []
        with torch.no_grad():
            for text in texts:
                # Tokenize text
                inputs = self.tokenizer(
                    text,
                    padding=True,
                    truncation=True,
                    max_length=77,
                    return_tensors="pt"
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Get text embeddings from CLIP
                text_features = self.clip_model.get_text_features(**inputs)
                
                # Normalize embeddings
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # Convert to list and append (convert bfloat16 to float32 first)
                embedding = text_features[0].cpu().float().numpy().tolist()
                embeddings.append(embedding)
        
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single query using CLIP text encoder.
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector as a list of floats
        """
        with torch.no_grad():
            # Tokenize query
            inputs = self.tokenizer(
                query,
                padding=True,
                truncation=True,
                max_length=77,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get text embeddings from CLIP
            text_features = self.clip_model.get_text_features(**inputs)
            
            # Normalize embeddings
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            # Convert to list (convert bfloat16 to float32 first)
            embedding = text_features[0].cpu().float().numpy().tolist()
        
        return embedding

    def embed_image(self, image_path: str) -> list[float]:
        """
        Embed a single image using CLIP vision encoder.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Embedding vector as a list of floats
        """
        with torch.no_grad():
            # Load and process image
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get image embeddings from CLIP
            image_features = self.clip_model.get_image_features(**inputs)
            
            # Normalize embeddings
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Convert to list (convert bfloat16 to float32 first)
            embedding = image_features[0].cpu().float().numpy().tolist()
        
        return embedding

    @property
    def embedding_dim(self) -> int:
        """Get the dimension of the embeddings."""
        return len(self.embed_query("test"))
    

if __name__ == "__main__":
    embedder = EmbedderService()

    documents = [
        "LangChain is a framework for building LLM apps.",
        "Azure OpenAI supports embedding models."
    ]
    doc_embeddings = embedder.embed_documents(documents)
    print(f"documents:\n{doc_embeddings}\nvector embeddings:\n{doc_embeddings}")

    query = "What is LangChain?"
    query_embedding = embedder.embed_query(query)
    print(f"query:\n{query}\nvector embedding:\n{query_embedding}")

    print(f"vector length: {embedder.embedding_dim}")