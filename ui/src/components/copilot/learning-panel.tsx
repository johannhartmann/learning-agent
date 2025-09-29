"use client";

import { useMemo } from "react";
import { useCoAgent } from "@copilotkit/react-core";

import type { Memory } from "@/app/types/types";
import { useLearningPolling } from "@/hooks/useLearningPolling";
import { LEARNING_AGENT_KEY, type LearningAgentState } from "./types";

function MemoryCard({ memory }: { memory: Memory }) {
  return (
    <article
      className="rounded-lg border p-4 text-sm space-y-3"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-background)",
        color: "var(--color-text-primary)"
      }}
    >
      <header className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <h3 className="font-semibold text-base mb-1" style={{ color: "var(--color-primary)" }}>
            {memory.task}
          </h3>
          {memory.confidence_score && (
            <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
              Confidence: {(memory.confidence_score * 100).toFixed(0)}%
            </span>
          )}
        </div>
        <span className="text-xs uppercase tracking-wide px-2 py-1 rounded"
          style={{
            backgroundColor: memory.outcome === "success" ? "var(--color-success-bg)" : "var(--color-error-bg)",
            color: memory.outcome === "success" ? "var(--color-success)" : "var(--color-error)"
          }}>
          {memory.outcome}
        </span>
      </header>

      {/* Display full learning content */}
      {memory.tactical_learning && (
        <div>
          <h4 className="font-medium text-sm mb-1" style={{ color: "var(--color-text-secondary)" }}>
            Tactical Learning
          </h4>
          <p className="text-sm" style={{ color: "var(--color-text-primary)" }}>
            {memory.tactical_learning}
          </p>
        </div>
      )}

      {memory.strategic_learning && (
        <div>
          <h4 className="font-medium text-sm mb-1" style={{ color: "var(--color-text-secondary)" }}>
            Strategic Learning
          </h4>
          <p className="text-sm" style={{ color: "var(--color-text-primary)" }}>
            {memory.strategic_learning}
          </p>
        </div>
      )}

      {memory.meta_learning && (
        <div>
          <h4 className="font-medium text-sm mb-1" style={{ color: "var(--color-text-secondary)" }}>
            Meta Learning
          </h4>
          <p className="text-sm" style={{ color: "var(--color-text-primary)" }}>
            {memory.meta_learning}
          </p>
        </div>
      )}

      {memory.anti_patterns && memory.anti_patterns.description && (
        <div>
          <h4 className="font-medium text-sm mb-1" style={{ color: "var(--color-warning)" }}>
            Anti-patterns Detected
          </h4>
          <p className="text-sm" style={{ color: "var(--color-text-primary)" }}>
            {memory.anti_patterns.description}
          </p>
        </div>
      )}

      {memory.reflection && (
        <div className="pt-2 border-t" style={{ borderColor: "var(--color-border)" }}>
          <p className="text-xs italic" style={{ color: "var(--color-text-tertiary)" }}>
            {memory.reflection}
          </p>
        </div>
      )}

      <footer className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
        {new Date(memory.timestamp).toLocaleString()}
      </footer>
    </article>
  );
}

export function LearningPanel() {
  const { state } = useCoAgent<LearningAgentState>({ name: LEARNING_AGENT_KEY });
  const { learnings, isLoading, error } = useLearningPolling();

  const memories = useMemo(() => state?.memories ?? [], [state?.memories]);

  // Get only the 5 most recent learnings (sorted by timestamp, newest first)
  const displayedMemories = useMemo(() => {
    const allMemories = learnings.length > 0 ? learnings : memories;
    return allMemories
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 5);
  }, [learnings, memories]);

  return (
    <div className="grid gap-4">
      <section
        className="rounded-xl border p-5 shadow-lg"
        style={{
          borderColor: "var(--color-border)",
          backgroundColor: "var(--color-surface)"
        }}
      >
        <h2 className="text-lg font-bold" style={{ color: "var(--color-text-primary)" }}>Memories</h2>
        {isLoading ? (
          <p className="text-sm" style={{ color: "var(--color-text-tertiary)" }}>Syncing background learnings…</p>
        ) : null}
        {error ? (
          <p className="text-sm" style={{ color: "var(--color-error)" }}>{error}</p>
        ) : null}
        <div className="mt-4 grid gap-3">
          {displayedMemories.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>Learning memories will appear here once the agent reflects.</p>
          ) : (
            displayedMemories.map((memory) => <MemoryCard key={memory.id} memory={memory} />)
          )}
        </div>
      </section>
    </div>
  );
}
