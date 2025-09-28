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
  reflection: string;
  tactical_learning?: string | null;
  strategic_learning?: string | null;
  meta_learning?: string | null;
  anti_patterns?: {
    description?: string;
    redundancies?: string[];
    inefficiencies?: string[];
  } | null;
  execution_metadata?: {
    tool_counts?: Record<string, number>;
    efficiency_score?: number;
    patterns?: Record<string, unknown>;
    parallelization_opportunities?: string[];
  } | null;
  confidence_score?: number;
  outcome: "success" | "failure";
  timestamp: string;
  embedding?: number[] | null;
  similarity?: number;
}

export interface Pattern {
  id: string;
  description: string;
  confidence: number;
  success_rate: number;
  applications: number;
  last_used: string | null;
}

export interface ExecutionData {
  task: string;
  context: string | null;
  outcome: "success" | "failure";
  duration: number;
  description: string;
  error: string | null;
}
