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
      <section
        className="rounded-xl border p-5 shadow-lg"
        style={{
          borderColor: "var(--color-border)",
          backgroundColor: "var(--color-surface)"
        }}
      >
        <h2 className="text-lg font-bold" style={{ color: "var(--color-text-primary)" }}>
          Files
        </h2>
        <p className="mt-3 text-sm" style={{ color: "var(--color-text-secondary)" }}>
          Generated files, plots, and reports will appear here.
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
        Files
      </h2>
      <div className="mt-4 grid gap-4">
        {entries.map(([name, content]) => {
          if (typeof content !== "string") {
            return (
              <details
                key={name}
                className="rounded-lg border p-3 text-sm"
                style={{
                  borderColor: "var(--color-border)",
                  backgroundColor: "var(--color-background)",
                  color: "var(--color-text-primary)"
                }}
              >
                <summary className="cursor-pointer font-medium">{name}</summary>
                <pre
                  className="mt-2 overflow-auto text-xs"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {JSON.stringify(content, null, 2)}
                </pre>
              </details>
            );
          }

          if (isImage(name)) {
            const src = resolveImageSource(name, content);
            return (
              <figure
                key={name}
                className="rounded-lg border p-3"
                style={{
                  borderColor: "var(--color-border)",
                  backgroundColor: "var(--color-background)"
                }}
              >
                <Image
                  src={src}
                  alt={name}
                  width={800}
                  height={600}
                  className="h-auto w-full rounded-lg"
                  unoptimized
                />
                <figcaption
                  className="mt-2 text-xs"
                  style={{ color: "var(--color-text-tertiary)" }}
                >
                  {name}
                </figcaption>
              </figure>
            );
          }

          if (isMarkdown(name)) {
            return (
              <article
                key={name}
                className="rounded-lg border p-4 text-sm"
                style={{
                  borderColor: "var(--color-border)",
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-text-primary)"
                }}
              >
                <header
                  className="mb-3 text-sm font-semibold"
                  style={{ color: "var(--color-text-primary)" }}
                >
                  {name}
                </header>
                <ReactMarkdown remarkPlugins={[remarkGfm]} className="markdown-body">
                  {content}
                </ReactMarkdown>
              </article>
            );
          }

          return (
            <details
              key={name}
              className="rounded-lg border p-3 text-sm"
              style={{
                borderColor: "var(--color-border)",
                backgroundColor: "var(--color-background)",
                color: "var(--color-text-primary)"
              }}
            >
              <summary className="cursor-pointer font-medium">{name}</summary>
              <pre
                className="mt-2 overflow-auto text-xs"
                style={{ color: "var(--color-text-secondary)" }}
              >
                {content}
              </pre>
            </details>
          );
        })}
      </div>
    </section>
  );
}
