import marimo

__generated_with = "0.23.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    For a production-grade ingestion pipeline using AWS S3 and Supabase, the architecture generally flows like this:

    Trigger: A new document is uploaded to your S3 bucket.

    Compute: An AWS Lambda function (or an ECS container) is triggered by the S3 event.

    Processing: The script downloads the file, extracts the text, normalizes it, and splits it into chunks.

    Embedding: The chunks are sent to an embedding model (like OpenAI or HuggingFace).

    Storage: The text chunks, metadata, and vector embeddings are saved to Supabase (using pgvector).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 1: Prepare Supabase (PostgreSQL + pgvector)
    Before we write the ingestion code, Supabase needs to be ready to store vector embeddings. Supabase uses the pgvector extension for this.

    1. Go to your Supabase dashboard and navigate to the SQL Editor.

    2. Run the following SQL to enable the vector extension and create your documents table. We will use 1536 dimensions, which is standard for OpenAI's text-embedding-3-small or text-embedding-ada-002.
    """)
    return


app._unparsable_cell(
    """
    _df = mo.sql(
        f\"\"\"
        -- Enable the pgvector extension to work with embedding vectors
        create extension if not exists vector;

        -- Create a table to store your document chunks and their embeddings
        create table document_chunks (
            id uuid primary key default gen_random_uuid(),
            document_name text not null,
            chunk_content text not null,
            metadata jsonb default '{}'::jsonb,
            embedding vector(1536) not null,
            created_at timestamp with time zone default timezone('utc'::text, now()) not null
        );

        -- Create a generic HNSW index for fast similarity search
        create index on document_chunks using hnsw (embedding vector_ip_ops);
        \"\"\"
    )
    """,
    name="_"
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Need to update the vector dimension for SentenceTransformer
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Run this in Supabase SQL Editor if you previously created a 1536-dim column
        -- alter table document_chunks 
        -- alter column embedding type vector(384);
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    all-MiniLM-L6-v2 which creates 384-dimension vectors. OpenAI’s 3-small creates 1536-dimension vectors. so if using openai, update the table
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- 1. Update the column to 1536 dimensions
        alter table document_chunks 
        alter column embedding type vector(1536);
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- 2. Update your search function to match
        create or replace function match_documents (
          query_embedding vector(1536),
          match_threshold float,
          match_count int
        )
        returns table (
          id uuid,
          chunk_content text,
          metadata jsonb,
          similarity float
        )
        language plpgsql
        as $$
        begin
          return query
          select
            document_chunks.id,
            document_chunks.chunk_content,
            document_chunks.metadata,
            1 - (document_chunks.embedding <=> query_embedding) as similarity
          from document_chunks
          where 1 - (document_chunks.embedding <=> query_embedding) > match_threshold
          order by document_chunks.embedding <=> query_embedding
          limit match_count;
        end;
        $$;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 2: Set Up the AWS S3 Bucket
    You need a dedicated bucket for your raw documents.

    1. Go to the AWS S3 Console and create a new bucket (e.g., my-company-rag-docs-prod).

    2. Keep the bucket private. In a production RAG system, your policy documents and company data should never be publicly accessible.

    3. Note down the bucket name and ensure you have an IAM User/Role with s3:GetObject permissions so your Python code can read from it.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 3: The Core Python Ingestion Logic
    This script replaces your local folder reading with S3 streaming using boto3, chunks the text using LangChain, generates embeddings, and pushes everything to Supabase.

    Prerequisites:
    """)
    return


app._unparsable_cell(
    r"""
    pip install boto3 supabase langchain-openai tiktoken pypdf
    """,
    name="_"
)


@app.cell
def _():
    import os
    import boto3
    import tempfile
    import uuid
    import re
    from datetime import datetime
    import numpy as np
    from supabase import create_client, Client
    from langchain_community.document_loaders import PyPDFLoader
    import fitz
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    # from sentence_transformers import SentenceTransformer
    from langchain_openai import OpenAIEmbeddings
    from langchain_core.documents import Document

    return (
        Client,
        Document,
        OpenAIEmbeddings,
        RecursiveCharacterTextSplitter,
        boto3,
        create_client,
        datetime,
        fitz,
        os,
        re,
        tempfile,
        uuid,
    )


@app.cell
def _():
    from dotenv import load_dotenv
    load_dotenv()
    return


@app.cell
def _(os):
    # Correct way
    print(os.environ.get("OPENAI_API_KEY_TEMP"), len(os.environ.get("OPENAI_API_KEY_TEMP")))
    return


@app.cell
def _(boto3):
    sts = boto3.client('sts')
    print(f"Authenticated as: {sts.get_caller_identity()['Arn']}")
    return


