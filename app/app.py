from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
import os
import uuid
import asyncio
import json
from app.ingestion import process_s3_document
from typing import Dict, List, Callable

app = FastAPI()

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
async def s3_webhook(payload: dict, background_tasks: BackgroundTasks):
    """Ingest documents and return a job ID for tracking progress."""

    job_id = str(uuid.uuid4())
    records = payload.get("Records", [])

    # Initialize job progress
    job_progress[job_id] = {
        "status": "pending",
        "total_files": len(records),
        "processed_files": 0,
        "current_file": None,
        "message": "Starting ingestion...",
        "errors": [],
    }

    # Process files in background
    background_tasks.add_task(process_ingestion, job_id, records)

    return {"job_id": job_id, "status": "processing", "files": len(records)}


async def process_ingestion(job_id: str, records: List[dict]):
    """Process ingestion and update progress."""
    try:
        job_progress[job_id]["status"] = "in_progress"

        for idx, record in enumerate(records):
            s3_key = record["s3"]["object"]["key"]

            # Update progress
            job_progress[job_id]["current_file"] = s3_key
            job_progress[job_id]["processed_files"] = idx + 1

            # Create callback for this document
            callback = create_progress_callback(job_id)

            # Process the document with progress tracking
            process_s3_document(s3_key, progress_callback=callback)

        job_progress[job_id]["status"] = "completed"
        job_progress[job_id]["message"] = "Ingestion completed successfully"

    except Exception as e:
        job_progress[job_id]["status"] = "failed"
        job_progress[job_id]["message"] = f"Error: {str(e)}"
        job_progress[job_id]["errors"].append(str(e))


@app.get("/ingest/progress/{job_id}")
async def get_progress(job_id: str):
    """Get current progress of an ingestion job."""
    if job_id not in job_progress:
        return {"error": "Job not found"}
    return job_progress[job_id]


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
