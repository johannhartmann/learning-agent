"""LangSmith-based probabilistic testing for the learning agent.

This module uses LangSmith datasets and evaluations to test the complex,
non-deterministic behaviors of the learning agent system.
"""

import asyncio
import os
from typing import Any

from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run

from learning_agent.agent import create_learning_agent


# Initialize LangSmith client
client = Client()


# Test Datasets
def create_test_datasets():
    """Create or update LangSmith datasets for testing."""

    # Dataset 1: Simple task execution
    simple_tasks = client.create_dataset(
        "learning-agent-simple-tasks",
        description="Simple tasks to test basic execution flow",
    )

    simple_examples = [
        {"input": {"task": "Say hello"}, "expected": {"contains": ["hello", "greeting"]}},
        {"input": {"task": "Calculate 5 + 3"}, "expected": {"result": 8, "type": "calculation"}},
        {"input": {"task": "List three colors"}, "expected": {"count": 3, "type": "list"}},
    ]

    for example in simple_examples:
        client.create_example(
            dataset_id=simple_tasks.id,
            inputs=example["input"],
            outputs=example["expected"],
        )

    # Dataset 2: Complex multi-step tasks
    complex_tasks = client.create_dataset(
        "learning-agent-complex-tasks",
        description="Complex tasks requiring planning and multiple steps",
    )

    complex_examples = [
        {
            "input": {
                "task": "Create a Python function to calculate factorial and test it with n=5"
            },
            "expected": {"steps": ["plan", "implement", "test"], "result": 120},
        },
        {
            "input": {
                "task": "Analyze the benefits of async programming and summarize in 3 points"
            },
            "expected": {"points": 3, "topics": ["concurrency", "performance", "scalability"]},
        },
    ]

    for example in complex_examples:
        client.create_example(
            dataset_id=complex_tasks.id,
            inputs=example["input"],
            outputs=example["expected"],
        )

    # Dataset 3: Learning and adaptation tasks
    learning_tasks = client.create_dataset(
        "learning-agent-adaptation",
        description="Tasks to test learning and memory capabilities",
    )

    learning_examples = [
        {
            "input": {
                "task": "Remember that the user prefers Python over JavaScript",
                "followup": "What language should I use?",
            },
            "expected": {"remembers": True, "preference": "Python"},
        },
        {
            "input": {
                "task": "Learn from this mistake: file.txt should be file.py",
                "followup": "Create a new file",
            },
            "expected": {"learns": True, "correct_extension": ".py"},
        },
    ]

    for example in learning_examples:
        client.create_example(
            dataset_id=learning_tasks.id,
            inputs=example["input"],
            outputs=example["expected"],
        )

    return {
        "simple": simple_tasks,
        "complex": complex_tasks,
        "learning": learning_tasks,
    }


# Evaluator Functions
async def execution_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate if the task was executed correctly."""
    output = run.outputs or {}
    expected = example.outputs or {}

    scores = {}

    # Check task completion
    if "status" in output:
        scores["completion"] = 1.0 if output["status"] in ["completed", "success"] else 0.0

    # Check for expected content
    if "contains" in expected and "summary" in output:
        summary_lower = output["summary"].lower()
        contains_score = sum(
            1 for word in expected["contains"] if word.lower() in summary_lower
        ) / len(expected["contains"])
        scores["content_match"] = contains_score

    # Check numerical results
    if "result" in expected and "result" in output:
        try:
            actual = float(output["result"])
            expected_val = float(expected["result"])
            scores["numerical_accuracy"] = 1.0 if abs(actual - expected_val) < 0.01 else 0.0
        except (ValueError, TypeError):
            pass

    # Check step completion for complex tasks
    if "steps" in expected and "todos_completed" in output:
        scores["step_completion"] = min(1.0, output["todos_completed"] / len(expected["steps"]))

    return scores


async def learning_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate learning and memory capabilities."""
    _ = run.outputs or {}
    expected = example.outputs or {}

    scores = {}

    # Check if system remembers context
    if "remembers" in expected:
        # This would need to check if subsequent runs show memory
        scores["memory_retention"] = 0.5  # Placeholder - needs multi-run evaluation

    # Check if patterns are learned
    if "learns" in expected:
        # Check if the learning was captured in the narrative
        scores["pattern_learning"] = 0.5  # Placeholder - needs trace analysis

    return scores


async def latency_evaluator(run: Run, example: Example) -> dict[str, float]:
    """Evaluate response time and efficiency."""
    if run.end_time and run.start_time:
        latency = (run.end_time - run.start_time).total_seconds()

        # Score based on latency thresholds
        if latency < 2:
            score = 1.0
        elif latency < 5:
            score = 0.8
        elif latency < 10:
            score = 0.6
        else:
            score = 0.3

        return {"latency_score": score, "response_time": latency}

    return {"latency_score": 0.0, "response_time": float("inf")}


async def consistency_evaluator(run: Run, example: Example) -> dict[str, float]:
    """Evaluate consistency across multiple runs of the same task."""
    # This would compare multiple runs of the same input
    # For now, return a placeholder
    return {"consistency": 0.8}


