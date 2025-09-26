"use client";

import React from "react";
import {
  CheckCircle,
  AlertCircle,
  Loader2,
  ArrowUpRight,
  Sparkles,
} from "lucide-react";
import type { SubAgent } from "../../types/types";
import styles from "./SubAgentCard.module.scss";

interface SubAgentCardProps {
  subAgent: SubAgent;
  onSelect: (subAgent: SubAgent) => void;
  isSelected: boolean;
}

const STATUS_COPY: Record<SubAgent["status"], string> = {
  pending: "Delegating…",
  active: "In progress",
  completed: "Completed",
  error: "Failed",
};

export const SubAgentCard: React.FC<SubAgentCardProps> = ({
  subAgent,
  onSelect,
  isSelected,
}) => {
  const handleClick = () => {
    onSelect(subAgent);
  };

  const renderStatusIcon = () => {
    switch (subAgent.status) {
      case "completed":
        return <CheckCircle className={styles.statusCompleted} />;
      case "error":
        return <AlertCircle className={styles.statusError} />;
      case "pending":
      case "active":
      default:
        return <Loader2 className={styles.statusPending} />;
    }
  };

  const hasOutput =
    subAgent.output !== undefined && subAgent.output !== null && `${subAgent.output}`.trim() !== "";

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`${styles.card} ${isSelected ? styles.selected : ""}`}
      aria-pressed={isSelected}
      aria-label={`View ${subAgent.subAgentName} details`}
    >
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <Sparkles className={styles.agentIcon} />
          <div>
            <span className={styles.title}>Delegated to</span>
            <span className={styles.agentName}>{subAgent.subAgentName}</span>
          </div>
        </div>
        <div className={styles.status}>
          {renderStatusIcon()}
          <span className={styles.statusLabel}>{STATUS_COPY[subAgent.status]}</span>
        </div>
      </div>
      {subAgent.input && (
        <div className={styles.section}>
          <span className={styles.sectionLabel}>Request</span>
          <p className={styles.sectionBody}>{`${subAgent.input}`}</p>
        </div>
      )}
      {hasOutput && (
        <div className={styles.section}>
          <span className={styles.sectionLabel}>Summary</span>
          <p className={styles.sectionBody}>{`${subAgent.output}`}</p>
        </div>
      )}
      <div className={styles.footer}>
        <span>Inspect details</span>
        <ArrowUpRight className={styles.footerIcon} />
      </div>
    </button>
  );
};

SubAgentCard.displayName = "SubAgentCard";
