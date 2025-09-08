"use client";

import React, { useState, useCallback, useEffect } from "react";
import { useQueryState } from "nuqs";
import { ChatInterface } from "./components/ChatInterface/ChatInterface";
import { TasksFilesSidebar } from "./components/TasksFilesSidebar/TasksFilesSidebar";
import { SubAgentPanel } from "./components/SubAgentPanel/SubAgentPanel";
import { FileViewDialog } from "./components/FileViewDialog/FileViewDialog";
import { createClient } from "@/lib/client";
import { useAuthContext } from "@/providers/Auth";
import { useMemoryPolling } from "@/hooks/useMemoryPolling";
import type { SubAgent, FileItem, TodoItem, Memory, Pattern, ExecutionData } from "./types/types";
import styles from "./page.module.scss";

export default function HomePage() {
  const { session } = useAuthContext();
  const [threadId, setThreadId] = useQueryState("threadId");
  const [selectedSubAgent, setSelectedSubAgent] = useState<SubAgent | null>(
    null,
  );
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [files, setFiles] = useState<Record<string, string>>({});
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isLoadingThreadState, setIsLoadingThreadState] = useState(false);
  const [stateMemories, setStateMemories] = useState<Memory[]>([]);
  const [statePatterns, setStatePatterns] = useState<Pattern[]>([]);
  const [stateLearningQueue, setStateLearningQueue] = useState<ExecutionData[]>([]);
  
  // Poll for LangMem memories every 5 seconds
  const { 
    memories: langMemMemories, 
    patterns: langMemPatterns, 
    learningQueue: langMemQueue 
  } = useMemoryPolling(5000);
  
  // Combine state memories with LangMem memories
  const memories = [...stateMemories, ...langMemMemories];
  const patterns = [...statePatterns, ...langMemPatterns];
  const learningQueue = [...stateLearningQueue, ...langMemQueue];

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  // When the threadId changes, grab the thread state from the graph server
  useEffect(() => {
    const fetchThreadState = async () => {
      if (!threadId || !session?.accessToken) {
        setTodos([]);
        setFiles({});
        setStateMemories([]);
        setStatePatterns([]);
        setStateLearningQueue([]);
        setIsLoadingThreadState(false);
        return;
      }
      setIsLoadingThreadState(true);
      try {
        const client = createClient(session.accessToken);
        const state = await client.threads.getState(threadId);

        if (state.values) {
          const currentState = state.values as {
            todos?: TodoItem[];
            files?: Record<string, string>;
            memories?: Memory[];
            patterns?: Pattern[];
            learning_queue?: ExecutionData[];
          };
          setTodos(currentState.todos || []);
          setFiles(currentState.files || {});
          setStateMemories(currentState.memories || []);
          setStatePatterns(currentState.patterns || []);
          setStateLearningQueue(currentState.learning_queue || []);
        }
      } catch (error) {
        console.error("Failed to fetch thread state:", error);
        setTodos([]);
        setFiles({});
        setStateMemories([]);
        setStatePatterns([]);
        setStateLearningQueue([]);
      } finally {
        setIsLoadingThreadState(false);
      }
    };
    fetchThreadState();
  }, [threadId, session?.accessToken]);

  const handleNewThread = useCallback(() => {
    setThreadId(null);
    setSelectedSubAgent(null);
    setTodos([]);
    setFiles({});
    setStateMemories([]);
    setStatePatterns([]);
    setStateLearningQueue([]);
  }, [setThreadId]);

  return (
    <div className={styles.container}>
      <TasksFilesSidebar
        todos={todos}
        files={files}
        memories={memories}
        patterns={patterns}
        learningQueue={learningQueue}
        onFileClick={setSelectedFile}
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
      />
      <div className={styles.mainContent}>
        <ChatInterface
          threadId={threadId}
          selectedSubAgent={selectedSubAgent}
          setThreadId={setThreadId}
          onSelectSubAgent={setSelectedSubAgent}
          onTodosUpdate={setTodos}
          onFilesUpdate={setFiles}
          onNewThread={handleNewThread}
          isLoadingThreadState={isLoadingThreadState}
        />
        {selectedSubAgent && (
          <SubAgentPanel
            subAgent={selectedSubAgent}
            onClose={() => setSelectedSubAgent(null)}
          />
        )}
      </div>
      {selectedFile && (
        <FileViewDialog
          file={selectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </div>
  );
}
