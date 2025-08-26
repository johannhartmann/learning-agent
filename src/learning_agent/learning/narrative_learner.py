"""Natural language learning system with deep reflection and semantic search."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import faiss
import numpy as np

# Removed get_current_callbacks import - will pass callbacks explicitly
from langmem import create_memory_manager
from pydantic import BaseModel, Field


try:
    from langsmith import traceable
except ImportError:
    # Fallback if langsmith is not installed
    def traceable(**kwargs: Any) -> Any:  # noqa: ARG001
        def decorator(func: Any) -> Any:
            return func

        return decorator


from learning_agent.config import settings
from learning_agent.providers import get_chat_model, get_embeddings


class NarrativeMemory(BaseModel):
    """Structured output for narrative memory creation."""

    narrative: str = Field(
        description="A story-like narrative memory of the experience, including intent, approach, insights, and lessons"
    )


class ReflectionOutput(BaseModel):
    """Structured output for reflections."""

    reflection: str = Field(description="The deep reflection on the specific aspect")


class QueryEnrichment(BaseModel):
    """Structured output for query enrichment."""

    enriched_query: str = Field(
        description="Rich description of the task including intent, problem type, skills needed, and task category"
    )


class RelevanceAnalysis(BaseModel):
    """Structured output for relevance analysis."""

    analysis: str = Field(
        description="Actionable advice based on past experiences including what to repeat and what to avoid"
    )


class PatternAnalysis(BaseModel):
    """Structured output for pattern analysis."""

    patterns: str = Field(
        description="Analysis of patterns, habits, and growth areas across multiple experiences"
    )


class NarrativeLearner:
    """
    Learning system that thinks in natural language narratives.

    - Stores experiences as rich stories
    - Reflects from multiple perspectives
    - Searches semantically for relevant memories
    - Learns patterns across experiences
    """

    def __init__(self, storage_path: Path | None = None):
        """Initialize the narrative learner."""
        self.storage_path = storage_path or Path(".agent") / "narratives"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize LLM and embeddings
        self.llm = get_chat_model(settings)
        self.embeddings = get_embeddings(settings)

        # Initialize memory manager using langmem for narrative extraction
        self.memory_manager = create_memory_manager(
            self.llm,
            enable_inserts=True,
            enable_updates=True,
            enable_deletes=False,
        )

        # Initialize FAISS for semantic search
        self.vector_dimension = 1536  # Will be set dynamically on first embedding
        self.vector_store: Any | None = None  # Initialize on first use
        self.memories: list[Any] = []  # Store narratives alongside vectors

        # Queue for background reflection
        self.reflection_queue: asyncio.Queue[Any] = asyncio.Queue()
        self.background_task: asyncio.Task[Any] | None = None

        # Load existing memories if any
        self._load_memories()

    def _load_memories(self) -> None:
        """Load existing memories from disk."""
        index_path = self.storage_path / "faiss.index"
        memories_path = self.storage_path / "memories.txt"

        if index_path.exists() and memories_path.exists():
            try:
                # Load FAISS index
                self.vector_store = faiss.read_index(str(index_path))

                # Load narrative memories
                with memories_path.open(encoding="utf-8") as f:
                    content = f.read()
                    # Memories are separated by special delimiter
                    self.memories = content.split("\n---MEMORY---\n")
                    self.memories = [m.strip() for m in self.memories if m.strip()]
            except Exception as e:
                print(f"Could not load existing memories: {e}")
                self.vector_store = None
                self.memories = []

    def _save_memories(self) -> None:
        """Save memories to disk."""
        if self.vector_store is not None and self.memories:
            try:
                # Save FAISS index
                index_path = self.storage_path / "faiss.index"
                faiss.write_index(self.vector_store, str(index_path))

                # Save narrative memories
                memories_path = self.storage_path / "memories.txt"
                with memories_path.open("w", encoding="utf-8") as f:
                    f.write("\n---MEMORY---\n".join(self.memories))
            except Exception as e:
                print(f"Could not save memories: {e}")

    async def start_background_processor(self) -> None:
        """Start the background reflection processor."""
        if self.background_task is None or self.background_task.done():
            self.background_task = asyncio.create_task(self._process_reflection_queue())

    async def stop_background_processor(self) -> None:
        """Stop the background processor gracefully."""
        if self.background_task and not self.background_task.done():
            await self.reflection_queue.put(None)
            await self.background_task

    async def _process_reflection_queue(self) -> None:
        """Process reflections in the background."""
        while True:
            try:
                task = await self.reflection_queue.get()
                if task is None:  # Shutdown signal
                    break
                # Extract callbacks from task if present
                callbacks = task.pop("callbacks", None) if isinstance(task, dict) else None
                await self._deep_reflection(task, callbacks=callbacks)
            except Exception as e:
                print(f"Reflection error: {e}")

    @traceable(name="create_narrative_memory", run_type="chain")
    async def create_narrative_memory(
        self, execution_data: dict[str, Any], callbacks: Any = None
    ) -> str:
        """Create a rich narrative memory from an execution."""
        narrative_prompt = f"""I just completed a task and I want to remember this experience as a story.

