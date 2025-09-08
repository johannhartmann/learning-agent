"use client";

import React from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import type { PrismTheme } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import styles from "./MarkdownContent.module.scss";
import { getInternalApiBase } from "@/lib/environment/api";

interface MarkdownContentProps {
  content: string;
  className?: string;
  threadId?: string | null;
}

export const MarkdownContent = React.memo<MarkdownContentProps>(
  ({ content, className = "", threadId }) => {
    return (
      <div className={`${styles.markdown} ${className}`}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ inline, className, children, ...props }: { inline?: boolean; className?: string; children?: React.ReactNode } & Record<string, unknown>) {
              const match = /language-(\w+)/.exec(className || "");
              return !inline && match ? (
                <SyntaxHighlighter
                  style={oneDark as PrismTheme}
                  language={match[1]}
                  PreTag="div"
                  className={styles.codeBlock}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              ) : (
                <code className={styles.inlineCode} {...props}>
                  {children}
                </code>
              );
            },
            pre({ children }: { children?: React.ReactNode }) {
              return <div className={styles.preWrapper}>{children}</div>;
            },
            img({ src, alt }: { src?: string; alt?: string }) {
              // Skip images with missing/empty src from LLM outputs
              if (!src || src.trim() === "") {
                return null;
              }
              // Normalize various image references from sandbox/tool output
              const toApiUrl = (filePath: string) => {
                const base = getInternalApiBase();
                const path = filePath.startsWith("/") ? filePath : `/${filePath}`;
                const q = threadId ? `?thread_id=${threadId}` : "";
                return `${base}/files${path}${q}`;
              };

              let actualSrc: string | undefined = src;

              if (src) {
                if (src.startsWith("sandbox-file:")) {
                  // sandbox-file:/tmp/foo.png -> /api/files/tmp/foo.png
                  actualSrc = toApiUrl(src.replace("sandbox-file:", ""));
                } else if (src.startsWith("attachment://")) {
                  // attachment://foo.png -> /api/files/tmp/foo.png (common pattern)
                  const name = src.replace("attachment://", "");
                  actualSrc = toApiUrl(`tmp/${name}`);
                } else if (src.startsWith("data:image")) {
                  // Base64-encoded image
                  actualSrc = src;
                } else if (src.startsWith("/")) {
                  // Absolute path from sandbox (e.g., /tmp/foo.png)
                  actualSrc = toApiUrl(src);
                } else if (!/^https?:\/\//i.test(src)) {
                  // Relative filename from sandbox output (e.g., foo.png or tmp/foo.png)
                  if (src.trim() === "") return null;
                  actualSrc = toApiUrl(src);
                }
              }

              if (!actualSrc) {
                return null;
              }
              return (
                <div className={styles.imageWrapper}>
                  <Image
                    src={actualSrc}
                    alt={alt || "Image"}
                    className={styles.figure}
                    style={{ maxWidth: "100%", height: "auto" }}
                    width={800}
                    height={600}
                    unoptimized
                  />
                  {alt && <p className={styles.imageCaption}>{alt}</p>}
                </div>
              );
            },
            a({ href, children }: { href?: string; children?: React.ReactNode }) {
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.link}
                >
                  {children}
                </a>
              );
            },
            blockquote({ children }: { children?: React.ReactNode }) {
              return (
                <blockquote className={styles.blockquote}>
                  {children}
                </blockquote>
              );
            },
            ul({ children }: { children?: React.ReactNode }) {
              return <ul className={styles.list}>{children}</ul>;
            },
            ol({ children }: { children?: React.ReactNode }) {
              return <ol className={styles.orderedList}>{children}</ol>;
            },
            table({ children }: { children?: React.ReactNode }) {
              return (
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>{children}</table>
                </div>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  },
);

MarkdownContent.displayName = "MarkdownContent";
