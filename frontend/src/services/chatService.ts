const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

export interface StreamEvent {
  type: 'sources' | 'token' | 'citations' | 'metrics' | 'done' | 'error' | 'tool_call' | 'tool_result' | 'info';
  content?: string;
  sources?: any[];
  citations?: any[];
  metrics?: any;
  message?: string;
  name?: string;
  args?: any;
  result?: any;
  run_id?: string;
  thread_id?: string;
}

export const chatService = {
  /**
   * Stream RAG / Agent Chat response from the backend
   */
  async streamChat(
    query: string,
    history: { role: 'user' | 'assistant'; content: string }[],
    onMessage: (event: StreamEvent) => void,
    onDone: () => void,
    onError: (error: any) => void,
    topK: number = 5,
    threshold: number = 0.3,
    passengerProfile: any = null,
    threadId: string | null = null
  ): Promise<void> {
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          history,
          top_k: topK,
          threshold,
          passenger_profile: passengerProfile,
          thread_id: threadId
        }),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => "Unknown error");
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last partial line in the buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const dataStr = trimmed.slice(6);
            try {
              const data: StreamEvent = JSON.parse(dataStr);
              onMessage(data);
              if (data.type === 'done') {
                onDone();
                return;
              }
            } catch (err) {
              console.error("Error parsing SSE line:", line, err);
            }
          }
        }
      }
      
      onDone();
    } catch (error) {
      console.error("Stream error:", error);
      onError(error);
    }
  }
};
