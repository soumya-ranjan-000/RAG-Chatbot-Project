// File upload response
export interface UploadResponse {
  message: string;
  filename: string;
  s3_uri: string;
  content_type: string;
}

// Metadata for document chunks
export interface ChunkMetadata {
  source?: string;
  document_id?: string;
  chunk_index?: number;
  page_label?: string;
  page_range?: string;
  category?: string;
  tags?: string[];
  ingestion_date?: string;
  [key: string]: any;
}

// Single document chunk from query results
export interface DocumentChunk {
  id: string;
  chunk_content: string;
  metadata: ChunkMetadata;
  similarity: number;
}

// Query response
export interface QueryResponse {
  query: string;
  results_count: number;
  results: DocumentChunk[];
}

// Ingestion job request (S3 event format)
export interface S3EventRecord {
  s3: {
    bucket: { name: string };
    object: { key: string };
  };
}

export interface IngestionRequest {
  Records: S3EventRecord[];
}

// Ingestion job response
export interface IngestionResponse {
  job_id: string;
  status: string;
  files: number;
}

// Job progress status
export type JobStatus = "pending" | "in_progress" | "completed" | "failed";

// Job progress response
export interface JobProgress {
  status: JobStatus;
  total_files: number;
  processed_files: number;
  current_file: string;
  message: string;
  errors: string[];
}

// Search history entry
export interface SearchHistoryEntry {
  id: string;
  query: string;
  timestamp: number;
  topK?: number;
  threshold?: number;
}

// Export data type
export type ExportFormat = "csv" | "json";

// S3 file information
export interface S3File {
  key: string;
  size: number;
  last_modified: string;
  s3_uri: string;
  indexed: boolean;
}
