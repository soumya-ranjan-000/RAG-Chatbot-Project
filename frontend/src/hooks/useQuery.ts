import { useState, useCallback } from "react";
import type { QueryResponse, DocumentChunk } from "../types/api";
import apiService from "../services/api";

export const useQuery = () => {
  const [results, setResults] = useState<DocumentChunk[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState<string>("");

  const query = useCallback(
    async (
      text: string,
      topK: number = 5,
      threshold: number = 0.5
    ): Promise<QueryResponse | null> => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiService.queryDocuments(text, topK, threshold);
        setResults(response.results);
        setLastQuery(text);
        return response;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to query documents";
        setError(errorMessage);
        setResults([]);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const clearResults = useCallback(() => {
    setResults([]);
    setLastQuery("");
    setError(null);
  }, []);

  return {
    results,
    loading,
    error,
    lastQuery,
    query,
    clearResults,
  };
};
