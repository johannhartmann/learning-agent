"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CheckCircle, XCircle, Timer } from "lucide-react";
import type { ExecutionData } from "../../types/types";
import styles from "./LearningQueue.module.scss";

interface LearningQueueProps {
  queue: ExecutionData[];
  onItemClick?: (item: ExecutionData) => void;
}

export const LearningQueue = React.memo<LearningQueueProps>(
  ({ queue, onItemClick }) => {
    const getOutcomeIcon = (outcome: ExecutionData["outcome"]) => {
      return outcome === "success" ? (
        <CheckCircle size={16} className={styles.successIcon} />
      ) : (
        <XCircle size={16} className={styles.failureIcon} />
      );
    };

    const formatDuration = (duration: number) => {
      if (duration < 1000) {
        return `${Math.round(duration)}ms`;
      } else if (duration < 60000) {
        return `${(duration / 1000).toFixed(1)}s`;
      } else {
        return `${Math.round(duration / 60000)}m`;
      }
    };

    if (queue.length === 0) {
      return (
        <div className={styles.emptyState}>
          <p>No pending learning items. New experiences will appear here for processing.</p>
        </div>
      );
    }

    return (
      <ScrollArea className={styles.scrollArea}>
        <div className={styles.queueList}>
          <div className={styles.queueHeader}>
            <h3>Pending Learning</h3>
            <Badge variant="secondary">
              {queue.length} item{queue.length !== 1 ? "s" : ""}
            </Badge>
          </div>
          {queue.map((item, index) => (
            <Card
              key={index}
              className={styles.queueCard}
              onClick={() => onItemClick?.(item)}
            >
              <CardHeader className={styles.itemHeader}>
                <div className={styles.headerRow}>
                  <CardTitle className={styles.itemTask}>
                    {item.task}
                  </CardTitle>
                  {getOutcomeIcon(item.outcome)}
                </div>
                <div className={styles.metadata}>
                  <div className={styles.duration}>
                    <Timer size={12} />
                    <span>{formatDuration(item.duration)}</span>
                  </div>
                  <Badge
                    variant={item.outcome === "success" ? "default" : "destructive"}
                    className={styles.outcomeBadge}
                  >
                    {item.outcome}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className={styles.itemContent}>
                <div className={styles.description}>
                  <p>{item.description}</p>
                </div>
                {item.error && (
                  <div className={styles.error}>
                    <span className={styles.errorLabel}>Error:</span>
                    <p>{item.error}</p>
                  </div>
                )}
                {item.context && (
                  <div className={styles.context}>
                    <span className={styles.contextLabel}>Context:</span>
                    <p>{item.context}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>
    );
  }
);

LearningQueue.displayName = "LearningQueue";
