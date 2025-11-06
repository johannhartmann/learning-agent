export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  status: "pending" | "completed" | "error";
}

// Sandbox-specific types
export interface SandboxImage {
  type: "matplotlib" | "pil" | "other";
  format: "png" | "jpeg";
  base64: string;
}

export interface SandboxResult {
  stdout?: string;
  stderr?: string;
  images?: SandboxImage[];
  tables?: Array<Record<string, unknown>>;
  success?: boolean;
}

export interface SubAgent {
  id: string;
  name: string;
  subAgentName: string;
  input: unknown;
  output?: unknown;
  status: "pending" | "active" | "completed" | "error";
}

export interface FileItem {
  path: string;
  content: string;
}

export interface TodoItem {
  id?: string;
  content: string;
  status: "pending" | "in_progress" | "completed";
  createdAt?: Date;
  updatedAt?: Date;
}

export interface Thread {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
}

// Learning-specific types
export interface Memory {
  id: string;
  task: string;
  context: string | null;
  narrative: string;
  learnings: string;  // Single unified learning field
  reflection?: string;  // Keep for backward compatibility
  confidence_score?: number;
  outcome: "success" | "failure";
  timestamp: string;
  embedding?: number[] | null;
  similarity?: number;
}
