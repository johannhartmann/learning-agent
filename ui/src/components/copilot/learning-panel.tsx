"use client";

import { useMemo } from "react";
import { useCoAgent } from "@copilotkit/react-core";

import type { ExecutionData, Memory, Pattern } from "@/app/types/types";
import { LEARNING_AGENT_KEY, type LearningAgentState } from "./types";

function MemoryCard({ memory }: { memory: Memory }) {
  return (
    <article
      className="rounded-lg border p-3 text-sm"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-background)",
        color: "var(--color-text-primary)"
      }}
    >
      <header className="mb-2 flex items-center justify-between gap-2">
        <span className="font-semibold" style={{ color: "var(--color-primary)" }}>{memory.task}</span>
        <span className="text-xs uppercase tracking-wide" style={{ color: "var(--color-text-tertiary)" }}>{memory.outcome}</span>
      </header>
      <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{memory.narrative}</p>
      {memory.reflection ? (
        <p className="mt-2 text-xs" style={{ color: "var(--color-text-tertiary)" }}>
          <span className="font-medium" style={{ color: "var(--color-text-secondary)" }}>Reflection:</span> {memory.reflection}
        </p>
      ) : null}
    </article>
  );
}

function PatternCard({ pattern }: { pattern: Pattern }) {
  return (
    <article
      className="rounded-lg border p-3 text-sm"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-background)",
        color: "var(--color-text-primary)"
      }}
    >
      <header className="mb-1 flex items-center justify-between gap-2">
        <span className="font-semibold" style={{ color: "var(--color-warning)" }}>Pattern #{pattern.id}</span>
        <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>Confidence {Math.round(pattern.confidence * 100)}%</span>
      </header>
      <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{pattern.description}</p>
    </article>
  );
}

function QueueCard({ item }: { item: ExecutionData }) {
  return (
    <article
      className="rounded-lg border p-3 text-sm"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-background)",
        color: "var(--color-text-primary)"
      }}
    >
      <header className="mb-1 flex items-center justify-between gap-2">
        <span className="font-semibold" style={{ color: "var(--color-text-primary)" }}>{item.task}</span>
        <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>{item.outcome}</span>
      </header>
      {item.description ? <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{item.description}</p> : null}
      {item.error ? (
        <p className="mt-1 text-xs" style={{ color: "var(--color-error)" }}>{item.error}</p>
      ) : null}
    </article>
  );
}

export function LearningPanel() {
  const { state } = useCoAgent<LearningAgentState>({ name: LEARNING_AGENT_KEY });

  const memories = useMemo(() => state?.memories ?? [], [state?.memories]);
  const patterns = useMemo(() => state?.patterns ?? [], [state?.patterns]);
  const learningQueue = useMemo(() => state?.learning_queue ?? [], [state?.learning_queue]);

  return (
    <div className="grid gap-6">
      <section>
        <h2 className="text-base font-semibold" style={{ color: "var(--color-text-primary)" }}>Memories</h2>
        <div className="mt-3 grid gap-3">
          {memories.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--color-text-tertiary)" }}>Learning memories will appear here once the agent reflects.</p>
          ) : (
            memories.map((memory) => <MemoryCard key={memory.id} memory={memory} />)
          )}
        </div>
      </section>
      <section>
        <h2 className="text-base font-semibold" style={{ color: "var(--color-text-primary)" }}>Patterns</h2>
        <div className="mt-3 grid gap-3">
          {patterns.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--color-text-tertiary)" }}>The agent will list reusable tactics and anti-patterns as it works.</p>
          ) : (
            patterns.map((pattern) => <PatternCard key={pattern.id} pattern={pattern} />)
          )}
        </div>
      </section>
      <section>
        <h2 className="text-base font-semibold" style={{ color: "var(--color-text-primary)" }}>Learning Queue</h2>
        <div className="mt-3 grid gap-3">
          {learningQueue.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--color-text-tertiary)" }}>Pending evaluations appear here during narrative learning.</p>
          ) : (
            learningQueue.map((item, index) => <QueueCard key={`${item.task}-${index}`} item={item} />)
          )}
        </div>
      </section>
    </div>
  );
}
