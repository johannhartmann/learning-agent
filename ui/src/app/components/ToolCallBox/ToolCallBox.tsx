"use client";

import React, { useState, useMemo, useCallback } from "react";
import {
  ChevronDown,
  ChevronRight,
  Terminal,
  CheckCircle,
  AlertCircle,
  Loader,
  FileImage,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { MarkdownContent } from "../MarkdownContent/MarkdownContent";
import { FileViewer } from "../FileViewer/FileViewer";
import styles from "./ToolCallBox.module.scss";
import Image from "next/image";
import { ToolCall } from "../../types/types";

interface ToolCallBoxProps {
  toolCall: ToolCall;
  threadId: string | null;
}

export const ToolCallBox = React.memo<ToolCallBoxProps>(({ toolCall, threadId }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const { name, args, result, status, files } = useMemo(() => {
    const toolName = toolCall.name || "Unknown Tool";
    const toolArgs = toolCall.args || "{}";
    let parsedArgs = {};
    try {
      parsedArgs =
        typeof toolArgs === "string" ? JSON.parse(toolArgs) : toolArgs;
    } catch {
      parsedArgs = { raw: toolArgs };
    }
    const toolResult = toolCall.result || null;
    const toolStatus = toolCall.status || "completed";

    // Extract files from result if this is a python_sandbox tool
    let extractedFiles: string[] = [];
    if (toolName === "python_sandbox" && toolResult) {
      // Look for "Saved plot to" pattern in the output
      const savedPlotMatches = toolResult.match(/Saved plot to (\/[^\s]+)/g);
      if (savedPlotMatches) {
        extractedFiles = savedPlotMatches.map((match: string) => {
          const pathMatch = match.match(/Saved plot to (\/[^\s]+)/);
          return pathMatch ? pathMatch[1] : "";
        }).filter(path => path !== "");
      }
      
      // Also check for the Generated files pattern in the formatted result
      const generatedFilesMatch = toolResult.match(/Generated \d+ file\(s\):/);
      if (generatedFilesMatch) {
        // Extract file paths that appear as list items after "Generated X file(s):"
        const afterGenerated = toolResult.substring(toolResult.indexOf(generatedFilesMatch[0]) + generatedFilesMatch[0].length);
        const filePathMatches = afterGenerated.match(/\/[^\s\n]+\.(png|jpg|jpeg|gif|svg)/gi);
        if (filePathMatches) {
          extractedFiles.push(...filePathMatches);
        }
      }
      
      // Remove duplicates
      extractedFiles = [...new Set(extractedFiles)];
    }

    return {
      name: toolName,
      args: parsedArgs,
      result: toolResult,
      status: toolStatus,
      files: extractedFiles,
    };
  }, [toolCall]);

  const statusIcon = useMemo(() => {
    switch (status) {
      case "completed":
        return <CheckCircle className={styles.statusCompleted} />;
      case "error":
        return <AlertCircle className={styles.statusError} />;
      case "pending":
        return <Loader className={styles.statusRunning} />;
      default:
        return <Terminal className={styles.statusDefault} />;
    }
  }, [status]);

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const hasContent = result || Object.keys(args).length > 0 || files.length > 0;

  return (
    <div className={styles.container}>
      <Button
        variant="ghost"
        size="sm"
        onClick={toggleExpanded}
        className={styles.header}
        disabled={!hasContent}
      >
        <div className={styles.headerLeft}>
          {hasContent && isExpanded ? (
            <ChevronDown size={14} />
          ) : (
            <ChevronRight size={14} />
          )}
          {statusIcon}
          <span className={styles.toolName}>{name}</span>
          {files.length > 0 && (
            <span className={styles.fileCount}>
              <FileImage size={12} />
              {files.length}
            </span>
          )}
        </div>
      </Button>

      {isExpanded && hasContent && (
        <div className={styles.content}>
          {Object.keys(args).length > 0 && (
            <div className={styles.section}>
              <h4 className={styles.sectionTitle}>Arguments</h4>
              <pre className={styles.codeBlock}>
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}
          
          {files.length > 0 && (
            <div className={styles.section}>
              <h4 className={styles.sectionTitle}>Generated Files</h4>
              <div className={styles.fileList}>
                {files.map((filePath) => {
                  const isImage = filePath.toLowerCase().endsWith('.png') || 
                                  filePath.toLowerCase().endsWith('.jpg') || 
                                  filePath.toLowerCase().endsWith('.jpeg') || 
                                  filePath.toLowerCase().endsWith('.gif') || 
                                  filePath.toLowerCase().endsWith('.svg');
                  
                  if (isImage) {
                    // Display images inline directly
                    return (
                      <div key={filePath} className={styles.fileItem}>
                        <div className={styles.imageContainer}>
                          <p className={styles.fileName}>{filePath.split("/").pop()}</p>
                          <Image 
                            src={`http://localhost:8001/api/files${filePath}${threadId ? `?thread_id=${threadId}` : ''}`}
                            alt={filePath.split("/").pop() || "Generated file"}
                            className={styles.inlineImage}
                            style={{ maxWidth: '100%', height: 'auto' }}
                            width={800}
                            height={600}
                            unoptimized
                          />
                        </div>
                      </div>
                    );
                  }
                  
                  // For non-image files, keep the button
                  return (
                    <div key={filePath} className={styles.fileItem}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedFile(filePath)}
                        className={styles.fileButton}
                      >
                        <FileImage size={14} />
                        <span>{filePath.split("/").pop()}</span>
                      </Button>
                    </div>
                  );
                })}
              </div>
              {selectedFile && (
                <div className={styles.filePreview}>
                  <FileViewer
                    filePath={selectedFile}
                    onClose={() => setSelectedFile(null)}
                  />
                </div>
              )}
            </div>
          )}
          
          {result && (
            <div className={styles.section}>
              <h4 className={styles.sectionTitle}>Result</h4>
              {name === "python_sandbox" ? (
                <MarkdownContent content={result} threadId={threadId} />
              ) : (
                <pre className={styles.codeBlock}>
                  {typeof result === "string"
                    ? result
                    : JSON.stringify(result, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

ToolCallBox.displayName = "ToolCallBox";
