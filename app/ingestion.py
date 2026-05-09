import os
import boto3
import tempfile
import uuid
import re
import logging
from datetime import datetime
import numpy as np
from supabase import create_client, Client
from langchain_community.document_loaders import PyPDFLoader
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter

# from sentence_transformers import SentenceTransformer
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger("rag-ingestion")

load_dotenv()
sts = boto3.client("sts")
try:
    print(f"Authenticated as: {sts.get_caller_identity()['Arn']}")
except Exception as e:
    print(f"⚠️ AWS Credentials not found or invalid: {e}")

# ==========================================
# ⚙️ CONFIGURATION & CLIENTS
# ==========================================
S3_BUCKET = "amzn-souranj-rag-docs-prod-789303374640-us-east-1-an"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

s3_client = boto3.client("s3")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file_to_s3(file_content: bytes, file_name: str, bucket_name: str = None):
    """Upload raw bytes to S3 and return the S3 URI."""
    target_bucket = bucket_name or S3_BUCKET
    logger.info(f"Uploading {file_name} to {target_bucket}...")
    
    try:
        s3_client.put_object(
            Bucket=target_bucket,
            Key=file_name,
            Body=file_content
        )
        s3_uri = f"s3://{target_bucket}/{file_name}"
        logger.info(f"Successfully uploaded to {s3_uri}")
        return s3_uri
    except Exception as e:
        logger.error(f"Failed to upload {file_name} to S3: {e}", exc_info=True)
        raise e

# --- REPLACED OpenAI WITH SentenceTransformer ---
# Note: all-MiniLM-L6-v2 produces 384-dimensional vectors.
# Ensure your Supabase column is set to vector(384) instead of vector(1536).
# model = SentenceTransformer('all-MiniLM-L6-v2')
model = OpenAIEmbeddings(
    model="text-embedding-3-small", openai_api_key=os.environ.get("OPENAI_API_KEY_TEMP")
)

# ==========================================
# 🧩 NORMALIZATION & ENRICHMENT
# ==========================================


def normalize_text(text: str) -> str:
    # 1. Standardize whitespace
    text = re.sub(r"\s+", " ", text)
    # 2. Fix the specific 's issue if it persists
    text = re.sub(r"([’'])\s+s", r"\1s", text)
    return text.strip()


def get_enriched_chunk_metadata(
    file_name, chunk_text, chunk_index, page_range, document_id
):
    company_prefix = file_name.split("_")[0].lower()

    category_mapping = {
        "google": {"category": "Ethics", "tags": ["Big Tech", "Conduct"]},
        "apple": {
            "category": "Supply Chain",
            "tags": ["Sustainability", "Human Rights"],
        },
    }

    info = category_mapping.get(
        company_prefix, {"category": "General", "tags": ["Policy"]}
    )

    return {
        "source": file_name,
        "document_id": document_id,
        "chunk_index": chunk_index,
        "page_label": (
            f"Page {page_range}"
            if "-" not in str(page_range)
            else f"Pages {page_range}"
        ),
        "page_range": page_range,  # Storing the raw range (e.g., "1-2")
        "category": info["category"],
        "tags": info["tags"],
        "ingestion_date": datetime.now().strftime("%Y-%m-%d"),
    }


# extraction logics
def extract_pages_from_pdf(file_path: str) -> list:
    """
    Handles the heavy lifting of PDF layout analysis and text reconstruction.
    """
    logger.info(f"Extracting pages from PDF: {file_path}")
    try:
        doc = fitz.open(file_path)
        pages = []
        for page_num, page in enumerate(doc):
            page_text = page.get_text("blocks")
            content = " ".join([b[4].replace("\n", " ") for b in page_text])
            if content.strip():
                pages.append(
                    Document(
                        page_content=normalize_text(content),
                        metadata={
                            "page_number": page_num + 1
                        },  # Humans prefer 1-based indexing
                    )
                )
        logger.info(f"Successfully extracted {len(pages)} pages")
        return pages
    except Exception as e:
        logger.error(f"Extraction error for {file_path}: {e}", exc_info=True)
        return []


