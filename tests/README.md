# Testing Strategy for Learning Agent

## Overview

This project uses a **hybrid testing approach** combining traditional unit tests with LangSmith-based probabilistic testing. This is necessary because:

1. **Non-deterministic behavior**: LLMs produce varied outputs for the same input
2. **Complex interactions**: Multi-agent orchestration creates emergent behaviors
3. **Learning dynamics**: The system adapts over time based on experience
4. **Real-world validation**: Need to test with actual LLM calls, not mocks

## Testing Layers

### 1. Traditional Unit Tests (52% coverage)
- **Purpose**: Test deterministic components and data structures
- **Coverage**: Models, configuration, basic tool operations
- **Run with**: `make test`

### 2. LangSmith Probabilistic Testing
- **Purpose**: Test complex, non-deterministic behaviors
- **Coverage**: LLM interactions, learning patterns, orchestration flows
- **Run with**: `make langsmith-test`

### 3. Integration Testing via LangSmith Datasets
- **Purpose**: Validate end-to-end workflows
- **Datasets**:
  - `learning-agent-simple-tasks`: Basic execution flows
  - `learning-agent-complex-tasks`: Multi-step planning and execution
  - `learning-agent-adaptation`: Learning and memory capabilities
  - `learning-agent-regression`: Production trace regression tests

## LangSmith Testing Features

### Evaluation Metrics
1. **Execution Evaluator**: Task completion, content matching, numerical accuracy
2. **Learning Evaluator**: Memory retention, pattern learning
3. **Latency Evaluator**: Response time scoring
4. **Consistency Evaluator**: Cross-run stability

### Advanced Testing Capabilities

#### Regression Testing from Production
```python
# Automatically converts successful production traces to test cases
await regression_test_from_traces()
```

#### Anomaly Detection
```python
# Identifies outliers in latency, token usage, and error rates
anomalies = await detect_anomalies()
```

#### A/B Testing
```python
# Compare different configurations (temperature, models, etc.)
comparison = await ab_test_configurations()
```

## Why Probabilistic Testing?

### Traditional Testing Limitations

1. **Mocking LLMs loses real behavior**
   - Mock responses don't capture reasoning patterns
   - Can't test prompt engineering effectiveness
   - Miss edge cases in structured output parsing

2. **Complex State Spaces**
   - LangGraph creates dynamic execution paths
   - Parallel orchestration has race conditions
   - Learning creates feedback loops

3. **Emergent Properties**
   - System behavior emerges from component interactions
   - Memory retrieval affects planning
   - Pattern consolidation changes future executions

### LangSmith Advantages

1. **Real LLM Testing**
   - Test with actual model calls
   - Capture token usage and costs
   - Validate structured output schemas

2. **Trace Analysis**
   - Full execution visibility
   - Parent-child span relationships
   - Background task tracking

3. **Statistical Validation**
   - Score distributions across runs
   - Confidence intervals for metrics
   - Regression detection

4. **Production Feedback Loop**
   - Convert successful runs to test cases
   - Monitor for drift
   - Continuous improvement

## Test Execution

### Local Development
```bash
# Traditional tests
make test           # Run unit tests
make test-cov      # Generate coverage report

# LangSmith tests
make langsmith-test # Run probabilistic tests
make langsmith-eval # Run full evaluation suite
```

### CI/CD Pipeline
```yaml
- name: Unit Tests
  run: make test

- name: LangSmith Evaluation
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: make langsmith-eval
  env:
    LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
```

### Monitoring Production
```python
# Run periodically to detect drift
anomalies = await detect_anomalies()
if anomalies:
    alert_team(anomalies)
```

## Coverage Analysis

### Well-Tested Components (Traditional)
- ✅ Models and data structures (100%)
- ✅ Configuration loading (92%)
- ✅ Basic orchestration (75%)

### Components Requiring Probabilistic Testing
- 🔄 Supervisor LangGraph flows
- 🔄 Narrative learning and reflection
- 🔄 Pattern consolidation
- 🔄 Multi-agent coordination
- 🔄 Memory retrieval and ranking

## Best Practices

1. **Use traditional tests for deterministic logic**
   - Data validation
   - Configuration parsing
   - File operations

2. **Use LangSmith for LLM interactions**
   - Task planning
   - Execution flows
   - Learning behaviors

3. **Maintain test datasets**
   - Update with new use cases
   - Include edge cases from production
   - Version control dataset definitions

4. **Monitor test metrics**
   - Track success rates over time
   - Watch for latency regressions
   - Alert on anomalies

## Future Improvements

1. **Automated dataset generation** from production traces
2. **Semantic similarity** scoring for outputs
3. **Multi-turn conversation** testing
4. **Adversarial testing** for robustness
5. **Cost optimization** testing

## Conclusion

The combination of traditional and probabilistic testing provides comprehensive coverage for this complex LLM-based system. While traditional tests ensure basic correctness, LangSmith testing validates the emergent behaviors that make the system valuable.
