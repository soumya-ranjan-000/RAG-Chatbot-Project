import axios from "axios";
import type {
  UploadResponse,
  QueryResponse,
  IngestionRequest,
  IngestionResponse,
  JobProgress,
  S3File,
} from "../types/api";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

let rawPssUrl = import.meta.env.VITE_PSS_API_URL || "http://localhost:8000/api/pss";
if (rawPssUrl && !rawPssUrl.endsWith("/api/pss")) {
  rawPssUrl = rawPssUrl.replace(/\/$/, "") + "/api/pss";
}
export const PSS_API_URL = rawPssUrl;


const client = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add response error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    throw error;
  }
);

export const apiService = {
  /**
   * Upload a file to S3
   */
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await client.post<UploadResponse>("/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  },

  /**
   * Query documents using semantic search
   */
  async queryDocuments(
    text: string,
    topK: number = 5,
    threshold: number = 0.5
  ): Promise<QueryResponse> {
    const response = await client.get<QueryResponse>("/query", {
      params: {
        text,
        top_k: topK,
        threshold,
      },
    });

    return response.data;
  },

  /**
   * Trigger ingestion pipeline
   */
  async triggerIngestion(request: IngestionRequest): Promise<IngestionResponse> {
    const response = await client.post<IngestionResponse>("/ingest", request);
    return response.data;
  },

  /**
   * Get ingestion job progress
   */
  async getIngestionProgress(jobId: string): Promise<JobProgress> {
    const response = await client.get<JobProgress>(`/ingest/progress/${jobId}`);
    return response.data;
  },

  /**
   * Stream ingestion progress using Server-Sent Events
   */
  streamIngestionProgress(
    jobId: string,
    onMessage: (progress: JobProgress) => void,
    onError: (error: Error) => void
  ): EventSource {
    const url = `${API_URL}/ingest/stream/${jobId}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const progress = JSON.parse(event.data);
        onMessage(progress);
      } catch (error) {
        onError(new Error("Failed to parse progress message"));
      }
    };

    eventSource.onerror = () => {
      onError(new Error("SSE connection error"));
      eventSource.close();
    };

    return eventSource;
  },

  /**
   * List files in S3 bucket
   */
  async listFiles(): Promise<S3File[]> {
    const response = await client.get<S3File[]>("/files");
    return response.data;
  },

  /**
   * Delete a file from S3 and its chunks
   */
  async deleteFile(key: string): Promise<any> {
    const response = await client.delete("/files", {
      params: { key },
    });
    return response.data;
  },

  /**
   * Get application settings (model and API key configurations)
   */
  async getSettings(): Promise<{ model: string; openai_api_key: string; is_key_configured: boolean }> {
    const response = await client.get("/settings");
    return response.data;
  },

  /**
   * Update application settings (model and API key configurations)
   */
  async updateSettings(settings: { model: string; openai_api_key?: string }): Promise<any> {
    const response = await client.post("/settings", settings);
    return response.data;
  },
};

export default apiService;
