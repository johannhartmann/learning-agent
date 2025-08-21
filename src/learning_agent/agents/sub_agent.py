"""Sub-agent implementation for parallel task execution."""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

from learning_agent.config import settings
from learning_agent.providers import get_chat_model


class SubAgentConfig(BaseModel):
    """Configuration for a sub-agent."""

    agent_id: str = Field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    name: str = Field(default="SubAgent")
    description: str = Field(default="Sub-agent for task execution")
    task: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = Field(default=5)
    timeout_seconds: int = Field(default=300)


class SubAgentResult(BaseModel):
    """Result from sub-agent execution."""

    agent_id: str
    task: str
    status: str  # "success", "failure", "timeout"
    result: Any | None = None
    error: str | None = None
    duration_seconds: float
    steps_taken: list[dict[str, Any]] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)


class SubAgent:
    """Sub-agent for executing individual tasks."""

    def __init__(self, config: SubAgentConfig):
        """Initialize the sub-agent."""
        self.config = config
        self.agent_id = config.agent_id
        self.start_time: datetime | None = None
        self.execution_history: list[Any] = []

        # Initialize LLM using provider factory
        self.llm = get_chat_model(settings)

        # Initialize tools
        self.tools = self._create_tools()

        # Create agent executor
        self.agent_executor = self._create_agent_executor()

    def _create_tools(self) -> list[Tool]:
        """Create tools available to the sub-agent."""
        tools = []

        # Planning tool
        planning_tool = Tool(
            name="create_plan",
            description="Create a plan for completing a task",
            func=self._create_plan,
        )
        tools.append(planning_tool)

        # Execution tool
        execution_tool = Tool(
            name="execute_step",
            description="Execute a single step of the plan",
            func=self._execute_step,
        )
        tools.append(execution_tool)

        # Status tool
        status_tool = Tool(
            name="check_status",
            description="Check the status of execution",
            func=self._check_status,
        )
        tools.append(status_tool)

        return tools

    def _create_agent_executor(self) -> AgentExecutor:
        """Create the agent executor with React pattern."""

        # React prompt template
        react_prompt = PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
            template="""You are a sub-agent responsible for executing a specific task.

Task: {input}

You have access to the following tools:
{tools}

Use the following format:
Thought: Think about what needs to be done
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have completed the task
Final Answer: the final result

Begin!

{agent_scratchpad}""",
        )

        # Create React agent
        agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=react_prompt)

        # Create executor
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            max_iterations=self.config.max_iterations,
            handle_parsing_errors=True,
            verbose=settings.debug_mode,
        )

        return executor

    async def execute(self, task: str) -> SubAgentResult:
        """Execute the assigned task."""
        self.start_time = datetime.now()
        self.config.task = task

        try:
            # Run with timeout
            result = await asyncio.wait_for(
                self._run_task(task), timeout=self.config.timeout_seconds
            )

            duration = (datetime.now() - self.start_time).total_seconds()

            return SubAgentResult(
                agent_id=self.agent_id,
                task=task,
                status="success",
                result=result,
                duration_seconds=duration,
                steps_taken=self.execution_history,
                tools_used=self._get_tools_used(),
            )

        except TimeoutError:
            duration = (datetime.now() - self.start_time).total_seconds()
            return SubAgentResult(
                agent_id=self.agent_id,
                task=task,
                status="timeout",
                error=f"Task execution timed out after {self.config.timeout_seconds}s",
                duration_seconds=duration,
                steps_taken=self.execution_history,
                tools_used=self._get_tools_used(),
            )

        except Exception as e:
            duration = (datetime.now() - self.start_time).total_seconds()
            return SubAgentResult(
                agent_id=self.agent_id,
                task=task,
                status="failure",
                error=str(e),
                duration_seconds=duration,
                steps_taken=self.execution_history,
                tools_used=self._get_tools_used(),
            )

    async def _run_task(self, task: str) -> Any:
        """Run the actual task execution."""
        # Use agent executor
        result = await self.agent_executor.ainvoke({"input": task})
        return result.get("output", "Task completed")

    def _create_plan(self, task_description: str) -> str:
        """Create a plan for the task."""
        step = {
            "action": "create_plan",
            "input": task_description,
            "timestamp": datetime.now().isoformat(),
        }
        self.execution_history.append(step)

        # Simple planning logic - in production would be more sophisticated
        plan = f"Plan created for: {task_description}\n"
        plan += "1. Analyze requirements\n"
        plan += "2. Execute implementation\n"
        plan += "3. Verify results"

        step["output"] = plan
        return plan

    def _execute_step(self, step_description: str) -> str:
        """Execute a single step."""
        step = {
            "action": "execute_step",
            "input": step_description,
            "timestamp": datetime.now().isoformat(),
        }
        self.execution_history.append(step)

        # Simulate step execution
        result = f"Executed: {step_description}"
        step["output"] = result
        return result

    def _check_status(self, query: str) -> str:
        """Check execution status."""
        step = {"action": "check_status", "input": query, "timestamp": datetime.now().isoformat()}
        self.execution_history.append(step)

        status = f"Status check: {len(self.execution_history)} steps completed"
        step["output"] = status
        return status

    def _get_tools_used(self) -> list[str]:
        """Get list of tools used during execution."""
        tools = set()
        for step in self.execution_history:
            if "action" in step:
                tools.add(step["action"])
        return list(tools)

    def get_state(self) -> dict[str, Any]:
        """Get current agent state."""
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "task": self.config.task,
            "steps_completed": len(self.execution_history),
            "is_running": self.start_time is not None,
            "context": self.config.context,
        }


