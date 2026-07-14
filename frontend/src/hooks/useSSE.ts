import { useEffect, useRef, useCallback } from "react";
import type { JobProgress } from "../types/api";

interface UseSSEOptions {
  onMessage?: (data: JobProgress) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
}

export const useSSE = (url: string | null, options: UseSSEOptions = {}) => {
  const eventSourceRef = useRef<EventSource | null>(null);
  const { onMessage, onError, onOpen } = options;

  const close = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!url) return;

    try {
      const eventSource = new EventSource(url);

      eventSource.onopen = () => {
        onOpen?.();
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch (error) {
          onError?.(new Error("Failed to parse SSE message"));
        }
      };

      eventSource.onerror = () => {
        onError?.(new Error("SSE connection error"));
        eventSource.close();
      };

      eventSourceRef.current = eventSource;

      return () => {
        eventSource.close();
      };
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error("SSE error"));
    }
  }, [url, onMessage, onError, onOpen]);

  return { close };
};
