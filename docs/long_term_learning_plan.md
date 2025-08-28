# Long-Term Learning Support Plan

## Overview
A simple, reliable system for maintaining learning quality over time through validation, decay, generalization, and optimization.

## Core Principles
1. **Simplicity First**: Avoid complex ML models - use simple statistics and thresholds
2. **Fail Gracefully**: Bad learnings should fade, not break the system
3. **Continuous Validation**: Every application is a test
4. **Storage Efficiency**: Keep high-value learnings, prune the rest

## 1. Learning Lifecycle Management

### Learning States
```
NEW → VALIDATED → STABLE → DECLINING → ARCHIVED
 ↓        ↓          ↓         ↓           ↓
FAILED  UNSTABLE  OUTDATED  INVALID    DELETED
```

### State Transitions
- **NEW → VALIDATED**: After 3 successful applications (confidence > 0.7)
- **VALIDATED → STABLE**: After 10 successful applications (confidence > 0.9)
- **STABLE → DECLINING**: No use for 30 days OR 2 failures in last 5 attempts
- **ANY → FAILED**: 3 consecutive failures
- **DECLINING → ARCHIVED**: No use for 90 days
- **ARCHIVED → DELETED**: After 180 days

### Implementation Table Schema
```sql
ALTER TABLE memories ADD COLUMN lifecycle_state VARCHAR(20) DEFAULT 'NEW';
ALTER TABLE memories ADD COLUMN last_validated TIMESTAMP;
ALTER TABLE memories ADD COLUMN application_count INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN success_count INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN failure_count INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN consecutive_failures INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN last_failure_reason TEXT;

-- Index for lifecycle queries
CREATE INDEX idx_lifecycle ON memories(lifecycle_state, last_validated);
```

## 2. Confidence Decay Algorithm

### Simple Time-Based Decay
```python
def calculate_confidence(original_confidence: float, days_since_validation: int) -> float:
    """
    Simple exponential decay with floor at 0.3
    Confidence halves every 60 days without validation
    """
    decay_rate = 0.5 ** (days_since_validation / 60)
    decayed = original_confidence * decay_rate
    return max(0.3, decayed)  # Never below 30% to allow redemption
```

### Failure Impact
```python
def adjust_confidence_after_failure(current: float, severity: str) -> float:
    """
    Reduce confidence based on failure severity
    """
    penalties = {
        "minor": 0.9,    # Wrong but recoverable
        "major": 0.7,    # Caused errors
        "critical": 0.4  # Broke something
    }
    return current * penalties.get(severity, 0.8)
```

## 3. Learning Validation

### Continuous Validation Loop
```python
async def validate_applied_learning(learning_id: str, outcome: dict):
    """
    Called after every learning application
    """
    learning = await get_learning(learning_id)

    if outcome["success"]:
        learning.success_count += 1
        learning.consecutive_failures = 0
        learning.confidence = min(1.0, learning.confidence * 1.05)
        learning.last_validated = now()

        # State progression
        if learning.success_count >= 10 and learning.confidence > 0.9:
            learning.lifecycle_state = "STABLE"
        elif learning.success_count >= 3:
            learning.lifecycle_state = "VALIDATED"
    else:
        learning.failure_count += 1
        learning.consecutive_failures += 1
        learning.confidence = adjust_confidence_after_failure(
            learning.confidence,
            outcome["severity"]
        )
        learning.last_failure_reason = outcome["reason"]

        # State regression
        if learning.consecutive_failures >= 3:
            learning.lifecycle_state = "FAILED"
        elif learning.lifecycle_state == "STABLE":
            learning.lifecycle_state = "DECLINING"

    await save_learning(learning)
```

### Validation Triggers
- After each application of a learning
- During nightly maintenance job
- When conflicting learnings detected
- On user feedback/correction

## 4. Pattern Generalization

### Simple Generalization Rules
```python
def find_generalizable_patterns():
    """
    Find patterns that can be generalized across contexts
    Run weekly as background job
    """
    # Find similar successful learnings
    similar_groups = group_by_similarity(
        min_similarity=0.85,
        min_confidence=0.8,
        min_applications=5
    )

    for group in similar_groups:
        if len(group) >= 3:
            # Extract common elements
            common = extract_common_pattern(group)

            # Create generalized learning
            generalized = Learning(
                tactical=common.tactical,
                strategic=f"General principle: {common.principle}",
                confidence=min([l.confidence for l in group]) * 0.9,
                lifecycle_state="VALIDATED",
                is_generalization=True,
                source_learnings=[l.id for l in group]
            )

            # Archive specific versions
            for learning in group:
                learning.lifecycle_state = "ARCHIVED"
                learning.replaced_by = generalized.id
```

### Generalization Candidates
- Same operation succeeds in 3+ different contexts
- Pattern with >90% success rate across 10+ applications
- Strategic learnings that transcend specific tools
- Anti-patterns that appear in multiple failure modes

## 5. Storage Optimization

