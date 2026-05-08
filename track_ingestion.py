import requests
import json
import time
from datetime import datetime


def print_progress_bar(current, total):
    """Print a nice progress bar."""
    if total == 0:
        return
    percent = current / total
    bar_length = 40
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"[{bar}] {percent:.1%} ({current}/{total})"


# Start ingestion
print("🚀 Starting ingestion...")
response = requests.post(
    "http://127.0.0.1:8000/ingest",
    json={
        "Records": [
            {
                "s3": {
                    "object": {
                        "key": "s3://amzn-souranj-rag-docs-prod-789303374640-us-east-1-an/google_code_of_conduct_one_page.pdf"
                    }
                }
            }
        ]
    },
)

job_data = response.json()
job_id = job_data["job_id"]
print(f"📋 Job ID: {job_id}")
print(f"📝 Total files: {job_data['files']}\n")

# Stream progress with visual formatting
start_time = time.time()
last_status = None

try:
    with requests.get(
        f"http://127.0.0.1:8000/ingest/stream/{job_id}", stream=True, timeout=120
    ) as r:
        for line in r.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode().replace("data: ", ""))

                    status = data.get("status", "unknown")
                    processed = data.get("processed_files", 0)
                    total = data.get("total_files", 0)
                    message = data.get("message", "")
                    current_file = data.get("current_file", "")

                    # Print status change
                    if status != last_status:
                        print(f"\n📊 Status: {status.upper()}")
                        last_status = status

                    # Print progress bar
                    if total > 0:
                        progress = print_progress_bar(processed, total)
                        print(f"   {progress}")

                    # Print current file
                    if current_file:
                        file_name = current_file.split("/")[-1]
                        print(f"   📄 {file_name}")

                    # Print message
                    if message:
                        print(f"   💬 {message}")

                    # Final message
                    if status in ["completed", "failed"]:
                        elapsed = time.time() - start_time
                        print(f"\n✅ {status.upper()} in {elapsed:.2f}s")

                        if data.get("errors"):
                            print("❌ Errors:")
                            for error in data["errors"]:
                                print(f"   - {error}")
                        break

                except json.JSONDecodeError:
                    continue

except requests.exceptions.RequestException as e:
    print(f"❌ Connection error: {e}")
