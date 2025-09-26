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
    <main className="flex min-h-screen flex-col bg-neutral-100">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-1 px-6 py-5">
          <h1 className="text-xl font-semibold text-neutral-900">Learning Agent Workspace</h1>
          <p className="text-sm text-neutral-500">
            Chat with the agent, review its plans, and track what it learns from each run.
          </p>
        </div>
      </header>
      <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-6 py-6 lg:flex-row">
        <div className="flex min-h-[60vh] flex-1 flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
          <CopilotChat
            className="flex h-full flex-col"
            instructions="You are the Learning Agent. Maintain the todo list in state.todos, capture artifacts in state.files, and update memories, patterns, and learning_queue as you reflect."
            labels={{ title: "Learning Agent", initial: "What should we tackle?" }}
          />
        </div>
        <aside className="flex w-full max-w-sm flex-col gap-4">
          <nav className="rounded-xl border border-neutral-200 bg-white p-2 shadow-sm">
            <div className="grid grid-cols-3 gap-2">
              {(Object.keys(PANELS) as PanelKey[]).map((key) => {
                const panel = PANELS[key];
                const isActive = key === activePanel;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActivePanel(key)}
                    className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-indigo-600 text-white shadow"
                        : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                    }`}
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
