import logging
from .ingestion import supabase, model

logger = logging.getLogger("rag-retrieval")

def search_vector_chunks(query_text: str, top_k: int = 5, threshold: float = 0.5):
    """Embed the query and search for similar chunks in Supabase."""
    logger.info(f"Searching for: '{query_text}' (top_k={top_k}, threshold={threshold})")
    
    try:
        # 1. Embed the query text
        query_embedding = model.embed_query(query_text)
        
        # 2. Call Supabase RPC function for vector search
        response = supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": top_k,
            }
        ).execute()
        
        results = response.data
        logger.info(f"Found {len(results)} matching chunks")
        return results
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        raise e
