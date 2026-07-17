import json
import logging
import time
from typing import AsyncGenerator, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langsmith import traceable
from retrieval import search_vector_chunks
import os

logger = logging.getLogger("rag-chat")

# Setup OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY_TEMP")
settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
if os.path.exists(settings_path):
    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)
            if settings.get("openai_api_key"):
                openai_api_key = settings["openai_api_key"]
    except Exception:
        pass

SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on retrieved document context. 
Always answer the user's question accurately and concisely using the provided context.

Please format your response using clean Markdown (.md) such as bold headers, bullet lists, bold text, or tables to structure information clearly for the user.

When referring to facts from a source, you MUST cite it using the exact document name and the EXACT page number/label provided in the parentheses next to that source. 
For example, if the source header is: "Source [4]: walmart_code_of_conduct.pdf (Page 11)", you must cite it exactly as: [walmart_code_of_conduct.pdf, Page 11]. 
DO NOT mix up the source index number (like Source [4] or index 4) with the page number (like Page 11). The source index number is NOT the page number.

If the provided context does not contain the answer or is insufficient, state that you do not have enough information to answer, but still offer any general helpful knowledge if applicable, while being clear it's not from the documents."""


@traceable(name="rag-chat-agent", tags=["rag", "chat"])
def get_chat_chain(model_name: str = "gpt-4o-mini"):
    """Initialize the LangChain ChatModel and prompt template based on settings.json."""
    from llm_factory import get_llm
    llm = get_llm(temperature=0.2, streaming=True)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("system", "Context from documents:\n{context}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])
    return prompt | llm

from agents.booking_agent import run_booking_agent

PSS_API_URL = os.environ.get("PSS_API_URL", "http://localhost:8000/api/pss")
if PSS_API_URL and not PSS_API_URL.endswith("/api/pss"):
    PSS_API_URL = PSS_API_URL.rstrip("/") + "/api/pss"


async def stream_chat_response(
    query: str,
    history: List[Dict[str, str]],
    top_k: int = 5,
    threshold: float = 0.3,
    passenger_profile: dict = None,
    run_id: str = None,
    thread_id: str = None
) -> AsyncGenerator[str, None]:
    """
    Invokes the Airline Booking Agent orchestrator to handle the conversation,
    using the provided passenger profile context and streaming results over SSE.
    """
    try:
        # Yield the run_id and thread_id immediately as the first SSE event
        yield f"data: {json.dumps({'type': 'info', 'run_id': run_id, 'thread_id': thread_id})}\n\n"

        # 1. Use provided passenger profile or fallback
        if not passenger_profile:
            logger.warning("No passenger profile provided by frontend. Using fallback.")
            passenger_profile = {
                "passenger_id": "usr_94f83b",
                "name": "Jane Smith",
                "email": "jane.smith@example.com",
                "frequent_flyer_number": "FF773910"
            }

        # 2. Start time tracking
        start_time = time.time()
        ttft = None
        usage_metadata = None

        # 3. Stream agent execution events
        async for event in run_booking_agent(
            query, 
            history, 
            passenger_profile, 
            top_k, 
            threshold,
            run_id=run_id,
            thread_id=thread_id,
            langsmith_extra={
                "run_id": run_id,
                "metadata": {"thread_id": thread_id}
            }
        ):
            event_type = event.get("type")
            
            if event_type == "token":
                if ttft is None:
                    ttft = (time.time() - start_time) * 1000 # in ms
                yield f"data: {json.dumps({'type': 'token', 'content': event['content']})}\n\n"
                
            elif event_type == "tool_call":
                yield f"data: {json.dumps({'type': 'tool_call', 'name': event['name'], 'args': event['args']})}\n\n"
                
            elif event_type == "tool_result":
                yield f"data: {json.dumps({'type': 'tool_result', 'name': event['name'], 'args': event['args'], 'result': event['result']})}\n\n"
                
            elif event_type == "metrics":
                usage_metadata = event.get("usage")

        # 4. Calculate total latency and yield observability metrics
        latency = (time.time() - start_time) * 1000  # in ms
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        cost_usd = 0.0

        if usage_metadata:
            input_tokens = usage_metadata.get("input_tokens", 0)
            output_tokens = usage_metadata.get("output_tokens", 0)
            total_tokens = usage_metadata.get("total_tokens", 0)
            # Rates: $0.15 per 1M input tokens, $0.60 per 1M output tokens
            cost_usd = (input_tokens * 0.00000015) + (output_tokens * 0.00000060)

        metrics = {
            "ttft_ms": round(ttft, 2) if ttft is not None else 0.0,
            "latency_ms": round(latency, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd
        }
        yield f"data: {json.dumps({'type': 'metrics', 'metrics': metrics})}\n\n"

        # 5. Yield done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
