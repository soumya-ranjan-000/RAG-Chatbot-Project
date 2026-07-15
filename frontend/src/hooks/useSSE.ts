import { useEffect, useRef, useCallback } from "react";
import type { JobProgress } from "../types/api";

interface UseSSEOptions {
  onMessage?: (data: JobProgress) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
}

export const useSSE = (url: string | null, options: UseSSEOptions = {}) => {
  const eventSourceRef = useRef<EventSource | null>(null);
  const onMessageRef = useRef(options.onMessage);
  const onErrorRef = useRef(options.onError);
  const onOpenRef = useRef(options.onOpen);

  // Keep refs up-to-date with latest callbacks
  useEffect(() => {
    onMessageRef.current = options.onMessage;
    onErrorRef.current = options.onError;
    onOpenRef.current = options.onOpen;
  }, [options.onMessage, options.onError, options.onOpen]);

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
        onOpenRef.current?.();
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current?.(data);
        } catch (error) {
          onErrorRef.current?.(new Error("Failed to parse SSE message"));
        }
      };

      eventSource.onerror = () => {
        onErrorRef.current?.(new Error("SSE connection error"));
        eventSource.close();
      };

      eventSourceRef.current = eventSource;

      return () => {
        eventSource.close();
      };
    } catch (error) {
      onErrorRef.current?.(error instanceof Error ? error : new Error("SSE error"));
    }
  }, [url]);

  return { close };
};
