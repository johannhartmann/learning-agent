import { useEffect, useState, useCallback } from 'react';
import type { Memory, Pattern, ExecutionData } from '@/app/types/types';

interface MemoriesResponse {
  memories: Memory[];
  patterns: Pattern[];
  learning_queue: ExecutionData[];
}

export function useMemoryPolling(intervalMs: number = 5000) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [learningQueue, setLearningQueue] = useState<ExecutionData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMemories = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch('http://localhost:8001/api/memories');
      if (!response.ok) {
        throw new Error(`Failed to fetch memories: ${response.statusText}`);
      }
      
      const data: MemoriesResponse = await response.json();
      setMemories(data.memories);
      setPatterns(data.patterns);
      setLearningQueue(data.learning_queue);
    } catch (err) {
      console.error('Error fetching memories:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch memories');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchMemories();

    // Set up polling interval
    const interval = setInterval(fetchMemories, intervalMs);

    return () => clearInterval(interval);
  }, [fetchMemories, intervalMs]);

  return {
    memories,
    patterns,
    learningQueue,
    isLoading,
    error,
    refetch: fetchMemories,
  };
}