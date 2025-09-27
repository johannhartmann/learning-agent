"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { Check, ChevronDown, ChevronRight, Loader2, X } from "lucide-react";
import { useState } from "react";

function ToolCallCard({
  name,
  args,
  status,
  result,
}: {
  name: string;
  args: Record<string, unknown>;
  status: string;
  result?: unknown;
}) {
  const [expanded, setExpanded] = useState(false);

  const getToolColor = (toolName: string) => {
    if (toolName.includes("read") || toolName.includes("ls")) return "var(--color-primary)";
    if (toolName.includes("write") || toolName.includes("edit")) return "var(--color-warning)";
    if (toolName.includes("sandbox") || toolName.includes("python")) return "var(--color-success)";
    if (toolName.includes("task") || toolName.includes("delegate")) return "var(--color-secondary)";
    return "var(--color-text-secondary)";
  };

  const getStatusIcon = () => {
    if (status === "complete") {
      return <Check className="h-4 w-4" style={{ color: "var(--color-success)" }} />;
    }
    if (status === "error") {
      return <X className="h-4 w-4" style={{ color: "var(--color-error)" }} />;
    }
    return <Loader2 className="h-4 w-4 animate-spin" style={{ color: "var(--color-primary)" }} />;
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
          {getStatusIcon()}
          <span className="font-medium" style={{ color: getToolColor(name) }}>
            {name}
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
          {args && Object.keys(args).length > 0 ? (
            <div>
              <p className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>
                Arguments:
              </p>
              <pre
                className="mt-1 max-h-32 overflow-auto rounded p-2 text-xs"
                style={{
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-text-primary)",
                }}
              >
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          ) : null}
          {result && status === "complete" ? (
            <div>
              <p className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>
                Result:
              </p>
              <pre
                className="mt-1 max-h-32 overflow-auto rounded p-2 text-xs"
                style={{
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-text-primary)",
                }}
              >
                {typeof result === "string" ? result : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function AgentStreaming() {
  useCopilotAction({
    name: "*",
    render: ({ name, args, status, result }) => {
      return <ToolCallCard name={name} args={args || {}} status={status} result={result} />;
    },
  });

  return null;
}
