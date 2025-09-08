"use client";

import React, { useMemo, useCallback } from "react";
import { FileText, Copy, Download } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { MarkdownContent } from "../MarkdownContent/MarkdownContent";
import type { FileItem } from "../../types/types";
import styles from "./FileViewDialog.module.scss";

interface FileViewDialogProps {
  file: FileItem;
  onClose: () => void;
}

export const FileViewDialog = React.memo<FileViewDialogProps>(
  ({ file, onClose }) => {
    const fileExtension = useMemo(() => {
      return file.path.split(".").pop()?.toLowerCase() || "";
    }, [file.path]);

    const isMarkdown = useMemo(() => {
      return fileExtension === "md" || fileExtension === "markdown";
    }, [fileExtension]);

    const isImage = useMemo(() => {
      return ["png", "jpg", "jpeg", "gif", "svg", "webp", "bmp"].includes(
        fileExtension,
      );
    }, [fileExtension]);

    const mimeType = useMemo(() => {
      const map: Record<string, string> = {
        png: "image/png",
        jpg: "image/jpeg",
        jpeg: "image/jpeg",
        gif: "image/gif",
        svg: "image/svg+xml",
        webp: "image/webp",
        bmp: "image/bmp",
        txt: "text/plain",
        md: "text/markdown",
        markdown: "text/markdown",
        json: "application/json",
        csv: "text/csv",
      };
      return map[fileExtension] || "application/octet-stream";
    }, [fileExtension]);

    const language = useMemo(() => {
      const languageMap: Record<string, string> = {
        js: "javascript",
        jsx: "javascript",
        ts: "typescript",
        tsx: "typescript",
        py: "python",
        rb: "ruby",
        go: "go",
        rs: "rust",
        java: "java",
        cpp: "cpp",
        c: "c",
        cs: "csharp",
        php: "php",
        swift: "swift",
        kt: "kotlin",
        scala: "scala",
        sh: "bash",
        bash: "bash",
        zsh: "bash",
        json: "json",
        xml: "xml",
        html: "html",
        css: "css",
        scss: "scss",
        sass: "sass",
        less: "less",
        sql: "sql",
        yaml: "yaml",
        yml: "yaml",
        toml: "toml",
        ini: "ini",
        dockerfile: "dockerfile",
        makefile: "makefile",
      };
      return languageMap[fileExtension] || "text";
    }, [fileExtension]);

    const handleCopy = useCallback(() => {
      if (!file.content) return;
      // Copy text files; skip binary
      if (!isImage && mimeType.startsWith("text/")) {
        navigator.clipboard.writeText(file.content);
      }
    }, [file.content, isImage, mimeType]);

    const handleDownload = useCallback(() => {
      if (!file.content) return;
      let blob: Blob;
      try {
        if (isImage) {
          // file.content is base64; decode to binary
          const byteString = atob(file.content);
          const bytes = new Uint8Array(byteString.length);
          for (let i = 0; i < byteString.length; i++) {
            bytes[i] = byteString.charCodeAt(i);
          }
          blob = new Blob([bytes], { type: mimeType });
        } else {
          blob = new Blob([file.content], { type: mimeType });
        }
      } catch {
        // Fallback to text
        blob = new Blob([file.content], { type: "application/octet-stream" });
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = file.path.split("/").pop() || "download";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, [file.content, file.path, isImage, mimeType]);

    return (
      <Dialog open={true} onOpenChange={onClose}>
        <DialogContent className={styles.dialog}>
          <DialogTitle className="sr-only">{file.path}</DialogTitle>
          <div className={styles.header}>
            <div className={styles.titleSection}>
              <FileText className={styles.fileIcon} />
              <span className={styles.fileName}>{file.path}</span>
            </div>
            <div className={styles.actions}>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className={styles.actionButton}
              >
                <Copy size={16} />
                Copy
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDownload}
                className={styles.actionButton}
              >
                <Download size={16} />
                Download
              </Button>
            </div>
          </div>

          <ScrollArea className={styles.contentArea}>
            {file.content ? (
              isMarkdown ? (
                <div className={styles.markdownWrapper}>
                  <MarkdownContent content={file.content} />
                </div>
              ) : isImage ? (
                <div className={styles.markdownWrapper}>
                  {/* Render image from base64 content */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`data:${mimeType};base64,${file.content}`}
                    alt={file.path}
                    style={{ maxWidth: "100%", height: "auto" }}
                  />
                </div>
              ) : (
                <SyntaxHighlighter
                  language={language}
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    borderRadius: "0.5rem",
                    fontSize: "0.875rem",
                  }}
                  showLineNumbers
                >
                  {file.content}
                </SyntaxHighlighter>
              )
            ) : (
              <div className={styles.emptyContent}>
                <p>File is empty</p>
              </div>
            )}
          </ScrollArea>
        </DialogContent>
      </Dialog>
    );
  },
);

FileViewDialog.displayName = "FileViewDialog";