@app.cell
def _(Client, OpenAIEmbeddings, boto3, create_client, datetime, os, re):
    # ==========================================
    # ⚙️ CONFIGURATION & CLIENTS
    # ==========================================
    S3_BUCKET = "amzn-souranj-rag-docs-prod-789303374640-us-east-1-an"
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    s3_client = boto3.client('s3')
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # --- REPLACED OpenAI WITH SentenceTransformer ---
    # Note: all-MiniLM-L6-v2 produces 384-dimensional vectors.
    # Ensure your Supabase column is set to vector(384) instead of vector(1536).
    # model = SentenceTransformer('all-MiniLM-L6-v2')
    model = OpenAIEmbeddings(
        model="text-embedding-3-small", 
        openai_api_key=os.environ.get("OPENAI_API_KEY_TEMP")
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

    def get_enriched_chunk_metadata(file_name, chunk_text, chunk_index, page_range, document_id):
        company_prefix = file_name.split('_')[0].lower()

        category_mapping = {
            "google": {"category": "Ethics", "tags": ["Big Tech", "Conduct"]},
            "apple": {"category": "Supply Chain", "tags": ["Sustainability", "Human Rights"]},
        }

        info = category_mapping.get(company_prefix, {"category": "General", "tags": ["Policy"]})

        return {
            "source": file_name,
            "document_id": document_id,
            "chunk_index": chunk_index,
            "page_label": f"Page {page_range}" if "-" not in str(page_range) else f"Pages {page_range}",
            "page_range": page_range, # Storing the raw range (e.g., "1-2")
            "category": info["category"],
            "tags": info["tags"],
            "ingestion_date": datetime.now().strftime("%Y-%m-%d")
        }

    return (
        S3_BUCKET,
        get_enriched_chunk_metadata,
        model,
        normalize_text,
        s3_client,
        supabase,
    )


@app.cell
def _(Document, fitz, normalize_text):
    # extraction logics
    def extract_pages_from_pdf(file_path: str) -> list:
        """
        Handles the heavy lifting of PDF layout analysis and text reconstruction.
        """
        try:
            doc = fitz.open(file_path)
            pages = []
            for page_num, page in enumerate(doc):
                page_text = page.get_text("blocks")
                content = " ".join([b[4].replace('\n', ' ') for b in page_text])
                if content.strip():
                    pages.append(Document(
                        page_content=normalize_text(content),
                        metadata={"page_number": page_num + 1} # Humans prefer 1-based indexing
                    ))
            return pages
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return None

    return (extract_pages_from_pdf,)


@app.cell
def _(
    Document,
    RecursiveCharacterTextSplitter,
    S3_BUCKET,
    extract_pages_from_pdf,
    get_enriched_chunk_metadata,
    model,
    normalize_text,
    os,
    s3_client,
    supabase: "Client",
    tempfile,
    uuid,
):
    # ==========================================
    # ☁️ CLOUD PIPELINE LOGIC
    # ==========================================

    def process_s3_document(s3_key: str):
        # 1. Parse Key if full S3 URI is passed
        if s3_key.startswith("s3://"):
            parts = s3_key.replace("s3://", "").split("/", 1)
            s3_key = parts[1]

        print(f"📥 Starting ingestion for: {s3_key}")
        document_id = str(uuid.uuid4())[:8]
        ext = os.path.splitext(s3_key)[-1].lower()

        # 2. Setup Temp File (Windows-safe)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        temp_file_path = temp_file.name
        temp_file.close() 

        try:
            # 3. Download
            print(f"Downloading {s3_key}...")
            s3_client.download_file(S3_BUCKET, s3_key, temp_file_path)

            # 4. Load & Process (Combined into one block)
            if ext == '.pdf':
                documents = extract_pages_from_pdf(temp_file_path)
                clean_text=True
            elif ext == '.txt':
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    clean_text = normalize_text(f.read())
                    # Wrap in a LangChain Document so your existing chunker still works
                    documents = [Document(page_content=clean_text, metadata={"source": s3_key})]
            else:
                print(f"Unsupported extension: {ext}")
                return

            if not clean_text:
                print("⚠️ No text extracted. Skipping.")
                return


            # 5. Chunking
            print(f"Chunking {s3_key}...")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, 
                chunk_overlap=150, 
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)

            print(f"Converting to vector...")
            records_to_insert = []
            for i, chunk in enumerate(chunks):
                clean_content = chunk.page_content # Already normalized above
                if not clean_content: continue

                # Embedding
                # embedding_vector = model.encode(clean_content).tolist()
                embedding_vector = model.embed_query(clean_content)

                # Get the starting page from metadata
                start_page = chunk.metadata.get("page_number", 1)

                page_display = str(start_page)

                # Metadata
                metadata = get_enriched_chunk_metadata(
                    s3_key, clean_content, i, page_display, document_id
                )

                records_to_insert.append({
                    "document_name": s3_key,
                    "chunk_content": clean_content,
                    "metadata": metadata,
                    "embedding": embedding_vector
                })


            # 6. Supabase Upload
            print(f"Uploading to Supabase {s3_key}...")
            if records_to_insert:
                for i in range(0, len(records_to_insert), 50):
                    batch = records_to_insert[i:i + 50]
                    supabase.table("document_chunks").insert(batch).execute()
                print(f"✅ Ingested {len(records_to_insert)} chunks for {s3_key}")

        except Exception as e:
            print(f"❌ Error during processing: {str(e)}")
        finally:
            # 7. Single Cleanup at the very end
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"🧹 Cleaned up temp file.")

    return (process_s3_document,)


