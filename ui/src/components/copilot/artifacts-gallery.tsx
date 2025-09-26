"use client";

import { useMemo } from "react";
import Image from "next/image";
import { useCoAgent } from "@copilotkit/react-core";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { LEARNING_AGENT_KEY, type LearningAgentState } from "./types";

function resolveImageSource(name: string, content: string) {
  if (content.startsWith("http://") || content.startsWith("https://")) {
    return content;
  }

  if (content.startsWith("data:")) {
    return content;
  }

  const ext = name.toLowerCase().split(".").pop();
  const mime = ext === "jpg" || ext === "jpeg" ? "jpeg" : ext;
  return `data:image/${mime};base64,${content}`;
}

function isImage(name: string) {
  const lower = name.toLowerCase();
  return ["png", "jpg", "jpeg", "gif", "svg", "webp"].some((ext) => lower.endsWith(`.${ext}`));
}

function isMarkdown(name: string) {
  return name.toLowerCase().endsWith(".md");
}

export function ArtifactsGallery() {
  const { state } = useCoAgent<LearningAgentState>({ name: LEARNING_AGENT_KEY });

  const entries = useMemo(() => {
    const files = state?.files ?? {};
    return Object.entries(files ?? {});
  }, [state?.files]);

  if (entries.length === 0) {
    return (
      <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-neutral-900">Artifacts</h2>
        <p className="mt-2 text-sm text-neutral-500">Generated plots, notebooks, and markdown reports will appear here.</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-neutral-900">Artifacts</h2>
      <div className="mt-3 grid gap-4">
        {entries.map(([name, content]) => {
          if (typeof content !== "string") {
            return (
              <details key={name} className="rounded border border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-900">
                <summary className="cursor-pointer font-medium">{name}</summary>
                <pre className="mt-2 overflow-auto text-xs text-neutral-700">
                  {JSON.stringify(content, null, 2)}
                </pre>
              </details>
            );
          }

          if (isImage(name)) {
            const src = resolveImageSource(name, content);
            return (
              <figure key={name} className="rounded border border-neutral-200 bg-neutral-50 p-3">
                <Image
                  src={src}
                  alt={name}
                  width={800}
                  height={600}
                  className="h-auto w-full rounded"
                  unoptimized
                />
                <figcaption className="mt-2 text-xs text-neutral-500">{name}</figcaption>
              </figure>
            );
          }

          if (isMarkdown(name)) {
            return (
              <article
                key={name}
                className="rounded border border-neutral-200 bg-white p-3 text-sm text-neutral-900"
              >
                <header className="mb-2 text-sm font-semibold text-neutral-800">{name}</header>
                <ReactMarkdown remarkPlugins={[remarkGfm]} className="markdown-body">
                  {content}
                </ReactMarkdown>
              </article>
            );
          }

          return (
            <details key={name} className="rounded border border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-900">
              <summary className="cursor-pointer font-medium">{name}</summary>
              <pre className="mt-2 overflow-auto text-xs text-neutral-700">{content}</pre>
            </details>
          );
        })}
      </div>
    </section>
  );
}
