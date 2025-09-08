"use client";

import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Brain, History, TrendingUp, Clock } from "lucide-react";
import { MemoriesList } from "../MemoriesList/MemoriesList";
import { PatternsView } from "../PatternsView/PatternsView";
import { LearningQueue } from "../LearningQueue/LearningQueue";
import type { Memory, Pattern, ExecutionData } from "../../types/types";
import styles from "./LearningPanel.module.scss";

interface LearningPanelProps {
  memories: Memory[];
  patterns: Pattern[];
  learningQueue: ExecutionData[];
  onMemoryClick?: (memory: Memory) => void;
  onPatternClick?: (pattern: Pattern) => void;
  onQueueItemClick?: (item: ExecutionData) => void;
}

export const LearningPanel = React.memo<LearningPanelProps>(
  ({
    memories,
    patterns,
    learningQueue,
    onMemoryClick,
    onPatternClick,
    onQueueItemClick,
  }) => {
    const [activeTab, setActiveTab] = useState("memories");

    const stats = {
      totalMemories: memories.length,
      successRate: memories.length > 0
        ? (memories.filter(m => m.outcome === "success").length / memories.length * 100).toFixed(1)
        : "0",
      activePatterns: patterns.filter(p => p.confidence > 0.5).length,
      queueSize: learningQueue.length,
    };

    return (
      <div className={styles.learningPanel}>
        <div className={styles.header}>
          <Brain size={24} />
          <h2>Learning System</h2>
        </div>

        <div className={styles.statsGrid}>
          <Card className={styles.statCard}>
            <CardContent className={styles.statContent}>
              <History size={16} />
              <div>
                <p className={styles.statValue}>{stats.totalMemories}</p>
                <p className={styles.statLabel}>Memories</p>
              </div>
            </CardContent>
          </Card>

          <Card className={styles.statCard}>
            <CardContent className={styles.statContent}>
              <TrendingUp size={16} />
              <div>
                <p className={styles.statValue}>{stats.successRate}%</p>
                <p className={styles.statLabel}>Success Rate</p>
              </div>
            </CardContent>
          </Card>

          <Card className={styles.statCard}>
            <CardContent className={styles.statContent}>
              <Brain size={16} />
              <div>
                <p className={styles.statValue}>{stats.activePatterns}</p>
                <p className={styles.statLabel}>Patterns</p>
              </div>
            </CardContent>
          </Card>

          <Card className={styles.statCard}>
            <CardContent className={styles.statContent}>
              <Clock size={16} />
              <div>
                <p className={styles.statValue}>{stats.queueSize}</p>
                <p className={styles.statLabel}>Pending</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className={styles.tabs}
        >
          <TabsList className={styles.tabsList}>
            <TabsTrigger value="memories" className={styles.tabTrigger}>
              <History size={14} />
              Memories ({memories.length})
            </TabsTrigger>
            <TabsTrigger value="patterns" className={styles.tabTrigger}>
              <Brain size={14} />
              Patterns ({patterns.length})
            </TabsTrigger>
            <TabsTrigger value="queue" className={styles.tabTrigger}>
              <Clock size={14} />
              Queue ({learningQueue.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="memories" className={styles.tabContent}>
            <MemoriesList
              memories={memories}
              onMemoryClick={onMemoryClick}
            />
          </TabsContent>

          <TabsContent value="patterns" className={styles.tabContent}>
            <PatternsView
              patterns={patterns}
              onPatternClick={onPatternClick}
            />
          </TabsContent>

          <TabsContent value="queue" className={styles.tabContent}>
            <LearningQueue
              queue={learningQueue}
              onItemClick={onQueueItemClick}
            />
          </TabsContent>
        </Tabs>
      </div>
    );
  }
);

LearningPanel.displayName = "LearningPanel";
