"""Execution analyzer for extracting patterns and inefficiencies from agent runs."""

import re
from collections import Counter
from typing import Any


class ExecutionAnalyzer:
    """Analyzes execution traces to identify patterns, inefficiencies, and learning opportunities."""

    def __init__(self) -> None:
        self.tool_sequence: list[str] = []
        self.tool_counts: Counter[str] = Counter()
        self.redundancies: list[dict[str, Any]] = []
        self.missed_opportunities: list[dict[str, Any]] = []
        self.decision_points: list[dict[str, Any]] = []

    def analyze_conversation(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze a conversation to extract execution metadata and patterns.

        Args:
            messages: List of conversation messages with tool calls and responses

        Returns:
            Dictionary containing execution analysis with tool patterns, inefficiencies, etc.
        """
        self.tool_sequence = []
        self.tool_counts = Counter()
        self.redundancies = []
        self.missed_opportunities = []

        # Extract tool calls from messages
        for msg in messages:
            if isinstance(msg, dict):
                content = str(msg.get("content", ""))
                # Look for tool call patterns
                self._extract_tool_calls(content)

        # Analyze patterns
        redundancies = self._identify_redundancies()
        inefficiencies = self._identify_inefficiencies()
        parallelization = self._identify_parallel_opportunities()

        # Calculate metrics
        total_tool_calls = sum(self.tool_counts.values())
        unique_tools = len(self.tool_counts)

        return {
            "tool_sequence": self.tool_sequence,
            "tool_counts": dict(self.tool_counts),
            "total_tool_calls": total_tool_calls,
            "unique_tools_used": unique_tools,
            "redundancies": redundancies,
            "inefficiencies": inefficiencies,
            "parallelization_opportunities": parallelization,
            "execution_patterns": self._extract_patterns(),
            "efficiency_score": self._calculate_efficiency_score(),
        }

    def _extract_tool_calls(self, content: str) -> None:
        """Extract tool calls from message content."""
        # Common tool patterns
        tool_patterns = [
            r"search_memory",
            r"write_todos",
            r"read_file",
            r"write_file",
            r"edit_file",
            r"ls",
            r"queue_learning",
            r"task",
        ]

        for pattern in tool_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.tool_sequence.append(pattern)
                self.tool_counts[pattern] += 1

    def _identify_redundancies(self) -> list[dict[str, Any]]:
        """Identify redundant tool calls."""
        redundancies = []

        # Check for consecutive identical calls
        consecutive_duplicates = [
            {
                "type": "consecutive_duplicate",
                "tool": self.tool_sequence[i],
                "position": i,
                "suggestion": f"Batch {self.tool_sequence[i]} operations",
            }
            for i in range(1, len(self.tool_sequence))
            if self.tool_sequence[i] == self.tool_sequence[i - 1]
        ]
        redundancies.extend(consecutive_duplicates)

        # Check for excessive todo updates
        if self.tool_counts.get("write_todos", 0) > 3:
            redundancies.append(
                {
                    "type": "excessive_updates",
                    "tool": "write_todos",
                    "count": self.tool_counts["write_todos"],
                    "suggestion": "Batch todo updates instead of individual calls",
                }
            )

        # Check for ls after non-filesystem operations
        unnecessary_ls = [
            {
                "type": "unnecessary_ls",
                "position": i,
                "after": self.tool_sequence[i - 1],
                "suggestion": f"'ls' not needed after {self.tool_sequence[i - 1]}",
            }
            for i in range(1, len(self.tool_sequence))
            if self.tool_sequence[i] == "ls"
            and self.tool_sequence[i - 1] in ["write_todos", "search_memory"]
        ]
        redundancies.extend(unnecessary_ls)

        return redundancies

    def _identify_inefficiencies(self) -> list[dict[str, Any]]:
        """Identify inefficient tool usage patterns."""
        inefficiencies = []

        # Check if search_memory was called first (best practice)
        if self.tool_sequence and self.tool_sequence[0] != "search_memory":
            inefficiencies.append(
                {
                    "type": "no_initial_search",
                    "first_tool": self.tool_sequence[0] if self.tool_sequence else None,
                    "impact": "Missed learning from past experiences",
                    "suggestion": "Always start with search_memory for similar tasks",
                }
            )

        # Check for read_file without prior ls or search
        for i, tool in enumerate(self.tool_sequence):
            if tool == "read_file":
                # Check if ls or search preceded it
                prior_tools = self.tool_sequence[:i]
                if "ls" not in prior_tools[-3:] if len(prior_tools) >= 3 else prior_tools:
                    inefficiencies.append(
                        {
                            "type": "read_without_context",
                            "position": i,
                            "suggestion": "Use ls or grep before read_file to understand structure",
                        }
                    )

        # Check for multiple reads of same file (should cache)
        read_patterns = [i for i, t in enumerate(self.tool_sequence) if t == "read_file"]
        if len(read_patterns) > 2:
            inefficiencies.append(
                {
                    "type": "repeated_reads",
                    "count": len(read_patterns),
                    "suggestion": "Cache file contents instead of re-reading",
                }
            )

        return inefficiencies

    def _identify_parallel_opportunities(self) -> list[dict[str, Any]]:
        """Identify missed parallelization opportunities."""
        opportunities = []

        # Look for independent file operations that could be parallel
        file_ops = ["read_file", "write_file", "edit_file"]
        consecutive_file_ops = [
            (i, self.tool_sequence[i], self.tool_sequence[i + 1])
            for i in range(len(self.tool_sequence) - 1)
            if self.tool_sequence[i] in file_ops and self.tool_sequence[i + 1] in file_ops
        ]

        if len(consecutive_file_ops) > 2:
            opportunities.append(
                {
                    "type": "file_operations",
                    "count": len(consecutive_file_ops),
                    "suggestion": "These file operations could run in parallel",
                }
            )

        # Look for independent searches
        search_count = self.tool_counts.get("search_memory", 0)
        if search_count > 1:
            opportunities.append(
                {
                    "type": "multiple_searches",
                    "count": search_count,
                    "suggestion": "Multiple searches could be parallelized",
                }
            )

        return opportunities

    def _extract_patterns(self) -> dict[str, Any]:
        """Extract execution patterns from the tool sequence."""
        patterns = {
            "starts_with_search": self.tool_sequence[0] == "search_memory"
            if self.tool_sequence
            else False,
            "uses_todos": "write_todos" in self.tool_counts,
            "delegates_to_subagent": "task" in self.tool_counts,
            "learns_from_execution": "queue_learning" in self.tool_counts,
            "dominant_tool": self.tool_counts.most_common(1)[0][0] if self.tool_counts else None,
            "tool_diversity": len(self.tool_counts) / max(sum(self.tool_counts.values()), 1),
        }

        # Identify workflow pattern
        if patterns["starts_with_search"] and patterns["uses_todos"]:
            patterns["workflow_pattern"] = "search_plan_execute"
        elif patterns["uses_todos"]:
            patterns["workflow_pattern"] = "plan_execute"
        else:
            patterns["workflow_pattern"] = "ad_hoc"

        return patterns

    def _calculate_efficiency_score(self) -> float:
        """Calculate an efficiency score based on the analysis.

        Returns:
            Score from 0.0 (inefficient) to 1.0 (highly efficient)
        """
        score = 1.0

        # Deduct for redundancies
        redundancy_count = len(self._identify_redundancies())
        score -= min(redundancy_count * 0.1, 0.3)

        # Deduct for inefficiencies
        inefficiency_count = len(self._identify_inefficiencies())
        score -= min(inefficiency_count * 0.15, 0.3)

        # Deduct for missed parallelization
        parallel_missed = len(self._identify_parallel_opportunities())
        score -= min(parallel_missed * 0.1, 0.2)

        # Bonus for good practices
        if self.tool_sequence and self.tool_sequence[0] == "search_memory":
            score += 0.1
        if "queue_learning" in self.tool_counts:
            score += 0.05

        return max(0.0, min(1.0, score))

    def analyze_tool_sequence_pattern(self, sequence: list[str]) -> str:
        """Analyze a tool sequence and return a pattern description.

        Args:
            sequence: List of tool names in order

        Returns:
            Human-readable pattern description
        """
        if not sequence:
            return "No tools used"

        # Common patterns
        if sequence[:2] == ["search_memory", "write_todos"]:
            return "Learn-then-plan pattern (recommended)"
        if sequence[0] == "write_todos":
            return "Plan-first pattern (skipped learning)"
        if sequence[0] == "read_file":
            return "Explore-first pattern (no context gathering)"
        if sequence.count("write_todos") > 5:
            return "Over-planning pattern (excessive todo updates)"
        if "search_memory" not in sequence:
            return "No-learning pattern (missed past experiences)"
        return "Custom pattern"
