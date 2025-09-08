"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TrendingUp, Activity, Calendar } from "lucide-react";
import type { Pattern } from "../../types/types";
import styles from "./PatternsView.module.scss";

interface PatternsViewProps {
  patterns: Pattern[];
  onPatternClick?: (pattern: Pattern) => void;
}

export const PatternsView = React.memo<PatternsViewProps>(
  ({ patterns, onPatternClick }) => {
    const formatDate = (dateStr: string | null) => {
      if (!dateStr) return "Never used";
      const date = new Date(dateStr);
      return date.toLocaleDateString();
    };

    const getConfidenceColor = (confidence: number) => {
      if (confidence >= 0.8) return styles.highConfidence;
      if (confidence >= 0.5) return styles.mediumConfidence;
      return styles.lowConfidence;
    };

    if (patterns.length === 0) {
      return (
        <div className={styles.emptyState}>
          <p>No patterns identified yet. Patterns emerge from repeated experiences.</p>
        </div>
      );
    }

    return (
      <ScrollArea className={styles.scrollArea}>
        <div className={styles.patternsList}>
          {patterns.map((pattern) => (
            <Card
              key={pattern.id}
              className={styles.patternCard}
              onClick={() => onPatternClick?.(pattern)}
            >
              <CardHeader className={styles.patternHeader}>
                <CardTitle className={styles.patternDescription}>
                  {pattern.description}
                </CardTitle>
                <div className={styles.badges}>
                  <Badge className={getConfidenceColor(pattern.confidence)}>
                    {Math.round(pattern.confidence * 100)}% confident
                  </Badge>
                  {pattern.applications > 5 && (
                    <Badge variant="secondary">Frequently Used</Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className={styles.patternContent}>
                <div className={styles.metrics}>
                  <div className={styles.metric}>
                    <div className={styles.metricHeader}>
                      <TrendingUp size={14} />
                      <span>Success Rate</span>
                    </div>
                    <div className={styles.metricValue}>
                      <Progress 
                        value={pattern.success_rate * 100} 
                        className={styles.progressBar}
                      />
                      <span className={styles.percentage}>
                        {Math.round(pattern.success_rate * 100)}%
                      </span>
                    </div>
                  </div>
                  
                  <div className={styles.metric}>
                    <div className={styles.metricHeader}>
                      <Activity size={14} />
                      <span>Applications</span>
                    </div>
                    <div className={styles.metricValue}>
                      <span className={styles.count}>{pattern.applications}</span>
                    </div>
                  </div>
                  
                  <div className={styles.metric}>
                    <div className={styles.metricHeader}>
                      <Calendar size={14} />
                      <span>Last Used</span>
                    </div>
                    <div className={styles.metricValue}>
                      <span className={styles.date}>
                        {formatDate(pattern.last_used)}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>
    );
  }
);

PatternsView.displayName = "PatternsView";