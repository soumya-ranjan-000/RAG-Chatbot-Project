from fastapi import FastAPI, BackgroundTasks, Request, HTTPException, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import os
import uuid
import asyncio
import json
import logging
from ingestion import process_s3_document, upload_file_to_s3, list_files_in_s3, delete_file_from_s3, get_indexed_documents
from retrieval import search_vector_chunks
from chat import stream_chat_response
from typing import Dict, List, Callable, Optional, Union, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag-app")

app = FastAPI()

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",                          # Allow all origins for development
        "http://localhost:5173",      # Vite dev server
        "http://localhost:3000",      # Backend itself
        "http://127.0.0.1:5173",      # Localhost alternative
        "http://127.0.0.1:3000",      # Localhost alternative
        "https://localhost:5173",     # HTTPS versions
        "https://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# --- Request Models ---

class S3Object(BaseModel):
    key: str

class S3Bucket(BaseModel):
    name: Optional[str] = None

class S3Data(BaseModel):
    bucket: Optional[S3Bucket] = None
    object: S3Object

class S3Record(BaseModel):
    s3: S3Data

class S3Event(BaseModel):
    Records: List[S3Record]

class EventBridgeBucket(BaseModel):
    name: str

class EventBridgeObject(BaseModel):
    key: str
    size: Optional[int] = None
    etag: Optional[str] = None
    sequencer: Optional[str] = None

class EventBridgeDetail(BaseModel):
    version: Optional[str] = None
    bucket: EventBridgeBucket
    object: EventBridgeObject
    request_id: Optional[str] = Field(None, alias="request-id")
    requester: Optional[str] = None
    source_ip_address: Optional[str] = Field(None, alias="source-ip-address")
    reason: Optional[str] = None

class EventBridgeEvent(BaseModel):
    version: str
    id: str
    detail_type: str = Field(..., alias="detail-type")
    source: str
    account: str
    time: str
    region: str
    resources: List[str]
    detail: EventBridgeDetail

    class Config:
        populate_by_name = True

from typing import Union

# In-memory job tracking
job_progress: Dict[str, Dict] = {}


