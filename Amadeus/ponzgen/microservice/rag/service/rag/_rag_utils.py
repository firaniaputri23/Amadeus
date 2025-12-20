from ..storage_database._storage_utils import SupabaseStorageClient
from ..embedding._embedding_utils import EmbedderService
from ....agent_boilerplate.boilerplate.utils.get_llms import get_llms

import os

embedder = EmbedderService()
storage_client = SupabaseStorageClient()

def generate_response(query, retrieved_context, model_name="custom-vlm", temperature=0):
    """
    Generates a response from LLM based on the query and context.
    """
    llm = get_llms(model_name=model_name, temperature=temperature)
    
    formatted_context = ""
    for i, (doc_id, score, doc) in enumerate(retrieved_context):
        formatted_context += f"Document {i+1} (ID: {doc_id}, Relevance: {score:.4f}):\n{doc['text']}\n\n"
    
    prompt = f"""Based on the following retrieved reviews, please answer the query.
    
Query: {query}

Retrieved Context:
{formatted_context}

Answer:"""
    
    response = llm.invoke(prompt)
    return response.content

def retrieval_with_rerank(query: str):
    query_embedding = embedder.embed_query(query)
    query_embedding_str = str(query_embedding)

    response = storage_client.run_rpc(
        function_name="rerank_documents",
        params={
            "query_embedding": query_embedding_str,
            "top_k": 5
        }
    ).execute()
    results = response.data

    retrieved_context = []
    for i, result in enumerate(results):
        retrieved_context.append((
            result["file_id"],
            result["similarity"],
            {"text": result["content"]}
        ))

    return retrieved_context

if __name__ == "__main__":
    embedder = EmbedderService()
    storage_client = SupabaseStorageClient()

    query = "What does CLAHE stands for?"
    query_embedding = embedder.embed_query(query)
    query_embedding_str = str(query_embedding)

    # Call the Supabase function to rerank
    response = storage_client.run_rpc(
        function_name="rerank_documents",
        params={
            "query_embedding": query_embedding_str,
            "top_k": 5
        }
    ).execute()

    results = response.data

    # Tampilkan hasil
    print(f"Top dokumen yang paling relevan:")
    retrieved_context = []
    for i, result in enumerate(results):
        print(f"{i+1}. Similarity: {result['similarity']:.4f}")
        print(f"   Content: {result['content'][:100]}...\n")
        
        # Simpan untuk dipakai LLM
        retrieved_context.append((
            result["file_id"],
            result["similarity"],
            {"text": result["content"]}
        ))

    # Generate response dari LLM
    response = generate_response(query, retrieved_context)
    print(f"Query: {query}\n")
    print(f"Response: {response}")