@app.cell
def _(process_s3_document):
    if __name__ == "__main__":
        process_s3_document("s3://amzn-souranj-rag-docs-prod-789303374640-us-east-1-an/google_code_of_conduct_one_page.pdf")
        # pass
    return


@app.cell
def _():
    [
      {
        "id": "c238116b-b628-42f2-8ac8-5845de9d518b",
        "document_name": "google_code_of_conduct_one_page.pdf",
        "chunk_content": "Board & Governance https://abc.xyz/investor/google-code-of-conduct/ Google Code of Conduct The Google Code of Conduct is one of the ways we put Google’s values into practice. It’s built around the recognition that everything we do in connection with our work at Google will be, and should be, measured against the highest possible standards of ethical business conduct. We set the bar that high for practical as well as aspirational reasons: Our commitment to the highest standards helps us hire great people, build great products, and attract loyal users. Respect for our users, for the opportunity, and for each other are foundational to our success, and are something we need to support every day. So please do read the Code and Google’s values, and follow both in spirit and letter, always bearing in mind that each of us has a personal responsibility to incorporate, and to encourage other Googlers to incorporate, the principles of the Code and values into our work. And if you have a question",
        "metadata": {
          "tags": [
            "Big Tech",
            "Conduct"
          ],
          "source": "google_code_of_conduct_one_page.pdf",
          "category": "Ethics",
          "page_label": "Page 1",
          "page_range": "1",
          "chunk_index": 0,
          "document_id": "35bf9f06",
          "ingestion_date": "2026-05-09"
        }
      },
      {
        "id": "457d8f71-23df-4bae-acff-970ca0cf371a",
        "document_name": "google_code_of_conduct_one_page.pdf",
        "chunk_content": "to incorporate, and to encourage other Googlers to incorporate, the principles of the Code and values into our work. And if you have a question or ever think that one of your fellow Googlers or the company as a whole may be falling short of our commitment, don’t be silent. We want – and need – to hear from you. Who Must Follow Our Code? We expect all of our employees and Board members to know and follow the Code. Failure to do so can result in disciplinary action, including termination of employment. Moreover, while the Code is specifically written for Google employees and Board members, we expect members of our extended workforce (temps, vendors, and independent contractors) and others who",
        "metadata": {
          "tags": [
            "Big Tech",
            "Conduct"
          ],
          "source": "google_code_of_conduct_one_page.pdf",
          "category": "Ethics",
          "page_label": "Page 1",
          "page_range": "1",
          "chunk_index": 1,
          "document_id": "35bf9f06",
          "ingestion_date": "2026-05-09"
        }
      }
    ]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Retrieve context from Supabase - vector similarity search

    The most efficient way to do this is by calling a PostgreSQL function (stored procedure) via the Supabase client.

    ### Step 1: Create the Search Function in Supabase
    Run this SQL in your Supabase SQL Editor. This function calculates the distance between your query embedding and your stored chunks, returning the most relevant matches.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        create or replace function match_documents (
          query_embedding vector(384),
          match_threshold float,
          match_count int
        )
        returns table (
          id uuid,
          chunk_content text,
          metadata jsonb,
          similarity float
        )
        language plpgsql
        as $$
        begin
          return query
          select
            document_chunks.id,
            document_chunks.chunk_content,
            document_chunks.metadata,
            1 - (document_chunks.embedding <=> query_embedding) as similarity
          from document_chunks
          where 1 - (document_chunks.embedding <=> query_embedding) > match_threshold
          order by document_chunks.embedding <=> query_embedding
          limit match_count;
        end;
        $$;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Step 2: Python Retrieval Script
    This script takes a user's natural language query, converts it into a vector using your all-MiniLM-L6-v2 model, and fetches the top results from Supabase.
    """)
    return


@app.cell
def _(model, supabase: "Client"):
    # import os
    # from supabase import create_client, Client
    # from sentence_transformers import SentenceTransformer
    # from dotenv import load_dotenv

    # load_dotenv()

    # 1. Setup Clients
    # SUPABASE_URL = os.environ.get("SUPABASE_URL")
    # SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    # supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Use the SAME model used during ingestion
    # model = SentenceTransformer('all-MiniLM-L6-v2')

    def retrieve_context(query: str, count: int = 3):
        print(f"🔍 Searching for: {query}")

        # 2. Vectorize the User Query
        query_embedding = model.embed_query(query)

        # 3. Call the Supabase 'match_documents' function
        response = supabase.rpc(
            'match_documents', 
            {
                'query_embedding': query_embedding,
                'match_threshold': 0.5, # Adjust based on how strict you want matches to be
                'match_count': count,
            }
        ).execute()

        return response.data

    return (retrieve_context,)


@app.cell
def _(retrieve_context):
    if __name__ == "__main__":
        user_query = "How does Google encourage employees to respond if they see a colleague or the company falling short of the Code?"

        results = retrieve_context(user_query)

        if results:
            print(f"\n✅ Found {len(results)} relevant chunks:\n")
            for idx, res in enumerate(results):
                print(f"--- Result {idx + 1} (Similarity: {res['similarity']:.4f}) ---")
                print(f"Source: {res['metadata'].get('source')}")
                print(f"Page No: {res['metadata'].get('page_label')}")
                print(f"Content: {res['chunk_content']}")
                print("\n")
        else:
            print("❌ No relevant context found.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Comprehension Questions

    What is the primary purpose of the Google Code of Conduct?

    Why does Google set the bar for ethical business conduct so high?

    Which three groups are explicitly expected to follow the Code?

    What are the potential consequences for employees who fail to follow the Code?

    How does Google encourage employees to respond if they see a colleague or the company falling short of the Code?
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Pre-Deployment: Wrapp the ingestion logic in FastAPI

    Also define the payload structure to mirror an S3 event, the final step is ensuring the POST endpoint correctly parses that specific JSON structure and triggers your processing logic.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    1. Update your FastAPI Endpoint
    Ensure your main.py (or equivalent) is set up to drill down into that nested dictionary to extract the key.
    """)
    return


