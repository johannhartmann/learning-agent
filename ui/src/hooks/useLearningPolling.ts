import { useCallback, useEffect, useState } from "react";

import type { Memory } from "@/app/types/types";

// Always use the Next.js proxy route - no direct backend access
function getApiUrl(): string {
  return "/api/learnings";
}

interface LearningsResponse {
  learnings: Memory[];
}

export function useLearningPolling(intervalMs: number = 5000) {
  const [learnings, setLearnings] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLearnings = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const url = getApiUrl();
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch learnings: ${response.statusText}`);
      }
      const data: LearningsResponse = await response.json();
      setLearnings(data.learnings ?? []);
    } catch (err) {
      console.error("Error fetching learnings:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch learnings");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLearnings();
    const interval = setInterval(fetchLearnings, intervalMs);
    return () => clearInterval(interval);
  }, [fetchLearnings, intervalMs]);

  return {
    learnings,
    isLoading,
    error,
    refetch: fetchLearnings,
  };
}
