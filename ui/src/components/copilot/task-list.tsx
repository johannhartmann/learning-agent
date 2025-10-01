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

  const subagentTodos = useMemo(() => {
    const rawSubagentTodos = state?.subagent_todos ?? {};
    return Object.entries(rawSubagentTodos).map(([contextId, todoList]) => ({
      contextId,
      todos: todoList.map(formatTodoEntry),
    }));
  }, [state?.subagent_todos]);

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
          Todo List
        </h2>
        <p className="mt-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>
          No todos yet. Ask the agent to plan a workflow.
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
        Todo List
      </h2>
      <ol className="mt-4 space-y-3 text-sm">
        {todos.map((todo, index) => {
          const key = todo.id || `${todo.content}-${index}`;
          // Find subagent todos for this parent task (if any)
          const relatedSubagentTodos = subagentTodos.filter(
            (subagent) => todo.content && subagent.contextId.includes(todo.content.substring(0, 20))
          );

          return (
            <li key={key}>
              <div className="flex items-start gap-3">
                <span
                  className="mt-1.5 inline-flex h-2 w-2 flex-none rounded-full"
                  style={{ backgroundColor: "var(--color-primary)" }}
                  aria-hidden
                />
                <div className="flex-1">
                  <p className="font-medium leading-relaxed" style={{ color: "var(--color-text-primary)" }}>
                    {todo.content}
                  </p>
                  {todo.status && todo.status !== "pending" ? (
                    <p className="mt-1 text-xs" style={{ color: "var(--color-text-tertiary)" }}>
                      {todo.status.replace("_", " ")}
                    </p>
                  ) : null}

                  {/* Render subagent todos if any */}
                  {relatedSubagentTodos.length > 0 && (
                    <ol className="mt-2 ml-4 space-y-2 border-l-2" style={{ borderColor: "var(--color-border)" }}>
                      {relatedSubagentTodos.flatMap((subagent) =>
                        subagent.todos.map((subTodo, subIndex) => (
                          <li key={`${subagent.contextId}-${subIndex}`} className="flex items-start gap-2 pl-3">
                            <span
                              className="mt-1.5 inline-flex h-1.5 w-1.5 flex-none rounded-full"
                              style={{ backgroundColor: "var(--color-text-tertiary)" }}
                              aria-hidden
                            />
                            <div className="flex-1">
                              <p className="text-xs leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                                {subTodo.content}
                              </p>
                              {subTodo.status && subTodo.status !== "pending" ? (
                                <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-tertiary)" }}>
                                  {subTodo.status.replace("_", " ")}
                                </p>
                              ) : null}
                            </div>
                          </li>
                        ))
                      )}
                    </ol>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
