import type {
  ExecutionData,
  Memory,
  Pattern,
  TodoItem,
} from "@/app/types/types";

export interface LearningAgentState {
  todos?: Array<TodoItem | string> | null;
  files?: Record<string, string> | null;
  memories?: Memory[] | null;
  patterns?: Pattern[] | null;
  learning_queue?: ExecutionData[] | null;
}

export const LEARNING_AGENT_KEY = "learning_agent" as const;
