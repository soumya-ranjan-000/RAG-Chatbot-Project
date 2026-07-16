export interface ChunkSource {
  document_name: string;
  chunk_content: string;
  page_label: string;
  similarity: number;
  metadata?: {
    source?: string;
    document_id?: string;
    chunk_index?: number;
    page_label?: string;
    page_range?: string;
    category?: string;
    tags?: string[];
    ingestion_date?: string;
    [key: string]: any;
  };
}

export interface ChatMetrics {
  ttft_ms: number;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: ChunkSource[];
  citations?: {
    index: number;
    document_name: string;
    page_label: string;
    similarity: number;
  }[];
  metrics?: ChatMetrics;
  isStreaming?: boolean;
  runId?: string;
  threadId?: string;
}

export interface ChatRequest {
  query: string;
  history: {
    role: 'user' | 'assistant';
    content: string;
  }[];
  top_k?: number;
  threshold?: number;
}
