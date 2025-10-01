import type { Memory, TodoItem } from "@/app/types/types";

export interface LearningAgentState {
  todos?: Array<TodoItem | string> | null;
  subagent_todos?: Record<string, Array<TodoItem | string>> | null;
  files?: Record<string, string> | null;
  memories?: Memory[] | null;
}

export const LEARNING_AGENT_KEY = "learning_agent" as const;