@app.cell
def _(IndexErrors, process_s3_document):
    from fastapi import FastAPI, BackgroundTasks
    from pydantic import BaseModel
    from typing import List

    app = FastAPI()

    # This matches the structure you provided
    class S3Object(BaseModel):
        key: str

    class S3Record(BaseModel):
        s3: dict # Contains the 'object' with the 'key'

    class S3Payload(BaseModel):
        Records: List[dict]

    @app.post("/ingest")
    async def trigger_ingestion(payload: S3Payload, background_tasks: BackgroundTasks):
        # Extract the key from your specific JSON structure
        try:
            s3_key = payload.Records[0]['s3']['object']['key']
        
            # Use BackgroundTasks so the HTTP request returns 202 immediately 
            # while the heavy processing happens in the background.
            background_tasks.add_task(process_s3_document, s3_key)
        
            return {"status": "accepted", "file": s3_key}
        except (KeyError, IndexErrors):
            return {"status": "error", "message": "Invalid payload structure"}

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    2. Configuration on Render
    To deploy this successfully, make sure your Start Command in the Render Dashboard reflects the web server:

    - Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

    - (Note: main is your filename, app is your FastAPI instance name).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # After Deployement - Render
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Connecting S3 to Render

    Option A: AWS EventBridge (The "Clean" Way)
    1. Go to Amazon EventBridge in the AWS Console.

    2. Create a Pipe or an API Destination.

    3. Set the Source to your S3 Bucket (Object Created).

    4. Set the Target to your Render URL: https://your-service.onrender.com/ingest.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Option B: Simple Lambda Proxy

    If you want to keep it simple, a 5-line AWS Lambda function triggered by S3 can simply forward the event to Render:
    """)
    return


@app.cell
def _():
    import requests

    def lambda_handler(event, context):
        # Forwards the exact payload you provided to Render
        requests.post("https://your-service.onrender.com/ingest", json=event)
        return {"statusCode": 200}

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    EventBridge API Destinations Setup

    1. Enable EventBridge on your S3 Bucket:

    - Go to your S3 Bucket Properties.

    - Scroll down to Event notifications -> Amazon EventBridge.

    - Click Edit and set it to On.

    2. Create a Connection (Auth):

    - Go to the EventBridge Console -> API destinations -> Connections.

    - Click Create connection. Name it Render-FastAPI-Connection.

    - Destination type: Other. Authorization type: None (unless you added a secret header to your FastAPI).

    3. Create the API Destination:

    - Go to API destinations -> Create API destination.

    - API destination endpoint: https://your-render-app.onrender.com/ingest

    - HTTP method: POST.

    4. Create the Rule:

    - Go to Rules -> Create rule.

    - Event pattern: Choose AWS services, S3, and Object Created.

    - Target: Select API destination and choose the one you just created.
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
