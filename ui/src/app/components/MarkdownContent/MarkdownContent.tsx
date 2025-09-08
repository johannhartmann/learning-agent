"use client";

import React from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import type { PrismTheme } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import styles from "./MarkdownContent.module.scss";

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
              // Handle sandbox-file: protocol for in-memory session files
              if (src && src.startsWith("sandbox-file:")) {
                const filePath = src.replace("sandbox-file:", "");
                const actualSrc = `http://localhost:8001/api/files${filePath}${threadId ? `?thread_id=${threadId}` : ''}`;
                return (
                  <div className={styles.imageWrapper}>
                    <Image 
                      src={actualSrc} 
                      alt={alt || "Figure"} 
                      className={styles.figure}
                      style={{ maxWidth: '100%', height: 'auto' }}
                      width={800}
                      height={600}
                      unoptimized
                    />
                    {alt && <p className={styles.imageCaption}>{alt}</p>}
                  </div>
                );
              }
              // Handle data URI images (base64 encoded matplotlib figures)
              if (src && src.startsWith("data:image")) {
                return (
                  <div className={styles.imageWrapper}>
                    <Image 
                      src={src} 
                      alt={alt || "Figure"} 
                      className={styles.figure}
                      width={800}
                      height={600}
                      unoptimized
                    />
                    {alt && <p className={styles.imageCaption}>{alt}</p>}
                  </div>
                );
              }
              // Default image handling
              return (
                <Image
                  src={src || ""}
                  alt={alt || "Image"}
                  className={styles.image}
                  width={800}
                  height={600}
                  unoptimized
                />
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
