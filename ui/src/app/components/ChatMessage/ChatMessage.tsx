"use client";

import React, { useEffect, useMemo } from "react";
import { User, Bot } from "lucide-react";
import { SubAgentIndicator } from "../SubAgentIndicator/SubAgentIndicator";
import { ToolCallBox } from "../ToolCallBox/ToolCallBox";
import { MarkdownContent } from "../MarkdownContent/MarkdownContent";
import type { SubAgent, ToolCall } from "../../types/types";
import styles from "./ChatMessage.module.scss";
import { Message } from "@langchain/langgraph-sdk";
import { extractStringFromMessageContent } from "../../utils/utils";

interface ChatMessageProps {
  message: Message;
  toolCalls: ToolCall[];
  showAvatar: boolean;
  onSelectSubAgent: (subAgent: SubAgent) => void;
  selectedSubAgent: SubAgent | null;
  threadId: string | null;
  filesFromState?: Record<string, string>;
}

export const ChatMessage = React.memo<ChatMessageProps>(
  ({ message, toolCalls, showAvatar, onSelectSubAgent, selectedSubAgent, threadId, filesFromState }) => {
    const isUser = message.type === "human";
    const messageContent = extractStringFromMessageContent(message);
    const hasContent = messageContent && messageContent.trim() !== "";
    const hasToolCalls = toolCalls.length > 0;

    const fallbackImages = useMemo(() => {
      // Prefer explicit file list from state when available
      const fromState = filesFromState
        ? Object.keys(filesFromState).filter((p) => /\.(png|jpe?g|gif|svg|webp|bmp)$/i.test(p))
        : [];
      if (fromState.length > 0) return Array.from(new Set(fromState));

      const files: string[] = [];
      toolCalls.forEach((tc: ToolCall) => {
        if (tc.name === "python_sandbox" && tc.result) {
          // Match patterns like: Saved plot to /tmp/foo.png
          const saved = tc.result.match(/Saved\s+plot\s+to\s+(\/[^\s]+)/g);
          if (saved) {
            saved.forEach((m) => {
              const mm = m.match(/Saved\s+plot\s+to\s+(\/[^\s]+)/);
              if (mm && mm[1]) files.push(mm[1]);
            });
          }
          // Extract any png/jpg/svg paths after a "Generated X file(s):" pattern
          const genIdx = tc.result.indexOf("Generated ");
          if (genIdx >= 0) {
            const after = tc.result.slice(genIdx);
            const list = after.match(/\/[\w\-\.\/]+\.(png|jpg|jpeg|gif|svg)/gi) || [];
            list.forEach((p) => files.push(p));
          }
        }
      });
      // De-duplicate
      return Array.from(new Set(files));
    }, [toolCalls, filesFromState]);
    
    // Removed visualization extraction - images are displayed in ToolCallBox
    const subAgents = useMemo(() => {
      return toolCalls
        .filter((toolCall: ToolCall) => {
          return (
            toolCall.name === "task" &&
            toolCall.args["subagent_type"] &&
            toolCall.args["subagent_type"] !== "" &&
            toolCall.args["subagent_type"] !== null
          );
        })
        .map((toolCall: ToolCall) => {
          return {
            id: toolCall.id,
            name: toolCall.name,
            subAgentName: toolCall.args["subagent_type"],
            input: toolCall.args["description"],
            output: toolCall.result,
            status: toolCall.status,
          };
        });
    }, [toolCalls]);

    useEffect(() => {
      if (
        subAgents.some(
          (subAgent: SubAgent) => subAgent.id === selectedSubAgent?.id,
        )
      ) {
        onSelectSubAgent(
          subAgents.find(
            (subAgent: SubAgent) => subAgent.id === selectedSubAgent?.id,
          )!,
        );
      }
    }, [selectedSubAgent, onSelectSubAgent, subAgents]);

    return (
      <div
        className={`${styles.message} ${isUser ? styles.user : styles.assistant}`}
      >
        <div
          className={`${styles.avatar} ${!showAvatar ? styles.avatarHidden : ""}`}
        >
          {showAvatar &&
            (isUser ? (
              <User className={styles.avatarIcon} />
            ) : (
              <Bot className={styles.avatarIcon} />
            ))}
        </div>
        <div className={styles.content}>
          {hasContent && (
            <div className={styles.bubble}>
              {isUser ? (
                <p className={styles.text}>{messageContent}</p>
              ) : (
                <MarkdownContent content={messageContent} threadId={threadId} fallbackImages={fallbackImages} />
              )}
            </div>
          )}
          {hasToolCalls && (
            <div className={styles.toolCalls}>
              {toolCalls.map((toolCall: ToolCall) => {
                if (toolCall.name === "task") return null;
                return <ToolCallBox key={toolCall.id} toolCall={toolCall} threadId={threadId} />;
              })}
            </div>
          )}
          {!isUser && subAgents.length > 0 && (
            <div className={styles.subAgents}>
              {subAgents.map((subAgent: SubAgent) => (
                <SubAgentIndicator
                  key={subAgent.id}
                  subAgent={subAgent}
                  onClick={() => onSelectSubAgent(subAgent)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  },
);

ChatMessage.displayName = "ChatMessage";
