"""Learning lifecycle management for long-term support."""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from learning_agent.learning.vector_storage import VectorLearningStorage as VectorStorage


logger = logging.getLogger(__name__)


class LifecycleState(Enum):
    """Learning lifecycle states."""

    NEW = "NEW"
    VALIDATED = "VALIDATED"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"
    INVALID = "INVALID"


class FailureSeverity(Enum):
    """Severity levels for learning failures."""

    MINOR = "minor"  # Wrong but recoverable
    MAJOR = "major"  # Caused errors
    CRITICAL = "critical"  # Broke something


class LifecycleManager:
    """Manages learning lifecycle, validation, and confidence decay."""

    def __init__(self, vector_storage: VectorStorage):
        """Initialize lifecycle manager.

        Args:
            vector_storage: Vector storage instance for database operations
        """
        self.storage = vector_storage

    def calculate_confidence_decay(
        self, original_confidence: float, days_since_validation: int
    ) -> float:
        """Calculate confidence decay over time.

        Simple exponential decay with floor at 0.3.
        Confidence halves every 60 days without validation.

        Args:
            original_confidence: Original confidence score (0-1)
            days_since_validation: Days since last validation

        Returns:
            Decayed confidence score
        """
        if days_since_validation <= 0:
            return original_confidence

        decay_rate = 0.5 ** (days_since_validation / 60)
        decayed = original_confidence * decay_rate
        return float(max(0.3, decayed))  # Never below 30% to allow redemption

    def adjust_confidence_after_failure(
        self, current_confidence: float, severity: FailureSeverity
    ) -> float:
        """Reduce confidence based on failure severity.

        Args:
            current_confidence: Current confidence score
            severity: Severity of the failure

        Returns:
            Adjusted confidence score
        """
        penalties = {
            FailureSeverity.MINOR: 0.9,  # 10% reduction
            FailureSeverity.MAJOR: 0.7,  # 30% reduction
            FailureSeverity.CRITICAL: 0.4,  # 60% reduction
        }
        return current_confidence * penalties.get(severity, 0.8)

    async def validate_applied_learning(
        self,
        learning_id: str,
        success: bool,
        severity: FailureSeverity | None = None,
        failure_reason: str | None = None,
    ) -> None:
        """Validate a learning after application.

        Updates confidence, counters, and lifecycle state based on outcome.

        Args:
            learning_id: ID of the learning that was applied
            success: Whether the application was successful
            severity: Severity if failed (defaults to MINOR)
            failure_reason: Reason for failure if applicable
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return

        async with self.storage.pool.acquire() as conn:
            # Get the learning record
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", learning_id)

            if not row:
                logger.warning(f"Learning {learning_id} not found for validation")
                return

            # Initialize counters if needed
            application_count = row["application_count"] or 0
            success_count = row["success_count"] or 0
            failure_count = row["failure_count"] or 0
            consecutive_failures = row["consecutive_failures"] or 0
            confidence = row["confidence"] or 0.5

            application_count += 1

            if success:
                # Success path
                success_count += 1
                consecutive_failures = 0
                confidence = min(1.0, confidence * 1.05)
                last_validated = datetime.utcnow()

                # State progression
                if success_count >= 10 and confidence > 0.9:
                    lifecycle_state = LifecycleState.STABLE.value
                elif success_count >= 3:
                    lifecycle_state = LifecycleState.VALIDATED.value
                else:
                    lifecycle_state = row["lifecycle_state"] or LifecycleState.NEW.value

                await conn.execute(
                    """
                    UPDATE memories SET
                        application_count = $2,
                        success_count = $3,
                        consecutive_failures = $4,
                        confidence = $5,
                        last_validated = $6,
                        lifecycle_state = $7
                    WHERE id = $1
                    """,
                    learning_id,
                    application_count,
                    success_count,
                    consecutive_failures,
                    confidence,
                    last_validated,
                    lifecycle_state,
                )

                logger.info(
                    f"Learning {learning_id} validated successfully. "
                    f"State: {lifecycle_state}, Confidence: {confidence:.2f}"
                )

            else:
                # Failure path
                failure_count += 1
                consecutive_failures += 1
                severity = severity or FailureSeverity.MINOR
                confidence = self.adjust_confidence_after_failure(confidence, severity)

                # State regression
                current_state = row["lifecycle_state"] or LifecycleState.NEW.value
                if consecutive_failures >= 3:
                    lifecycle_state = LifecycleState.FAILED.value
                elif current_state == LifecycleState.STABLE.value:
                    lifecycle_state = LifecycleState.DECLINING.value
                else:
                    lifecycle_state = current_state

                await conn.execute(
                    """
                    UPDATE memories SET
                        application_count = $2,
                        failure_count = $3,
                        consecutive_failures = $4,
                        confidence = $5,
                        last_failure_reason = $6,
                        lifecycle_state = $7
                    WHERE id = $1
                    """,
                    learning_id,
                    application_count,
                    failure_count,
                    consecutive_failures,
                    confidence,
                    failure_reason,
                    lifecycle_state,
                )

                logger.warning(
                    f"Learning {learning_id} failed. "
                    f"State: {lifecycle_state}, Confidence: {confidence:.2f}, "
                    f"Consecutive failures: {consecutive_failures}"
                )

    async def apply_confidence_decay(self) -> int:
        """Apply confidence decay to all learnings.

        Should be run daily. Updates confidence based on time since validation.

        Returns:
            Number of learnings updated
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return 0

        async with self.storage.pool.acquire() as conn:
            # Get learnings that haven't been validated recently
            cutoff_date = datetime.utcnow() - timedelta(days=1)
            rows = await conn.fetch(
                """
                SELECT id, confidence, last_validated FROM memories
                WHERE last_validated < $1
                AND lifecycle_state = ANY($2)
                """,
                cutoff_date,
                [
                    LifecycleState.NEW.value,
                    LifecycleState.VALIDATED.value,
                    LifecycleState.STABLE.value,
                ],
            )

            updated_count = 0
            for row in rows:
                if row["last_validated"]:
                    days_since = (datetime.utcnow() - row["last_validated"]).days
                    old_confidence = row["confidence"] or 0.5
                    new_confidence = self.calculate_confidence_decay(old_confidence, days_since)

                    if old_confidence != new_confidence:
                        await conn.execute(
                            "UPDATE memories SET confidence = $2 WHERE id = $1",
                            row["id"],
                            new_confidence,
                        )
                        updated_count += 1
                        logger.debug(
                            f"Decayed confidence for {row['id']}: "
                            f"{old_confidence:.2f} -> {new_confidence:.2f}"
                        )

            logger.info(f"Applied confidence decay to {updated_count} learnings")
            return updated_count

    async def transition_declining_learnings(self) -> int:
        """Transition stable learnings to declining if not used.

        Should be run daily. Moves STABLE to DECLINING after 30 days of no use.

        Returns:
            Number of learnings transitioned
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return 0

        async with self.storage.pool.acquire() as conn:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            result = await conn.fetch(
                """
                UPDATE memories
                SET lifecycle_state = $1
                WHERE lifecycle_state = $2
                AND last_validated < $3
                RETURNING id
                """,
                LifecycleState.DECLINING.value,
                LifecycleState.STABLE.value,
                cutoff_date,
            )

            count = len(result)
            if count > 0:
                logger.info(f"Transitioned {count} learnings to DECLINING state")
            return count

    async def cleanup_failed_learnings(self) -> int:
        """Delete old failed learnings.

        Should be run daily. Removes FAILED learnings older than 7 days.

        Returns:
            Number of learnings deleted
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return 0

        async with self.storage.pool.acquire() as conn:
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            result = await conn.fetch(
                """
                DELETE FROM memories
                WHERE lifecycle_state = $1
                AND timestamp < $2
                RETURNING id
                """,
                LifecycleState.FAILED.value,
                cutoff_date,
            )

            count = len(result)
            if count > 0:
                logger.info(f"Deleted {count} old failed learnings")
            return count

    async def archive_old_learnings(self) -> int:
        """Archive learnings that haven't been used in 90 days.

        Should be run weekly.

        Returns:
            Number of learnings archived
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return 0

        async with self.storage.pool.acquire() as conn:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            result = await conn.fetch(
                """
                UPDATE memories
                SET lifecycle_state = $1
                WHERE lifecycle_state = $2
                AND last_validated < $3
                RETURNING id
                """,
                LifecycleState.ARCHIVED.value,
                LifecycleState.DECLINING.value,
                cutoff_date,
            )

            count = len(result)
            if count > 0:
                logger.info(f"Archived {count} old learnings")
            return count

    async def prune_archived_learnings(self) -> int:
        """Delete archived learnings older than 180 days.

        Should be run monthly.

        Returns:
            Number of learnings deleted
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return 0

        async with self.storage.pool.acquire() as conn:
            cutoff_date = datetime.utcnow() - timedelta(days=180)
            result = await conn.fetch(
                """
                DELETE FROM memories
                WHERE lifecycle_state = $1
                AND last_validated < $2
                RETURNING id
                """,
                LifecycleState.ARCHIVED.value,
                cutoff_date,
            )

            count = len(result)
            if count > 0:
                logger.info(f"Pruned {count} archived learnings")
            return count

    async def get_learning_metrics(self) -> dict[str, Any]:
        """Get metrics about learning health.

        Returns:
            Dictionary with learning metrics
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return {
                "state_counts": {},
                "health_score": 0.0,
                "at_risk_count": 0,
                "new_this_week": 0,
                "total_count": 0,
            }

        async with self.storage.pool.acquire() as conn:
            # Count by state
            state_counts = {}
            for state in LifecycleState:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM memories WHERE lifecycle_state = $1", state.value
                )
                state_counts[state.value] = result or 0

            # Calculate health score
            total = sum(state_counts.values())
            if total == 0:
                health_score = 1.0
            else:
                healthy = state_counts.get(LifecycleState.VALIDATED.value, 0) + state_counts.get(
                    LifecycleState.STABLE.value, 0
                )
                health_score = healthy / total

            # Count at-risk learnings
            at_risk = await conn.fetchval(
                "SELECT COUNT(*) FROM memories WHERE consecutive_failures >= 2"
            )

            # Count new this week
            week_ago = datetime.utcnow() - timedelta(days=7)
            new_this_week = await conn.fetchval(
                "SELECT COUNT(*) FROM memories WHERE timestamp > $1", week_ago
            )

            return {
                "state_counts": state_counts,
                "health_score": health_score,
                "at_risk_count": at_risk or 0,
                "new_this_week": new_this_week or 0,
                "total_count": total,
            }

    async def create_anti_pattern_from_failure(
        self, learning_id: str, failure_reason: str
    ) -> str | None:
        """Create an anti-pattern from a failed learning.

        Args:
            learning_id: ID of the failed learning
            failure_reason: Reason for the failure

        Returns:
            ID of created anti-pattern or None
        """
        if not self.storage.pool:
            logger.error("Storage pool not initialized")
            return None

        async with self.storage.pool.acquire() as conn:
            # Get the failed learning
            row = await conn.fetchrow(
                """
                SELECT task, tactical_learning
                FROM memories WHERE id = $1
                """,
                learning_id,
            )

            if not row:
                return None

            # Create anti-pattern
            anti_pattern = {
                "what_not_to_do": row["tactical_learning"],
                "why_it_fails": failure_reason,
                "original_approach": row["task"],
                "confidence": 0.9,  # High confidence in what NOT to do
            }

            # Store as new learning with anti-pattern type
            new_id = await self.storage.store_memory(
                {
                    "task": f"ANTI-PATTERN: {row['task']}",
                    "messages": [],
                    "learning": {
                        "tactical_learning": [],
                        "strategic_learning": [],
                        "meta_learning": [],
                        "anti_patterns": anti_pattern,
                        "confidence_scores": {"anti_pattern": 0.9},
                    },
                    "execution_analysis": {},
                }
            )

            logger.info(f"Created anti-pattern {new_id} from failed learning {learning_id}")
            return new_id
