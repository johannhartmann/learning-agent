"use client";

import { useMemo, useState } from "react";
import { CopilotChat } from "@copilotkit/react-ui";

import { ArtifactsGallery } from "@/components/copilot/artifacts-gallery";
import { LearningPanel } from "@/components/copilot/learning-panel";
import { TaskList } from "@/components/copilot/task-list";

const PANELS = {
  tasks: {
    label: "Tasks",
    render: () => <TaskList />,
  },
  learning: {
    label: "Learning",
    render: () => <LearningPanel />,
  },
  artifacts: {
    label: "Artifacts",
    render: () => <ArtifactsGallery />,
  },
} satisfies Record<string, { label: string; render: () => JSX.Element }>;

type PanelKey = keyof typeof PANELS;

export default function HomePage() {
  const [activePanel, setActivePanel] = useState<PanelKey>("tasks");

  const PanelComponent = useMemo(() => PANELS[activePanel].render, [activePanel]);

  return (
    <main className="flex min-h-screen flex-col" style={{ backgroundColor: "var(--color-background)" }}>
      <header
        className="border-b backdrop-blur-sm"
        style={{
          borderColor: "var(--color-border)",
          backgroundColor: "var(--color-surface)"
        }}
      >
        <div className="flex w-full flex-col gap-2 px-8 py-6">
          <h1 className="text-2xl font-bold" style={{ color: "var(--color-text-primary)" }}>
            Learning Agent Workspace
          </h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            Chat with the agent, review its plans, and track what it learns from each run.
          </p>
        </div>
      </header>
      <section className="flex w-full flex-1 flex-col gap-6 px-8 py-8 lg:flex-row">
        <div
          className="flex min-h-[70vh] flex-1 flex-col overflow-hidden rounded-2xl border shadow-2xl"
          style={{
            borderColor: "var(--color-border)",
            backgroundColor: "var(--color-surface)"
          }}
        >
          <CopilotChat
            className="flex h-full flex-col"
            instructions="You are the Learning Agent. Maintain the todo list in state.todos, capture artifacts in state.files, and update memories, patterns, and learning_queue as you reflect. When you generate code, images, or other artifacts, include them in your response using markdown code blocks or image syntax."
            labels={{ title: "Learning Agent", initial: "What should we tackle?" }}
            showResponseButton={true}
          />
        </div>
        <aside className="flex w-full flex-col gap-4 lg:w-80 lg:flex-shrink-0">
          <nav
            className="rounded-xl border p-2 shadow-lg"
            style={{
              borderColor: "var(--color-border)",
              backgroundColor: "var(--color-surface)"
            }}
          >
            <div className="grid grid-cols-3 gap-2">
              {(Object.keys(PANELS) as PanelKey[]).map((key) => {
                const panel = PANELS[key];
                const isActive = key === activePanel;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActivePanel(key)}
                    className={`rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
                      isActive
                        ? "shadow-md"
                        : "hover:shadow-sm"
                    }`}
                    style={{
                      backgroundColor: isActive ? "var(--color-primary)" : "var(--color-border)",
                      color: isActive ? "var(--primary-foreground)" : "var(--color-text-secondary)"
                    }}
                  >
                    {panel.label}
                  </button>
                );
              })}
            </div>
          </nav>
          <div className="flex-1 overflow-auto">
            <PanelComponent />
          </div>
        </aside>
      </section>
    </main>
  );
}