# ==========================================
# ☁️ CLOUD PIPELINE LOGIC
# ==========================================


def process_s3_document(s3_key: str, bucket_name: str = None, progress_callback=None):
    # Helper for optional progress reporting.
    def report(stage: str, details: dict = None):
        if progress_callback is not None:
            progress_callback(stage, details)

    # 1. Parse Key if full S3 URI is passed
    if s3_key.startswith("s3://"):
        parts = s3_key.replace("s3://", "").split("/", 1)
        s3_key = parts[1]

    # Use provided bucket or fallback to default
    target_bucket = bucket_name or S3_BUCKET

    logger.info(f"--- Starting Ingestion Pipeline for: {s3_key} in bucket {target_bucket} ---")
    report("Starting ingestion", {"current_file": s3_key})
    
    document_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(s3_key)[-1].lower()

    # 2. Setup Temp File (Windows-safe)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_file_path = temp_file.name
    temp_file.close()

    try:
        # 3. Download
        logger.info(f"Downloading {s3_key} from bucket {target_bucket}")
        report("Downloading file", {"current_file": s3_key})
        s3_client.download_file(target_bucket, s3_key, temp_file_path)
        logger.info(f"Download complete: {temp_file_path}")

        # 4. Load & Process
        documents = []
        clean_text = False

        if ext == ".pdf":
            report("Extracting PDF pages", {"current_file": s3_key})
            documents = extract_pages_from_pdf(temp_file_path)
            clean_text = len(documents) > 0
        elif ext == ".txt":
            report("Loading text file", {"current_file": s3_key})
            logger.info(f"Reading text file: {s3_key}")
            with open(temp_file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
                clean_content = normalize_text(raw_text)
                clean_text = len(clean_content) > 0
                documents = [
                    Document(page_content=clean_content, metadata={"source": s3_key})
                ]
            logger.info(f"Text file loaded and normalized")
        else:
            logger.warning(f"Unsupported file type: {ext}")
            report("Unsupported file type", {"current_file": s3_key})
            return

        if not clean_text:
            logger.warning(f"No text content extracted from {s3_key}")
            report("No text extracted", {"current_file": s3_key})
            return

        # 5. Chunking
        logger.info(f"Splitting document into chunks...")
        report("Chunking document", {"current_file": s3_key})
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=150, separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} chunks")

        report("Converting to vectors", {"current_file": s3_key})
        records_to_insert = []
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        for i, chunk in enumerate(chunks):
            clean_content = chunk.page_content
            if not clean_content:
                continue

            # Embedding
            embedding_vector = model.embed_query(clean_content)

            start_page = chunk.metadata.get("page_number", 1)
            page_display = str(start_page)

            metadata = get_enriched_chunk_metadata(
                s3_key, clean_content, i, page_display, document_id
            )

            records_to_insert.append(
                {
                    "document_name": s3_key,
                    "chunk_content": clean_content,
                    "metadata": metadata,
                    "embedding": embedding_vector,
                }
            )

        # 6. Supabase Upload
        logger.info(f"Uploading {len(records_to_insert)} vectors to Supabase...")
        report("Uploading to Supabase", {"current_file": s3_key})
        
        if records_to_insert:
            batch_size = 50
            for i in range(0, len(records_to_insert), batch_size):
                batch = records_to_insert[i : i + batch_size]
                supabase.table("document_chunks").insert(batch).execute()
                logger.info(f"Uploaded batch {i//batch_size + 1}")
            
            report("Upload complete", {"current_file": s3_key})
            logger.info(f"✅ SUCCESSFULLY INGESTED: {s3_key}")

    except Exception as e:
        logger.error(f"Error processing {s3_key}: {str(e)}", exc_info=True)
        report("Error during processing", {"current_file": s3_key, "errors": [str(e)]})
    finally:
        # 7. Single Cleanup at the very end
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"🧹 Cleaned up temp file.")


if __name__ == "__main__":
    process_s3_document(
        "s3://amzn-souranj-rag-docs-prod-789303374640-us-east-1-an/google_code_of_conduct_one_page.pdf"
    )