class SubAgentPool:
    """Manages a pool of sub-agents for parallel execution."""

    def __init__(self, max_agents: int = 10):
        """Initialize the agent pool."""
        self.max_agents = max_agents
        self.agents: dict[str, SubAgent] = {}
        self.available_agents: list[str] = []
        self.busy_agents: dict[str, str] = {}  # agent_id -> task

    def create_agent(self, config: SubAgentConfig | None = None) -> SubAgent:
        """Create a new sub-agent."""
        if config is None:
            config = SubAgentConfig()

        agent = SubAgent(config)
        self.agents[agent.agent_id] = agent
        self.available_agents.append(agent.agent_id)

        return agent

    def get_available_agent(self) -> SubAgent | None:
        """Get an available agent from the pool."""
        if self.available_agents:
            agent_id = self.available_agents.pop(0)
            return self.agents[agent_id]
        if len(self.agents) < self.max_agents:
            # Create new agent if under limit
            return self.create_agent()
        return None

    def assign_task(self, agent_id: str, task: str) -> None:
        """Assign a task to an agent."""
        if agent_id in self.available_agents:
            self.available_agents.remove(agent_id)
        self.busy_agents[agent_id] = task

    def release_agent(self, agent_id: str) -> None:
        """Release an agent back to the pool."""
        if agent_id in self.busy_agents:
            del self.busy_agents[agent_id]
        if agent_id not in self.available_agents:
            self.available_agents.append(agent_id)

    async def execute_parallel(self, tasks: list[str]) -> list[SubAgentResult]:
        """Execute multiple tasks in parallel."""
        results = []

        # Create tasks for parallel execution
        async_tasks = []
        assigned_agents = []

        for task in tasks:
            agent = self.get_available_agent()
            if agent:
                self.assign_task(agent.agent_id, task)
                assigned_agents.append(agent.agent_id)
                async_tasks.append(agent.execute(task))
            else:
                # If no agent available, wait and retry
                await asyncio.sleep(0.1)
                agent = self.get_available_agent()
                if agent:
                    self.assign_task(agent.agent_id, task)
                    assigned_agents.append(agent.agent_id)
                    async_tasks.append(agent.execute(task))

        # Execute all tasks
        if async_tasks:
            results = await asyncio.gather(*async_tasks)

        # Release agents
        for agent_id in assigned_agents:
            self.release_agent(agent_id)

        return results

    def get_pool_status(self) -> dict[str, Any]:
        """Get pool status."""
        return {
            "total_agents": len(self.agents),
            "available_agents": len(self.available_agents),
            "busy_agents": len(self.busy_agents),
            "max_agents": self.max_agents,
            "tasks_in_progress": list(self.busy_agents.values()),
        }
