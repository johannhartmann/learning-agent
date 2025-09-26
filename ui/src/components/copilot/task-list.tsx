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
      <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-neutral-900">Task List</h2>
        <p className="mt-2 text-sm text-neutral-500">No tasks yet. Ask the agent to plan a workflow.</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-neutral-900">Task List</h2>
      <ol className="mt-3 space-y-2 text-sm text-neutral-900">
        {todos.map((todo, index) => (
          <li key={`${todo.content}-${index}`} className="flex items-start gap-2">
            <span className="mt-1 inline-flex h-2 w-2 flex-none rounded-full bg-indigo-500" aria-hidden />
            <div>
              <p className="font-medium">{todo.content}</p>
              {todo.status && todo.status !== "pending" ? (
                <p className="text-xs text-neutral-500">{todo.status.replace("_", " ")}</p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
