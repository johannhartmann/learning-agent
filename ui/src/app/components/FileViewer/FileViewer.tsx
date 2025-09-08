"use client";

import React, { useState } from "react";
import Image from "next/image";
import { FileImage, Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import styles from "./FileViewer.module.scss";
import { getInternalApiBase } from "@/lib/environment/api";

interface FileViewerProps {
  filePath: string;
  onClose?: () => void;
  inline?: boolean;
}

export const FileViewer = React.memo<FileViewerProps>(
  ({ filePath, onClose, inline = false }) => {
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Construct the API URL for the file via Next proxy
    const base = getInternalApiBase();
    const fileUrl = `${base}/files${filePath.startsWith("/") ? "" : "/"}${filePath}`;
    
    const handleDownload = () => {
      const link = document.createElement("a");
      link.href = fileUrl;
      link.download = filePath.split("/").pop() || "download";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    const handleImageLoad = () => {
      setIsLoading(false);
      setError(null);
    };

    const handleImageError = () => {
      setIsLoading(false);
      setError("Failed to load image");
    };

    if (inline) {
      return (
        <div className={styles.inlineContainer}>
          {isLoading && (
            <div className={styles.loading}>
              <FileImage className={styles.loadingIcon} />
              <span>Loading...</span>
            </div>
          )}
          {error && (
            <div className={styles.error}>
              <FileImage className={styles.errorIcon} />
              <span>{error}</span>
            </div>
          )}
          <Image
            src={fileUrl}
            alt={filePath}
            className={styles.inlineImage}
            onLoad={handleImageLoad}
            onError={handleImageError}
            style={{ display: isLoading || error ? "none" : "block", height: "auto" }}
            width={800}
            height={600}
            unoptimized
          />
        </div>
      );
    }

    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h3 className={styles.title}>{filePath.split("/").pop()}</h3>
          <div className={styles.actions}>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              className={styles.downloadButton}
            >
              <Download size={16} />
            </Button>
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className={styles.closeButton}
              >
                <X size={16} />
              </Button>
            )}
          </div>
        </div>
        <div className={styles.content}>
          {isLoading && (
            <div className={styles.loading}>
              <FileImage className={styles.loadingIcon} />
              <span>Loading image...</span>
            </div>
          )}
          {error && (
            <div className={styles.error}>
              <FileImage className={styles.errorIcon} />
              <span>{error}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setError(null);
                  setIsLoading(true);
                }}
              >
                Retry
              </Button>
            </div>
          )}
          <Image
            src={fileUrl}
            alt={filePath}
            className={styles.image}
            onLoad={handleImageLoad}
            onError={handleImageError}
            style={{ display: isLoading || error ? "none" : "block", height: "auto" }}
            width={1000}
            height={750}
            unoptimized
          />
        </div>
      </div>
    );
  }
);

FileViewer.displayName = "FileViewer";