def create_progress_callback(job_id: str) -> Callable:
    """Create a progress callback function for a specific job."""

    def update_progress(stage: str, details: dict = None):
        if job_id in job_progress:
            if details:
                job_progress[job_id].update(details)
            job_progress[job_id]["message"] = stage

    return update_progress


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file directly to the S3 bucket."""
    logger.info(f"Received /upload request for file: {file.filename}")
    
    try:
        content = await file.read()
        s3_uri = upload_file_to_s3(content, file.filename)
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "s3_uri": s3_uri,
            "content_type": file.content_type
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/files")
async def get_files(bucket_name: Optional[str] = None):
    """List files in the S3 bucket with their indexing status."""
    logger.info("Received GET /files request")
    try:
        s3_files = list_files_in_s3(bucket_name)
        indexed_docs = get_indexed_documents()
        
        files_list = []
        for f in s3_files:
            files_list.append({
                "key": f["key"],
                "size": f["size"],
                "last_modified": f["last_modified"],
                "s3_uri": f["s3_uri"],
                "indexed": f["key"] in indexed_docs
            })
        return files_list
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@app.delete("/files")
async def delete_file(key: str = Query(..., description="The S3 key/filename to delete"), bucket_name: Optional[str] = None):
    """Delete a file from S3 and its corresponding chunks from Supabase."""
    logger.info(f"Received DELETE request for file: {key}")
    try:
        delete_file_from_s3(key, bucket_name)
        return {"message": f"Successfully deleted {key} from S3 and Supabase"}
    except Exception as e:
        logger.error(f"Failed to delete file {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@app.get("/query")
async def query_documents(
    text: str = Query(..., description="The search query text"),
    top_k: int = Query(5, description="Number of relevant chunks to return"),
    threshold: float = Query(0.5, description="Similarity threshold (0.0 to 1.0)")
):
    """Search for relevant document chunks based on semantic similarity."""
    logger.info(f"Received /query request: '{text}' (top_k={top_k})")
    
    try:
        results = search_vector_chunks(text, top_k=top_k, threshold=threshold)
        return {
            "query": text,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/ingest")
async def s3_webhook(
    payload: Union[EventBridgeEvent, S3Event], 
    background_tasks: BackgroundTasks
):
    """Ingest documents and return a job ID for tracking progress."""
    
    # payload is now automatically parsed and validated as either S3Event or EventBridgeEvent
    logger.info(f"Received /ingest request. Type: {type(payload).__name__}")
    
    # 2. Normalize the data into a records list
    records = []
    
    if isinstance(payload, S3Event):
        # Standard S3 Event
        records = [r.model_dump() for r in payload.Records]
        logger.info(f"Found {len(records)} records in standard S3 event format")
    elif isinstance(payload, EventBridgeEvent):
        # EventBridge wrapper
        records = [{
            "s3": {
                "bucket": { "name": payload.detail.bucket.name },
                "object": { "key": payload.detail.object.key }
            }
        }]
        logger.info(f"Found 1 record in EventBridge format: {records[0]['s3']['object']['key']}")
    
    if not records:
        logger.warning("No S3 records found in payload. Ignoring request.")
        return {"status": "ignored", "message": "No S3 records found in payload"}

    # 3. Logic
    job_id = str(uuid.uuid4())
    logger.info(f"Created Job ID: {job_id}")
    
    job_progress[job_id] = {
        "status": "pending",
        "total_files": len(records),
        "processed_files": 0,
        "current_file": None,
        "message": "Starting ingestion...",
        "errors": [],
    }

    # Pass the records (already dicts) to your background task
    background_tasks.add_task(process_ingestion, job_id, records)

    response = {"job_id": job_id, "status": "processing", "files": len(records)}
    logger.info(f"Returning response for {job_id}: {response}")
    return response


async def process_ingestion(job_id: str, records: List[dict]):
    """Process ingestion and update progress."""
    logger.info(f"Background task started for Job: {job_id}")
    try:
        job_progress[job_id]["status"] = "in_progress"

        for idx, record in enumerate(records):
            s3_key = record["s3"]["object"]["key"]
            bucket_name = record["s3"].get("bucket", {}).get("name")
            
            logger.info(f"[{job_id}] Processing file {idx+1}/{len(records)}: {s3_key} in bucket {bucket_name}")

            # Update progress
            job_progress[job_id]["current_file"] = s3_key
            job_progress[job_id]["processed_files"] = idx + 1

            # Create callback for this document
            callback = create_progress_callback(job_id)

            # Process the document with progress tracking
            process_s3_document(s3_key, bucket_name=bucket_name, progress_callback=callback)

        job_progress[job_id]["status"] = "completed"
        job_progress[job_id]["message"] = "Ingestion completed successfully"
        logger.info(f"Background task COMPLETED for Job: {job_id}")

    except Exception as e:
        logger.error(f"Background task FAILED for Job: {job_id}. Error: {str(e)}", exc_info=True)
        job_progress[job_id]["status"] = "failed"
        job_progress[job_id]["message"] = f"Error: {str(e)}"
        job_progress[job_id]["errors"].append(str(e))


@app.get("/ingest/progress/{job_id}")
async def get_progress(job_id: str):
    """Get current progress of an ingestion job."""
    logger.info(f"Progress check requested for Job: {job_id}")
    if job_id not in job_progress:
        logger.warning(f"Job not found: {job_id}")
        return {"error": "Job not found"}
    
    current_status = job_progress[job_id]
    logger.info(f"Job {job_id} status: {current_status['status']} ({current_status['processed_files']}/{current_status['total_files']})")
    return current_status


@app.get("/ingest/stream/{job_id}")
async def stream_progress(job_id: str):
    """Stream progress updates for an ingestion job using Server-Sent Events."""

    if job_id not in job_progress:
        return {"error": "Job not found"}

    async def event_generator():
        last_state = None
        max_wait = 60  # Max 60 seconds of streaming
        elapsed = 0

        while elapsed < max_wait:
            # Check if job exists and get current state
            if job_id not in job_progress:
                yield 'data: {"error": "Job not found"}\n\n'
                break

            current_state = job_progress[job_id]

            # Always send update (not just on change) to keep connection alive
            yield f"data: {json.dumps(current_state)}\n\n"

            # Stop streaming if job completed or failed
            if current_state["status"] in ["completed", "failed"]:
                await asyncio.sleep(1)  # Final delay to ensure message delivery
                break

            await asyncio.sleep(0.5)  # Check progress every 500ms
            elapsed += 0.5

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- Chat Endpoint ---

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = []
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.3
    passenger_profile: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Stream a chat response with document sources.
    """
    logger.info(f"Received /chat query: '{request.query}' with {len(request.history)} history messages for passenger {request.passenger_profile.get('passenger_id') if request.passenger_profile else 'Unknown'}")
    
    history_list = [msg.model_dump() for msg in request.history]
    
    # Generate unique IDs for this execution turn
    thread_id = request.thread_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    return StreamingResponse(
        stream_chat_response(
            query=request.query,
            history=history_list,
            top_k=request.top_k or 5,
            threshold=request.threshold or 0.3,
            passenger_profile=request.passenger_profile,
            run_id=run_id,
            thread_id=thread_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# --- Settings Endpoints ---

class SettingsRequest(BaseModel):
    env: Optional[str] = None
    local_service_provider: Optional[str] = None
    local_model: Optional[str] = None
    lmstudio_api_base: Optional[str] = None
    prod_service_provider: Optional[str] = None
    prod_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # Backward compatibility
    model: Optional[str] = None

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

def get_persisted_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read settings file: {e}")
    return {}

def mask_api_key(key: Optional[str]) -> str:
    if not key:
        return ""
    if key.startswith("sk-") and len(key) > 12:
        return f"{key[:7]}...{key[-4:]}"
    if len(key) > 8:
        return f"{key[:4]}...{key[-4:]}"
    return "..."

@app.get("/settings")
async def get_settings():
    settings = get_persisted_settings()
    env = settings.get("env", "prod")
    
    # Resolve backward-compatible model field
    if env == "local":
        model = settings.get("local_model", "qwen2.5-7b-instruct")
    else:
        model = settings.get("prod_model", settings.get("model", "gpt-4o-mini"))
        
    openai_key = settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY_TEMP") or ""
    anthropic_key = settings.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or ""
    gemini_key = settings.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or ""

    return {
        "env": env,
        "local_service_provider": settings.get("local_service_provider", "LMStudio"),
        "local_model": settings.get("local_model", "qwen2.5-7b-instruct"),
        "lmstudio_api_base": settings.get("lmstudio_api_base", "http://localhost:1234/v1"),
        "prod_service_provider": settings.get("prod_service_provider", "openai"),
        "prod_model": settings.get("prod_model", settings.get("model", "gpt-4o-mini")),
        
        # Backward-compatible fields
        "model": model,
        "openai_api_key": mask_api_key(openai_key),
        "anthropic_api_key": mask_api_key(anthropic_key),
        "gemini_api_key": mask_api_key(gemini_key),
        "is_key_configured": bool(openai_key)
    }

@app.post("/settings")
async def update_settings(req: SettingsRequest):
    settings = get_persisted_settings()
    
    if req.env is not None:
        settings["env"] = req.env
    if req.local_service_provider is not None:
        settings["local_service_provider"] = req.local_service_provider
    if req.local_model is not None:
        settings["local_model"] = req.local_model
    if req.lmstudio_api_base is not None:
        settings["lmstudio_api_base"] = req.lmstudio_api_base
    if req.prod_service_provider is not None:
        settings["prod_service_provider"] = req.prod_service_provider
    if req.prod_model is not None:
        settings["prod_model"] = req.prod_model
        
    # Map backward compatible `model` parameter if present
    if req.model is not None:
        settings["model"] = req.model
        env_to_use = req.env or settings.get("env", "prod")
        if env_to_use == "local":
            settings["local_model"] = req.model
        else:
            settings["prod_model"] = req.model

    # Helper to check and update specific keys
    def update_key(field_name: str, env_var_name: str, submitted_value: Optional[str]):
        if submitted_value is None:
            return
            
        current_key = settings.get(field_name) or os.environ.get(env_var_name) or ""
        current_masked = mask_api_key(current_key)
        
        if submitted_value and submitted_value != current_masked:
            settings[field_name] = submitted_value
            os.environ[env_var_name] = submitted_value
            logger.info(f"Updated setting '{field_name}' and env var '{env_var_name}'")

    update_key("openai_api_key", "OPENAI_API_KEY", req.openai_api_key)
    update_key("anthropic_api_key", "ANTHROPIC_API_KEY", req.anthropic_api_key)
    update_key("gemini_api_key", "GEMINI_API_KEY", req.gemini_api_key)

    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save settings file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings")
        
    return {"status": "success", "message": "Settings updated successfully"}