The user asked: {execution_data.get("task", "Unknown task")}

Here's what happened step by step:
{execution_data.get("execution_trace", "No trace available")}

The outcome was: {execution_data.get("outcome", "Unknown")}
It took {execution_data.get("duration", 0):.2f} seconds.

Write a narrative memory of this experience. Include:
- What the task was really about (the intent, not just the literal request)
- My approach and why I chose it
- What worked well
- What surprised me or was harder than expected
- Key insights I should remember for similar tasks

Write this as a story I'm telling my future self - conversational, insightful, and honest about what happened."""

        structured_llm = self.llm.with_structured_output(NarrativeMemory)
        config = {"callbacks": callbacks} if callbacks else {}
        narrative_response = await structured_llm.ainvoke(narrative_prompt, config=config)
        if isinstance(narrative_response, NarrativeMemory):
            narrative = narrative_response.narrative
        else:
            narrative = str(narrative_response)

        # Store the narrative with its embedding
        await self._store_narrative(narrative)

        return str(narrative)

    async def _store_narrative(self, narrative: str) -> None:
        """Store a narrative memory with its embedding."""
        # Get embedding for the narrative
        embedding = await self.embeddings.aembed_query(narrative)
        embedding_array = np.array(embedding, dtype="float32")

        # Initialize vector store if needed
        if self.vector_store is None:
            self.vector_dimension = len(embedding)
            self.vector_store = faiss.IndexFlatL2(self.vector_dimension)

        # Add to vector store
        self.vector_store.add(np.array([embedding_array]))
        self.memories.append(narrative)

        # Save to disk
        self._save_memories()

    @traceable(name="deep_reflection", run_type="chain")
    async def _deep_reflection(self, execution_data: dict[str, Any], callbacks: Any = None) -> None:  # noqa: ARG002
        """Perform deep multi-angle reflection on an execution."""
        reflections = []

        # Reflection 1: Order and Dependencies
        order_reflection_prompt = f"""Looking at this task execution sequence:

Task: {execution_data.get("task")}
Steps taken: {execution_data.get("steps", [])}

Reflect deeply on the order of operations:
- Which steps should have come earlier? Why?
- Were there unnecessary dependencies between steps?
- Could any steps have been done in parallel?
- Was there a more logical sequence I missed?
- Did I do things in order just out of habit?

Tell me what you learned about task sequencing and dependencies."""

        structured_llm = self.llm.with_structured_output(ReflectionOutput)
        order_reflection = await structured_llm.ainvoke(order_reflection_prompt)
        reflections.append(
            (
                "Order and Dependencies",
                order_reflection.reflection
                if isinstance(order_reflection, ReflectionOutput)
                else str(order_reflection),
            )
        )

        # Reflection 2: Tool Selection
        tool_reflection_prompt = f"""Examining the tools used in this execution:

Task: {execution_data.get("task")}
Tools used: {execution_data.get("tools_used", [])}
Results from each tool: {execution_data.get("tool_results", [])}

Question every tool choice:
- Was each tool the right choice for what it was asked to do?
- Were there better tools available that I overlooked?
- Did any tool struggle or produce unexpected results?
- Did I use a complex tool for a simple problem?
- What would I use differently next time?

Share your honest assessment of tool selection."""

        structured_llm = self.llm.with_structured_output(ReflectionOutput)
        tool_reflection = await structured_llm.ainvoke(tool_reflection_prompt)
        reflections.append(
            (
                "Tool Selection",
                tool_reflection.reflection
                if isinstance(tool_reflection, ReflectionOutput)
                else str(tool_reflection),
            )
        )

        # Reflection 3: Necessity and Efficiency
        efficiency_reflection_prompt = f"""Review this entire execution critically:

Task: {execution_data.get("task")}
Full execution: {execution_data.get("full_trace")}
Time taken: {execution_data.get("duration", 0):.2f} seconds

Question every single step:
- Which steps were absolutely necessary?
- Which steps added no value to the outcome?
- What was overcomplicated?
- Where did I waste time?
- How could this entire task be simpler?

Be ruthless about unnecessary complexity."""

        structured_llm = self.llm.with_structured_output(ReflectionOutput)
        efficiency_reflection = await structured_llm.ainvoke(efficiency_reflection_prompt)
        reflections.append(
            (
                "Efficiency",
                efficiency_reflection.reflection
                if isinstance(efficiency_reflection, ReflectionOutput)
                else str(efficiency_reflection),
            )
        )

        # Reflection 4: Failure Analysis (if applicable)
        if execution_data.get("outcome") != "success":
            failure_reflection_prompt = f"""This task failed or had issues that need deep analysis:

Task: {execution_data.get("task")}
Error: {execution_data.get("error", "Unknown error")}
What I tried: {execution_data.get("steps", [])}

Dig deep into the failure:
- What was the root cause? Not the symptom, but the real cause?
- Was it a planning problem or an execution problem?
- Did I misunderstand what was being asked?
- What warning signs did I miss along the way?
- What specific check or validation would have caught this?
- How do I prevent this exact failure in the future?

Give me your honest, detailed analysis of what went wrong."""

            structured_llm = self.llm.with_structured_output(ReflectionOutput)
            failure_reflection = await structured_llm.ainvoke(failure_reflection_prompt)
            reflections.append(
                (
                    "Failure Analysis",
                    failure_reflection.reflection
                    if isinstance(failure_reflection, ReflectionOutput)
                    else str(failure_reflection),
                )
            )

        # Reflection 5: Generalization and Patterns
        generalization_reflection_prompt = f"""From this specific task execution:

Task: {execution_data.get("task")}
Approach taken: {execution_data.get("approach")}
Outcome: {execution_data.get("outcome")}

Extract the general principles:
- What broader pattern does this task represent?
- What category of problems is this?
- What other tasks would benefit from this approach?
- What assumptions did I make that I should question?
- What would work differently in a different context?

Share the broader lessons that apply beyond this specific task."""

        structured_llm = self.llm.with_structured_output(ReflectionOutput)
        generalization_reflection = await structured_llm.ainvoke(generalization_reflection_prompt)
        reflections.append(
            (
                "Generalization",
                generalization_reflection.reflection
                if isinstance(generalization_reflection, ReflectionOutput)
                else str(generalization_reflection),
            )
        )

        # Synthesize all reflections into a unified narrative
        synthesis_prompt = f"""I've reflected on a task execution from multiple angles:

{chr(10).join([f"{angle}:{chr(10)}{reflection}" for angle, reflection in reflections])}

Synthesize these perspectives into a single, coherent story of what I learned.
This should be a narrative that captures all the insights but reads naturally,
not as a list or report. This is the memory I'll search for when I encounter
similar tasks in the future.

Write it as advice to my future self - what to remember, what to do differently,
and what wisdom was gained from this experience."""

        structured_llm = self.llm.with_structured_output(NarrativeMemory)
        synthesis = await structured_llm.ainvoke(synthesis_prompt)
        unified_narrative = (
            synthesis.narrative if isinstance(synthesis, NarrativeMemory) else str(synthesis)
        )

        # Store the synthesized learning
        await self._store_narrative(unified_narrative)

    async def find_relevant_experiences(
        self, task: str, context: str | None, recent_memories: list[Any] | None = None
    ) -> str:
        """Find and analyze relevant past experiences for a new task."""
        _ = recent_memories  # Unused but kept for API compatibility
        if not self.vector_store or not self.memories:
            return ""

        # Create an enriched query that captures intent
        query_prompt = f"""I need to understand what this task is really about to find relevant past experiences.

The user is asking: {task}
The context is: {context or "No specific context"}

Describe:
- What is the underlying intent of this task?
- What type of problem is being solved?
- What skills or tools might be needed?
- What category of task is this?

Write a rich description that will help me find similar past experiences."""

        structured_llm = self.llm.with_structured_output(QueryEnrichment)
        enriched_query_response = await structured_llm.ainvoke(query_prompt)
        enriched_query = (
            enriched_query_response.enriched_query
            if isinstance(enriched_query_response, QueryEnrichment)
            else str(enriched_query_response)
        )

        # Get embedding and search
        query_embedding = await self.embeddings.aembed_query(enriched_query)
        query_array = np.array([query_embedding], dtype="float32")

        # Search for similar memories
        k = min(5, len(self.memories))  # Get up to 5 similar memories
        if k > 0:
            distances, indices = self.vector_store.search(query_array, k)

            # Get the actual memory narratives
            similar_memories = [self.memories[i] for i in indices[0] if i < len(self.memories)]

            # Analyze relevance and extract applicable lessons
            relevance_prompt = f"""For the current task: {task}
Context: {context or "General execution"}

I found these past experiences:

{chr(10).join([f"Experience {i + 1}:{chr(10)}{mem}" for i, mem in enumerate(similar_memories)])}

Analyze these experiences and tell me:
- Which experiences are truly relevant to this new task and why
- What specific lessons from these experiences apply here
- What approaches worked that I should repeat
- What mistakes or pitfalls I should avoid
- Any warnings or special considerations

Give me actionable advice based on these past experiences, not just a summary."""

            structured_llm = self.llm.with_structured_output(RelevanceAnalysis)
            relevance_analysis = await structured_llm.ainvoke(relevance_prompt)
            return str(
                relevance_analysis.analysis
                if isinstance(relevance_analysis, RelevanceAnalysis)
                else relevance_analysis
            )

        return ""

    @traceable(name="pattern_consolidation", run_type="chain")
    async def consolidate_patterns(self, callbacks: Any = None) -> str:  # noqa: ARG002
        """Periodically analyze memories to find patterns across experiences."""
        if len(self.memories) < 5:
            return ""  # Need enough memories to find patterns

        # Get recent memories for pattern analysis
        recent_memories = self.memories[-20:] if len(self.memories) > 20 else self.memories

        pattern_prompt = f"""Looking across these recent task executions and their learnings:

{chr(10).join([f"Memory {i + 1}:{chr(10)}{mem[:500]}..." for i, mem in enumerate(recent_memories)])}

Find the deeper patterns:
- What mistakes do I keep making across different tasks?
- What approaches consistently work well regardless of task type?
- What assumptions do I repeatedly make that I should question?
- What types of tasks do I handle well vs poorly?
- What tools do I overuse or underuse?
- What do I tend to overcomplicate?

Tell me the story of my learning journey:
- What am I getting better at?
- What am I still struggling with?
- What should I focus on improving?
- What habits should I build or break?

Write this as honest advice to myself about my patterns and growth areas."""

        structured_llm = self.llm.with_structured_output(PatternAnalysis)
        pattern_analysis = await structured_llm.ainvoke(pattern_prompt)
        meta_learning = (
            pattern_analysis.patterns
            if isinstance(pattern_analysis, PatternAnalysis)
            else str(pattern_analysis)
        )

        # Store this meta-learning as a special memory
        meta_memory = (
            f"[META-LEARNING from analyzing {len(recent_memories)} experiences]\n\n{meta_learning}"
        )
        await self._store_narrative(meta_memory)

        return str(meta_learning)

    async def queue_for_reflection(
        self,
        execution_data: dict[str, Any],
        callbacks: Any = None,  # noqa: ARG002
    ) -> None:
        """Queue an execution for deep background reflection."""
        reflection_task = {
            "id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            **execution_data,
        }
        await self.reflection_queue.put(reflection_task)

    def schedule_post_execution_learning(
        self, execution_data: dict[str, Any], callbacks: Any = None
    ) -> None:
        """Schedule learning after task execution with callback propagation."""
        # Create context-aware tasks that preserve callback chain
        asyncio.create_task(self.create_narrative_memory(execution_data, callbacks=callbacks))  # noqa: RUF006

        # Queue for deep reflection
        asyncio.create_task(self.queue_for_reflection(execution_data, callbacks=callbacks))  # noqa: RUF006

        # Schedule pattern consolidation if we have enough memories
        if len(self.memories) > 0 and len(self.memories) % 10 == 0:
            asyncio.create_task(self.consolidate_patterns(callbacks=callbacks))  # noqa: RUF006

    async def get_quick_context(self, task: str) -> dict[str, Any]:
        """Get quick context without blocking."""
        # Check if we have memories to search
        if self.vector_store is not None and self.memories:
            try:
                # Quick embedding and search
                embedding = await self.embeddings.aembed_query(task)
                query_array = np.array([embedding], dtype="float32")

                k = min(3, len(self.memories))
                if k > 0:
                    distances, indices = self.vector_store.search(query_array, k)

                    # Calculate confidence based on similarity (closer = higher confidence)
                    # FAISS L2 distance: 0 = identical, larger = less similar
                    best_distance = float(distances[0][0]) if distances.size > 0 else float("inf")
                    # Convert distance to confidence (rough heuristic)
                    confidence = max(0.1, min(0.9, 1.0 - (best_distance / 10.0)))

                    recent_memories = [
                        self.memories[i] for i in indices[0][:3] if i < len(self.memories)
                    ]

                    return {
                        "has_prior_experience": True,
                        "recent_memories": recent_memories,
                        "confidence": confidence,
                    }
            except Exception as e:
                print(f"Quick context error: {e}")

        return {
            "has_prior_experience": False,
            "recent_memories": [],
            "confidence": 0.1,
        }

    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self.stop_background_processor()
        self._save_memories()
