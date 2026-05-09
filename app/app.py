from fastapi import FastAPI, BackgroundTasks, Request, HTTPException, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import os
import uuid
import asyncio
import json
import logging
from .ingestion import process_s3_document, upload_file_to_s3
from .retrieval import search_vector_chunks
from typing import Dict, List, Callable, Optional, Union

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag-app")

app = FastAPI()

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
