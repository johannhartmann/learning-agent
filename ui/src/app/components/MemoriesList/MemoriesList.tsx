"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  ChevronDown, 
  ChevronUp,
  Brain,
  Target,
  Lightbulb,
  AlertTriangle,
  BarChart
} from "lucide-react";
import type { Memory } from "../../types/types";
import styles from "./MemoriesList.module.scss";

interface MemoriesListProps {
  memories: Memory[];
  onMemoryClick?: (memory: Memory) => void;
}

export const MemoriesList = React.memo<MemoriesListProps>(
  ({ memories }) => {
    const [expandedMemories, setExpandedMemories] = useState<Set<string>>(new Set());

    const toggleMemory = (memoryId: string) => {
      setExpandedMemories(prev => {
        const next = new Set(prev);
        if (next.has(memoryId)) {
          next.delete(memoryId);
        } else {
          next.add(memoryId);
        }
        return next;
      });
    };

    const getOutcomeIcon = (outcome: Memory["outcome"]) => {
      return outcome === "success" ? (
        <CheckCircle size={16} className={styles.successIcon} />
      ) : (
        <XCircle size={16} className={styles.failureIcon} />
      );
    };

    const formatTimestamp = (timestamp: string) => {
      const date = new Date(timestamp);
      return date.toLocaleString();
    };

    const formatConfidence = (score?: number) => {
      if (!score) return null;
      const percentage = (score * 100).toFixed(0);
      const color = score >= 0.8 ? "green" : score >= 0.5 ? "yellow" : "red";
      return (
        <Badge variant="outline" className={`${styles.confidenceBadge} ${styles[color]}`}>
          {percentage}% confidence
        </Badge>
      );
    };

    const renderLearningSection = (
      title: string, 
      content: string | null | undefined, 
      icon: React.ReactNode
    ) => {
      if (!content) return null;
      
      // Parse markdown-like content for better display
      const lines = content.split('\n').filter(line => line.trim());
      const items = lines.map(line => {
        // Remove markdown headers and bullets
        return line.replace(/^###?\s+/, '')
                  .replace(/^-\s+/, '')
                  .replace(/^\*\*/, '')
                  .replace(/\*\*$/, '')
                  .replace(/\*\*/g, '')
                  .trim();
      }).filter(item => item.length > 0);

      return (
        <div className={styles.learningSection}>
          <div className={styles.sectionHeader}>
            {icon}
            <h5>{title}</h5>
          </div>
          <ul className={styles.learningItems}>
            {items.map((item, index) => (
              <li key={index} className={styles.learningItem}>
                {item}
              </li>
            ))}
          </ul>
        </div>
      );
    };

    const renderAntiPatterns = (antiPatterns: Memory["anti_patterns"]) => {
      if (!antiPatterns) return null;

      return (
        <div className={styles.learningSection}>
          <div className={styles.sectionHeader}>
            <AlertTriangle size={16} className={styles.warningIcon} />
            <h5>Anti-Patterns & Issues</h5>
          </div>
          {antiPatterns.description && (
            <p className={styles.antiPatternDesc}>{antiPatterns.description}</p>
          )}
          {antiPatterns.redundancies && antiPatterns.redundancies.length > 0 && (
            <div className={styles.issueList}>
              <span className={styles.issueLabel}>Redundancies:</span>
              <ul>
                {antiPatterns.redundancies.map((r, i) => (
                  <li key={i}>
                    {typeof r === 'string' ? r : r.suggestion || r.type || JSON.stringify(r)}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {antiPatterns.inefficiencies && antiPatterns.inefficiencies.length > 0 && (
            <div className={styles.issueList}>
              <span className={styles.issueLabel}>Inefficiencies:</span>
              <ul>
                {antiPatterns.inefficiencies.map((item, idx) => (
                  <li key={idx}>
                    {typeof item === 'string' ? item : item.impact || item.type || JSON.stringify(item)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    };

    const renderExecutionMetadata = (metadata: Memory["execution_metadata"]) => {
      if (!metadata) return null;

      return (
        <div className={styles.metadataSection}>
          <div className={styles.sectionHeader}>
            <BarChart size={16} />
            <h5>Execution Metrics</h5>
          </div>
          <div className={styles.metricsGrid}>
            {metadata.efficiency_score !== undefined && (
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Efficiency:</span>
                <span className={styles.metricValue}>
                  {(metadata.efficiency_score * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {metadata.tool_counts && Object.keys(metadata.tool_counts).length > 0 && (
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Tools Used:</span>
                <span className={styles.metricValue}>
                  {Object.entries(metadata.tool_counts)
                    .map(([tool, count]) => `${tool} (${count}x)`)
                    .join(", ")}
                </span>
              </div>
            )}
            {metadata.parallelization_opportunities && 
             metadata.parallelization_opportunities.length > 0 && (
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Parallelization Opportunities:</span>
                <span className={styles.metricValue}>
                  {metadata.parallelization_opportunities.length}
                </span>
              </div>
            )}
          </div>
        </div>
      );
    };

    if (memories.length === 0) {
      return (
        <div className={styles.emptyState}>
          <p>No memories yet. The agent will learn from future interactions.</p>
        </div>
      );
    }

    return (
      <ScrollArea className={styles.scrollArea}>
        <div className={styles.memoriesList}>
          {memories.map((memory) => {
            const isExpanded = expandedMemories.has(memory.id);
            
            return (
              <Card
                key={memory.id}
                className={`${styles.memoryCard} ${isExpanded ? styles.expanded : ''}`}
              >
                <CardHeader 
                  className={styles.memoryHeader}
                  onClick={() => toggleMemory(memory.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className={styles.headerRow}>
                    <div className={styles.titleSection}>
                      <CardTitle className={styles.memoryTask}>
                        {memory.task}
                      </CardTitle>
                      {memory.similarity && (
                        <Badge variant="secondary" className={styles.similarityBadge}>
                          {(memory.similarity * 100).toFixed(0)}% similar
                        </Badge>
                      )}
                    </div>
                    <div className={styles.headerRight}>
                      <div className={styles.outcomeWrapper}>
                        {getOutcomeIcon(memory.outcome)}
                        <Badge
                          variant={memory.outcome === "success" ? "default" : "destructive"}
                          className={styles.outcomeBadge}
                        >
                          {memory.outcome}
                        </Badge>
                      </div>
                      {formatConfidence(memory.confidence_score)}
                      <button className={styles.expandButton}>
                        {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </button>
                    </div>
                  </div>
                  <div className={styles.timestamp}>
                    <Clock size={12} />
                    <span>{formatTimestamp(memory.timestamp)}</span>
                  </div>
                </CardHeader>

                {isExpanded && (
                  <CardContent className={styles.memoryContent}>
                    <Tabs defaultValue="learnings" className={styles.contentTabs}>
                      <TabsList className={styles.tabsList}>
                        <TabsTrigger value="learnings">
                          <Brain size={14} />
                          Learnings
                        </TabsTrigger>
                        {renderExecutionMetadata(memory.execution_metadata) && (
                          <TabsTrigger value="metrics">
                            <BarChart size={14} />
                            Metrics
                          </TabsTrigger>
                        )}
                      </TabsList>

                      <TabsContent value="learnings" className={styles.tabContent}>
                        <div className={styles.learningsGrid}>
                          {renderLearningSection(
                            "Tactical Learning",
                            memory.tactical_learning,
                            <Target size={16} className={styles.tacticalIcon} />
                          )}
                          {renderLearningSection(
                            "Strategic Learning",
                            memory.strategic_learning,
                            <Lightbulb size={16} className={styles.strategicIcon} />
                          )}
                          {renderLearningSection(
                            "Meta Learning",
                            memory.meta_learning,
                            <Brain size={16} className={styles.metaIcon} />
                          )}
                          {renderAntiPatterns(memory.anti_patterns)}
                        </div>
                      </TabsContent>

                      {renderExecutionMetadata(memory.execution_metadata) && (
                        <TabsContent value="metrics" className={styles.tabContent}>
                          {renderExecutionMetadata(memory.execution_metadata)}
                        </TabsContent>
                      )}
                    </Tabs>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      </ScrollArea>
    );
  }
);

MemoriesList.displayName = "MemoriesList";
