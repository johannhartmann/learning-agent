"use client";

import { useMemo } from "react";
import { useCoAgent } from "@copilotkit/react-core";

import type { TodoItem } from "@/app/types/types";
import { LEARNING_AGENT_KEY, type LearningAgentState } from "./types";

function formatTodoEntry(entry: TodoItem | string) {
  if (typeof entry === "string") {
    return { content: entry, status: "pending" as const };
  }
  return entry;
}

export function TaskList() {
  const { state } = useCoAgent<LearningAgentState>({ name: LEARNING_AGENT_KEY });

  const todos = useMemo(() => {
    const rawTodos = state?.todos ?? [];
    return (rawTodos ?? []).map(formatTodoEntry);
  }, [state?.todos]);

  if (!todos.length) {
    return (
      <section
        className="rounded-xl border p-5 shadow-lg"
        style={{
          borderColor: "var(--color-border)",
          backgroundColor: "var(--color-surface)"
        }}
      >
        <h2 className="text-lg font-bold" style={{ color: "var(--color-text-primary)" }}>
          Task List
        </h2>
        <p className="mt-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>
          No tasks yet. Ask the agent to plan a workflow.
        </p>
      </section>
    );
  }

  return (
    <section
      className="rounded-xl border p-5 shadow-lg"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-surface)"
      }}
    >
      <h2 className="text-lg font-bold" style={{ color: "var(--color-text-primary)" }}>
        Task List
      </h2>
      <ol className="mt-4 space-y-3 text-sm">
        {todos.map((todo, index) => (
          <li key={`${todo.content}-${index}`} className="flex items-start gap-3">
            <span
              className="mt-1.5 inline-flex h-2 w-2 flex-none rounded-full"
              style={{ backgroundColor: "var(--color-primary)" }}
              aria-hidden
            />
            <div>
              <p className="font-medium leading-relaxed" style={{ color: "var(--color-text-primary)" }}>
                {todo.content}
              </p>
              {todo.status && todo.status !== "pending" ? (
                <p className="mt-1 text-xs" style={{ color: "var(--color-text-tertiary)" }}>
                  {todo.status.replace("_", " ")}
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