# Test Runner
async def run_probabilistic_tests():
    """Run probabilistic tests using LangSmith evaluation."""

    # Define the target function to test
    async def target_function(inputs: dict[str, Any]) -> dict[str, Any]:
        """Wrapper function for LangSmith evaluation."""
        task = inputs.get("task", "")
        context = inputs.get("context")

        agent = create_learning_agent()
        state = {"messages": [{"role": "user", "content": task}]}
        if context:
            state["current_context"] = {"context": context}
        result = await agent.ainvoke(state)
        return result

    # Run evaluations on each dataset
    datasets = create_test_datasets()

    results = {}
    for dataset_name, dataset in datasets.items():
        print(f"\nEvaluating {dataset_name} dataset...")

        eval_results = await evaluate(
            target_function,
            data=dataset.id,
            evaluators=[
                execution_evaluator,
                learning_evaluator,
                latency_evaluator,
                consistency_evaluator,
            ],
            experiment_prefix=f"learning-agent-{dataset_name}",
            max_concurrency=2,  # Limit concurrent evaluations
        )

        results[dataset_name] = eval_results

    return results


# Regression Testing with Real Traces
async def regression_test_from_traces():
    """Use successful production traces as regression tests."""

    # Query recent successful traces
    project_name = os.getenv("LANGSMITH_PROJECT", "learning-agent")

    # Get recent successful runs
    runs = client.list_runs(
        project_name=project_name,
        filter='eq(status, "success")',
        limit=10,
    )

    # Convert successful runs to test cases
    regression_dataset = client.create_dataset(
        "learning-agent-regression",
        description="Regression tests from successful production runs",
    )

    for run in runs:
        if run.inputs and run.outputs:
            client.create_example(
                dataset_id=regression_dataset.id,
                inputs=run.inputs,
                outputs=run.outputs,
                metadata={"source_run_id": str(run.id)},
            )

    print(f"Created regression dataset with {len(list(runs))} examples")

    return regression_dataset


# Anomaly Detection
async def detect_anomalies():
    """Detect anomalous behavior in recent runs."""

    project_name = os.getenv("LANGSMITH_PROJECT", "learning-agent")

    # Get recent runs
    recent_runs = list(
        client.list_runs(
            project_name=project_name,
            limit=100,
        )
    )

    # Analyze patterns
    latencies = []
    token_counts = []
    error_rates = []

    for run in recent_runs:
        if run.end_time and run.start_time:
            latency = (run.end_time - run.start_time).total_seconds()
            latencies.append(latency)

        if run.total_tokens:
            token_counts.append(run.total_tokens)

        if run.error:
            error_rates.append(1)
        else:
            error_rates.append(0)

    # Calculate statistics
    import statistics

    anomalies = []

    if latencies:
        mean_latency = statistics.mean(latencies)
        stdev_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0

        # Flag runs with latency > 2 standard deviations
        for run in recent_runs:
            if run.end_time and run.start_time:
                latency = (run.end_time - run.start_time).total_seconds()
                if abs(latency - mean_latency) > 2 * stdev_latency:
                    anomalies.append(
                        {
                            "run_id": run.id,
                            "type": "latency_anomaly",
                            "value": latency,
                            "threshold": mean_latency + 2 * stdev_latency,
                        }
                    )

    return anomalies


# A/B Testing
async def ab_test_configurations():
    """Run A/B tests between different configurations."""

    # Configuration A: Default settings
    agent_a = create_learning_agent()

    # Configuration B: Modified settings (e.g., different LLM temperature)
    import learning_agent.config as config

    original_temp = config.settings.llm_temperature
    config.settings.llm_temperature = 0.3
    agent_b = create_learning_agent()

    # Test dataset
    test_inputs = [
        {"task": "Write a haiku about coding"},
        {"task": "Explain recursion in simple terms"},
        {"task": "List 5 best practices for Python"},
    ]

    results_a = []
    results_b = []

    for input_data in test_inputs:
        # Run with config A
        state_a = {"messages": [{"role": "user", "content": input_data["task"]}]}
        result_a = await agent_a.ainvoke(state_a)
        results_a.append(result_a)

        # Run with config B
        state_b = {"messages": [{"role": "user", "content": input_data["task"]}]}
        result_b = await agent_b.ainvoke(state_b)
        results_b.append(result_b)

    # Compare results
    comparison = {
        "config_a_avg_latency": sum(r.get("duration", 0) for r in results_a) / len(results_a),
        "config_b_avg_latency": sum(r.get("duration", 0) for r in results_b) / len(results_b),
        "config_a_success_rate": sum(1 for r in results_a if r.get("status") == "completed")
        / len(results_a),
        "config_b_success_rate": sum(1 for r in results_b if r.get("status") == "completed")
        / len(results_b),
    }

    # Cleanup
    config.settings.llm_temperature = original_temp

    return comparison


if __name__ == "__main__":
    # Run all probabilistic tests
    asyncio.run(run_probabilistic_tests())
