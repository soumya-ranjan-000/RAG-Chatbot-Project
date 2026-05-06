import os
import boto3
import tempfile
import uuid
import re
import time
from datetime import datetime
from supabase import create_client, Client
from langchain_community.document_loaders import PyPDFLoader
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

sts = boto3.client("sts")
print(f"Authenticated as: {sts.get_caller_identity()['Arn']}")

# ==========================================
# ⚙️ CONFIGURATION & CLIENTS
# ==========================================
S3_BUCKET = "amzn-souranj-rag-docs-prod-789303374640-us-east-1-an"
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "Invalid"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "Invalid"

s3_client = boto3.client("s3")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- REPLACED OpenAI WITH SentenceTransformer ---
# Note: all-MiniLM-L6-v2 produces 384-dimensional vectors.
# Ensure your Supabase column is set to vector(384) instead of vector(1536).
model = SentenceTransformer("all-MiniLM-L6-v2")

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
def extract_pages_from_pdf(file_path: str) -> list[Document]:
    """
    Handles the heavy lifting of PDF layout analysis and text reconstruction.
    """
    try:
        doc = fitz.open(file_path)
        pages = []
        for page_num, page in enumerate(doc):  # type: ignore
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
        return pages
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return []


# ==========================================
# ☁️ CLOUD PIPELINE LOGIC
# ==========================================


def process_s3_document(s3_key: str, progress_callback=None):
    # 1. Parse Key if full S3 URI is passed
    if s3_key.startswith("s3://"):
        parts = s3_key.replace("s3://", "").split("/", 1)
        s3_key = parts[1]

    print(f"📥 Starting ingestion for: {s3_key}")

    if progress_callback:
        progress_callback("📥 Starting download...")

    document_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(s3_key)[-1].lower()

    # 2. Setup Temp File (Windows-safe)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_file_path = temp_file.name
    temp_file.close()

    try:
        # 3. Download
        print(f"Downloading {s3_key}...")
        if progress_callback:
            progress_callback("⬇️ Downloading from S3...")
            time.sleep(0.5)  # Allow client to receive update

        s3_client.download_file(S3_BUCKET, s3_key, temp_file_path)

        # 4. Load & Process (Combined into one block)
        if progress_callback:
            progress_callback("📄 Extracting text...")
            time.sleep(0.5)  # Allow client to receive update

        if ext == ".pdf":
            documents = extract_pages_from_pdf(temp_file_path)
            clean_text = True
        elif ext == ".txt":
            with open(temp_file_path, "r", encoding="utf-8") as f:
                clean_text = normalize_text(f.read())
                # Wrap in a LangChain Document so your existing chunker still works
                documents = [
                    Document(page_content=clean_text, metadata={"source": s3_key})
                ]
        else:
            print(f"Unsupported extension: {ext}")
            if progress_callback:
                progress_callback("❌ Unsupported file type")
            return

        if not clean_text:
            print("⚠️ No text extracted. Skipping.")
            if progress_callback:
                progress_callback("⚠️ No text extracted")
            return

        # 5. Chunking
        print(f"Chunking {s3_key}...")
        if progress_callback:
            progress_callback(f"✂️ Splitting into chunks ({len(documents)} pages)...")
            time.sleep(0.5)  # Allow client to receive update

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=150, separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)  # type: ignore

        print(f"Converting to vector...")
        if progress_callback:
            progress_callback(f"🧮 Converting to embeddings ({len(chunks)} chunks)...")
            time.sleep(0.5)  # Allow client to receive update

        records_to_insert = []
        for i, chunk in enumerate(chunks):
            clean_content = chunk.page_content  # Already normalized above
            if not clean_content:
                continue

            # Embedding
            embedding_vector = model.encode(clean_content).tolist()

            # Get the starting page from metadata
            start_page = chunk.metadata.get("page_number", 1)

            page_display = str(start_page)

            # Metadata
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
        print(f"Uploading to Supabase {s3_key}...")
        if progress_callback:
            progress_callback(
                f"📤 Uploading {len(records_to_insert)} chunks to Supabase..."
            )
            time.sleep(0.5)  # Allow client to receive update

        if records_to_insert:
            for i in range(0, len(records_to_insert), 50):
                batch = records_to_insert[i : i + 50]
                supabase.table("document_chunks").insert(batch).execute()

                # Update progress during upload
                percent = min(100, int((i + 50) / len(records_to_insert) * 100))
                if progress_callback:
                    progress_callback(f"📤 Uploading... {percent}% complete")
                    time.sleep(0.2)  # Small delay between batches

            print(f"✅ Ingested {len(records_to_insert)} chunks for {s3_key}")
            if progress_callback:
                progress_callback(
                    f"✅ Successfully ingested {len(records_to_insert)} chunks!"
                )
                time.sleep(0.5)  # Allow final message to be sent

    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        if progress_callback:
            progress_callback(f"❌ Error: {str(e)}")
    finally:
        # 7. Single Cleanup at the very end
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"🧹 Cleaned up temp file.")


if __name__ == "__main__":
    process_s3_document(
        "s3://amzn-souranj-rag-docs-prod-789303374640-us-east-1-an/google_code_of_conduct.pdf"
    )
    # pass