### Pruning Strategy
```python
async def optimize_storage():
    """
    Run monthly to clean up low-value learnings
    """
    # Delete old archived learnings
    await delete_where(
        lifecycle_state="ARCHIVED",
        last_validated < now() - timedelta(days=180)
    )

    # Merge near-duplicate learnings
    duplicates = find_duplicates(similarity_threshold=0.95)
    for group in duplicates:
        keep_best = max(group, key=lambda l: l.confidence * l.application_count)
        for learning in group:
            if learning != keep_best:
                await merge_into(learning, keep_best)

    # Compress old embeddings
    await compress_embeddings_older_than(days=90)

    # Archive low-value learnings
    await update_state_where(
        new_state="ARCHIVED",
        confidence < 0.5,
        application_count < 2,
        created_at < now() - timedelta(days=60)
    )
```

### Storage Tiers
1. **Hot (Active Memory)**: Recent, high-confidence, frequently used
2. **Warm (Database)**: Validated learnings, searchable
3. **Cold (Archive)**: Compressed, rarely accessed
4. **Deleted**: Pruned after 6 months of no use

## 6. Monitoring & Metrics

### Key Metrics to Track
```sql
-- Daily metrics view
CREATE VIEW learning_metrics AS
SELECT
    lifecycle_state,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    AVG(application_count) as avg_applications,
    AVG(success_count::float / NULLIF(application_count, 0)) as success_rate
FROM memories
GROUP BY lifecycle_state;

-- Learning health score
CREATE VIEW learning_health AS
SELECT
    (COUNT(*) FILTER (WHERE lifecycle_state IN ('VALIDATED', 'STABLE')))::float /
    NULLIF(COUNT(*), 0) as health_score,
    COUNT(*) FILTER (WHERE consecutive_failures >= 2) as at_risk,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as new_this_week
FROM memories;
```

### Alert Conditions
- Health score drops below 0.6
- More than 10% learnings in FAILED state
- Storage exceeds 1GB
- No new learnings in 7 days

## 7. Implementation Schedule

### Phase 1: Foundation (Week 1)
- Add lifecycle columns to database
- Implement confidence decay function
- Create validation hook in learning application

### Phase 2: Validation (Week 2)
- Build validation loop
- Add failure tracking
- Implement state transitions

### Phase 3: Optimization (Week 3)
- Create pruning job
- Build duplicate detection
- Implement storage tiers

### Phase 4: Generalization (Week 4)
- Pattern similarity detection
- Generalization rules
- Archival process

### Phase 5: Monitoring (Week 5)
- Create metrics views
- Build simple dashboard
- Set up alerts

## 8. Maintenance Jobs

### Daily (2 AM)
```python
async def daily_maintenance():
    # Update confidence decay
    await apply_confidence_decay()

    # Transition declining learnings
    await update_state_where(
        new_state="DECLINING",
        lifecycle_state="STABLE",
        last_validated < now() - timedelta(days=30)
    )

    # Clean up failures
    await delete_where(
        lifecycle_state="FAILED",
        created_at < now() - timedelta(days=7)
    )
```

### Weekly (Sunday 3 AM)
```python
async def weekly_maintenance():
    # Find generalizable patterns
    await find_generalizable_patterns()

    # Validate stable learnings
    await revalidate_stable_learnings()

    # Generate metrics report
    await generate_learning_report()
```

### Monthly (1st Sunday 4 AM)
```python
async def monthly_maintenance():
    # Storage optimization
    await optimize_storage()

    # Deep pattern analysis
    await analyze_learning_trends()

    # Backup before pruning
    await backup_learnings()

    # Major pruning
    await prune_old_learnings()
```

## 9. Failure Recovery

### When Learnings Go Wrong
1. **Immediate**: Mark as failed, reduce confidence
2. **Analysis**: Store failure reason and context
3. **Recovery**: Suggest alternative learnings
4. **Learning**: Create anti-pattern from failure

### Rollback Mechanism
```python
async def rollback_bad_learning(learning_id: str):
    learning = await get_learning(learning_id)

    # Restore previous version if exists
    if learning.previous_version_id:
        previous = await get_learning(learning.previous_version_id)
        previous.lifecycle_state = learning.lifecycle_state
        learning.lifecycle_state = "FAILED"

    # Notify about rollback
    await log_rollback(learning_id, reason)

    # Create anti-pattern
    await create_anti_pattern_from_failure(learning)
```

## 10. Success Criteria

### System Health Indicators
- **Learning Quality**: >70% learnings in VALIDATED or STABLE state
- **Application Success**: >80% success rate for applied learnings
- **Storage Efficiency**: <10MB per 1000 learnings
- **Query Performance**: <100ms for similarity search
- **Generalization Rate**: 5-10% learnings become generalized

### User Experience Goals
- No repeated mistakes after 3 occurrences
- Automatic improvement without intervention
- Relevant learnings found for >90% of tasks
- No performance degradation over time

## Simple Start Checklist

1. ✅ Add lifecycle_state column to database
2. ✅ Implement validation after each application
3. ✅ Add daily confidence decay job
4. ✅ Create monthly pruning job
5. ✅ Build simple metrics view
6. ✅ Test with 100 learnings
7. ✅ Monitor for 2 weeks
8. ✅ Adjust thresholds based on data

This plan prioritizes reliability over sophistication, using simple algorithms that are easy to debug and maintain.
