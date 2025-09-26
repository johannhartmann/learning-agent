"use client";

import { useCoAgentStateRender } from "@copilotkit/react-core";
import { ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { useState } from "react";

import { LEARNING_AGENT_KEY, type LearningAgentState } from "./types";

interface ToolCall {
  name: string;
  args?: Record<string, unknown>;
  result?: unknown;
  status: "in_progress" | "completed" | "error";
}

function ToolCallCard({ tool }: { tool: ToolCall }) {
  const [expanded, setExpanded] = useState(false);

  const getToolColor = (name: string) => {
    if (name.includes("read") || name.includes("ls")) return "var(--color-primary)";
    if (name.includes("write") || name.includes("edit")) return "var(--color-warning)";
    if (name.includes("sandbox") || name.includes("python")) return "var(--color-success)";
    return "var(--color-text-secondary)";
  };

  return (
    <div
      className="rounded-lg border p-3 text-sm"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-background)",
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2">
          {tool.status === "in_progress" ? (
            <Loader2 className="h-4 w-4 animate-spin" style={{ color: "var(--color-primary)" }} />
          ) : null}
          <span className="font-medium" style={{ color: getToolColor(tool.name) }}>
            {tool.name}
          </span>
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4" style={{ color: "var(--color-text-tertiary)" }} />
        ) : (
          <ChevronRight className="h-4 w-4" style={{ color: "var(--color-text-tertiary)" }} />
        )}
      </button>
      {expanded ? (
        <div className="mt-2 space-y-2">
          {tool.args ? (
            <div>
              <p className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>
                Arguments:
              </p>
              <pre
                className="mt-1 overflow-x-auto rounded p-2 text-xs"
                style={{
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-text-primary)",
                }}
              >
                {JSON.stringify(tool.args, null, 2)}
              </pre>
            </div>
          ) : null}
          {tool.result ? (
            <div>
              <p className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>
                Result:
              </p>
              <pre
                className="mt-1 overflow-x-auto rounded p-2 text-xs"
                style={{
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-text-primary)",
                }}
              >
                {typeof tool.result === "string"
                  ? tool.result
                  : JSON.stringify(tool.result, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function AgentStreaming() {
  useCoAgentStateRender<LearningAgentState>({
    name: LEARNING_AGENT_KEY,
    render: ({ status, state, nodeName }) => {
      const todos = state?.todos ?? [];
      const activeTodos = todos.filter(
        (t) => typeof t === "object" && t !== null && "status" in t && t.status === "in_progress"
      );

      if (status === "complete" && activeTodos.length === 0) {
        return null;
      }

      return (
        <div
          className="rounded-lg border p-4"
          style={{
            borderColor: "var(--color-border)",
            backgroundColor: "var(--color-surface)",
          }}
        >
          <div className="mb-3 flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" style={{ color: "var(--color-primary)" }} />
            <span className="text-sm font-medium" style={{ color: "var(--color-text-primary)" }}>
              Agent Working
            </span>
            {nodeName ? (
              <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
                ({nodeName})
              </span>
            ) : null}
          </div>
          {activeTodos.length > 0 ? (
            <div className="space-y-2">
              {activeTodos.map((todo, index) => {
                if (typeof todo === "object" && todo !== null && "content" in todo) {
                  return (
                    <div
                      key={`todo-${index}`}
                      className="flex items-start gap-2 text-sm"
                      style={{ color: "var(--color-text-secondary)" }}
                    >
                      <Loader2
                        className="mt-0.5 h-3 w-3 animate-spin"
                        style={{ color: "var(--color-primary)" }}
                      />
                      <span>{todo.content}</span>
                    </div>
                  );
                }
                return null;
              })}
            </div>
          ) : null}
        </div>
      );
    },
  });

  return null;
}
