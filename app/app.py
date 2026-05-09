from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import os
import uuid
import asyncio
import json
import logging
from .ingestion import process_s3_document
from typing import Dict, List, Callable, Optional

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


@app.post("/ingest")
async def s3_webhook(request: Request, background_tasks: BackgroundTasks):
    """Ingest documents and return a job ID for tracking progress."""
    
    # 1. Get raw JSON since the structure might vary
    try:
        payload = await request.json()
        logger.info(f"Received /ingest request. Payload: {json.dumps(payload)}")
    except Exception:
        logger.error("Failed to parse JSON payload in /ingest")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 2. Extract Records based on the source (Direct S3 vs EventBridge)
    records = []
    
    if "Records" in payload:
        # Standard S3 Event
        records = payload["Records"]
        logger.info(f"Found {len(records)} records in standard S3 event format")
    elif "detail" in payload:
        # EventBridge wrapper
        detail = payload["detail"]
        records = [{
            "s3": {
                "bucket": { "name": detail.get("bucket", {}).get("name") },
                "object": { "key": detail.get("object", {}).get("key") }
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
            logger.info(f"[{job_id}] Processing file {idx+1}/{len(records)}: {s3_key}")

            # Update progress
            job_progress[job_id]["current_file"] = s3_key
            job_progress[job_id]["processed_files"] = idx + 1

            # Create callback for this document
            callback = create_progress_callback(job_id)

            # Process the document with progress tracking
            process_s3_document(s3_key, progress_callback=callback)

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
