"use client";

import { useMemo } from "react";
import { useCoAgent } from "@copilotkit/react-core";

import type { ExecutionData, Memory, Pattern } from "@/app/types/types";
import { LEARNING_AGENT_KEY, type LearningAgentState } from "./types";

function MemoryCard({ memory }: { memory: Memory }) {
  return (
    <article className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-3 text-sm text-neutral-900">
      <header className="mb-2 flex items-center justify-between gap-2">
        <span className="font-semibold text-indigo-700">{memory.task}</span>
        <span className="text-xs uppercase tracking-wide text-neutral-500">{memory.outcome}</span>
      </header>
      <p className="text-sm text-neutral-800">{memory.narrative}</p>
      {memory.reflection ? (
        <p className="mt-2 text-xs text-neutral-600">
          <span className="font-medium text-neutral-700">Reflection:</span> {memory.reflection}
        </p>
      ) : null}
    </article>
  );
}

function PatternCard({ pattern }: { pattern: Pattern }) {
  return (
    <article className="rounded-lg border border-amber-100 bg-amber-50/60 p-3 text-sm text-neutral-900">
      <header className="mb-1 flex items-center justify-between gap-2">
        <span className="font-semibold text-amber-700">Pattern #{pattern.id}</span>
        <span className="text-xs text-neutral-500">Confidence {Math.round(pattern.confidence * 100)}%</span>
      </header>
      <p className="text-sm text-neutral-800">{pattern.description}</p>
    </article>
  );
}

function QueueCard({ item }: { item: ExecutionData }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-neutral-900">
      <header className="mb-1 flex items-center justify-between gap-2">
        <span className="font-semibold text-slate-700">{item.task}</span>
        <span className="text-xs text-neutral-500">{item.outcome}</span>
      </header>
      {item.description ? <p className="text-sm text-neutral-800">{item.description}</p> : null}
      {item.error ? (
        <p className="mt-1 text-xs text-red-600">{item.error}</p>
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
        <h2 className="text-base font-semibold text-neutral-900">Memories</h2>
        <div className="mt-3 grid gap-3">
          {memories.length === 0 ? (
            <p className="text-sm text-neutral-500">Learning memories will appear here once the agent reflects.</p>
          ) : (
            memories.map((memory) => <MemoryCard key={memory.id} memory={memory} />)
          )}
        </div>
      </section>
      <section>
        <h2 className="text-base font-semibold text-neutral-900">Patterns</h2>
        <div className="mt-3 grid gap-3">
          {patterns.length === 0 ? (
            <p className="text-sm text-neutral-500">The agent will list reusable tactics and anti-patterns as it works.</p>
          ) : (
            patterns.map((pattern) => <PatternCard key={pattern.id} pattern={pattern} />)
          )}
        </div>
      </section>
      <section>
        <h2 className="text-base font-semibold text-neutral-900">Learning Queue</h2>
        <div className="mt-3 grid gap-3">
          {learningQueue.length === 0 ? (
            <p className="text-sm text-neutral-500">Pending evaluations appear here during narrative learning.</p>
          ) : (
            learningQueue.map((item, index) => <QueueCard key={`${item.task}-${index}`} item={item} />)
          )}
        </div>
      </section>
    </div>
  );
}
