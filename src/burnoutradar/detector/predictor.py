"""Burnout trajectory prediction.

Forecasts future burnout risk based on current patterns and trends.
Uses a simplified demand-resource imbalance model inspired by the
Conservation of Resources (COR) theory (Hobfoll, 1989).

Key principles:
- Resource loss spirals: losing resources makes it harder to gain new ones
- Overwork without recovery compounds non-linearly
- Early intervention is exponentially more effective
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from burnoutradar.models import BurnoutScore, RiskLevel, WorkPattern


class BurnoutPredictor:
    """Forecast burnout risk trajectory and identify inflection points.

    Uses a simplified COR-based model where sustained demand-resource
    imbalance accumulates stress that compounds over time.
    """

    # Model parameters
    RECOVERY_RATE = 0.05      # Natural recovery per week (5%)
    STRESS_DECAY = 0.90       # Stress retention between weeks (90%)
    OVERWORK_MULTIPLIER = 1.5 # Non-linear compounding for sustained overwork
    INTERVENTION_EFFICACY = {
        "low": 0.3,      # 30% risk reduction if low risk
        "moderate": 0.2,  # 20% if moderate
        "high": 0.1,      # 10% if high (harder to reverse)
        "critical": 0.05, # 5% if critical (very hard to reverse)
    }

    def predict_trajectory(
        self,
        current_score: BurnoutScore,
        patterns: list[WorkPattern],
        weeks_ahead: int = 8,
    ) -> list[dict]:
        """Predict burnout risk for the next N weeks.

        Assumes current work patterns continue unchanged.

        Args:
            current_score: Current burnout score.
            patterns: Recent work patterns (used for trend estimation).
            weeks_ahead: Number of weeks to forecast.

        Returns:
            List of weekly predictions with risk_score, risk_level,
            and cumulative_stress.
        """
        if not patterns:
            return []

        # Estimate weekly stress input from recent patterns
        avg_weekly_stress = self._estimate_weekly_stress(patterns)

        trajectory = []
        risk = current_score.overall_risk
        cumulative_stress = risk  # Start from current risk

        for week in range(1, weeks_ahead + 1):
            # Apply stress accumulation model
            # New stress = decayed old stress + new stress input
            cumulative_stress = (
                cumulative_stress * self.STRESS_DECAY
                + avg_weekly_stress
                - self.RECOVERY_RATE * 100
            )

            # Non-linear compounding when above moderate risk
            if cumulative_stress > 50:
                cumulative_stress *= 1 + (cumulative_stress - 50) / 500

            cumulative_stress = max(0, min(100, cumulative_stress))
            risk = cumulative_stress

            level = self._classify_risk(risk)
            trajectory.append({
                "week": week,
                "predicted_date": (
                    date.today() + timedelta(weeks=week)
                ).isoformat(),
                "risk_score": round(risk, 1),
                "risk_level": level.value,
                "cumulative_stress": round(cumulative_stress, 1),
            })

        return trajectory

    def predict_with_intervention(
        self,
        current_score: BurnoutScore,
        patterns: list[WorkPattern],
        intervention: str,
        weeks_ahead: int = 8,
    ) -> list[dict]:
        """Predict trajectory with an intervention applied.

        Interventions:
        - "reduce_hours": Cut overtime to 0, cap at 40h/week
        - "add_recovery": Add 1 PTO day per 2 weeks
        - "reduce_meetings": Cut meeting load by 30%
        - "protect_deep_work": Ensure 10h+ deep work per week

        Args:
            current_score: Current burnout score.
            patterns: Recent work patterns.
            intervention: Type of intervention to model.
            weeks_ahead: Forecast horizon.

        Returns:
            Adjusted trajectory predictions.
        """
        modified_patterns = self._apply_intervention(patterns, intervention)
        return self.predict_trajectory(
            current_score, modified_patterns, weeks_ahead
        )

    def weeks_to_burnout(
        self,
        current_score: BurnoutScore,
        patterns: list[WorkPattern],
        threshold: float = 70.0,
    ) -> int | None:
        """Estimate weeks until burnout risk reaches a threshold.

        Args:
            current_score: Current score.
            patterns: Recent patterns.
            threshold: Risk score threshold for "burnout" (default 70).

        Returns:
            Estimated weeks, or None if trajectory doesn't reach threshold
            within 52 weeks.
        """
        trajectory = self.predict_trajectory(
            current_score, patterns, weeks_ahead=52
        )

        for point in trajectory:
            if point["risk_score"] >= threshold:
                return point["week"]

        return None

    def find_inflection_point(
        self,
        current_score: BurnoutScore,
        patterns: list[WorkPattern],
    ) -> dict | None:
        """Find the point where risk acceleration changes significantly.

        The inflection point is where the rate of risk increase changes
        most dramatically, indicating when intervention becomes urgent.

        Returns:
            Dict with week, risk_score, and acceleration, or None.
        """
        trajectory = self.predict_trajectory(
            current_score, patterns, weeks_ahead=26
        )

        if len(trajectory) < 3:
            return None

        scores = [t["risk_score"] for t in trajectory]

        # Compute second derivative (acceleration)
        velocity = np.diff(scores)
        acceleration = np.diff(velocity)

        if len(acceleration) == 0:
            return None

        max_accel_idx = int(np.argmax(np.abs(acceleration)))
        # +2 because of two diff operations
        inflection_week = max_accel_idx + 2

        if inflection_week < len(trajectory):
            return {
                "week": trajectory[inflection_week]["week"],
                "predicted_date": trajectory[inflection_week]["predicted_date"],
                "risk_score": trajectory[inflection_week]["risk_score"],
                "acceleration": round(float(acceleration[max_accel_idx]), 2),
            }

        return None

    def _estimate_weekly_stress(self, patterns: list[WorkPattern]) -> float:
        """Estimate average weekly stress input from work patterns."""
        if not patterns:
            return 0.0

        stress_scores = []
        for p in patterns:
            # Overwork component
            overwork = max(0, p.hours_worked - 40) / 20.0 * 30  # 0-30

            # Meeting overload
            meeting_ratio = p.meeting_hours / max(p.hours_worked, 1)
            meetings = max(0, meeting_ratio - 0.3) / 0.3 * 20  # 0-20

            # Boundary erosion
            boundary = min(20, p.after_hours_events * 2)  # 0-20

            # Recovery deficit
            recovery = 10 if p.pto_days == 0 else 0  # 0-10

            # Weekend erosion
            weekend = min(10, p.weekend_hours * 2)  # 0-10

            total = overwork + meetings + boundary + recovery + weekend
            stress_scores.append(min(100, total))

        return float(np.mean(stress_scores))

    def _apply_intervention(
        self, patterns: list[WorkPattern], intervention: str
    ) -> list[WorkPattern]:
        """Create modified patterns reflecting an intervention."""
        modified = []
        for p in patterns:
            data = p.model_dump()

            if intervention == "reduce_hours":
                data["hours_worked"] = min(40, data["hours_worked"])
                data["overtime_hours"] = 0
                data["weekend_hours"] = 0

            elif intervention == "add_recovery":
                data["pto_days"] = max(data["pto_days"], 0.5)

            elif intervention == "reduce_meetings":
                data["meeting_hours"] *= 0.7

            elif intervention == "protect_deep_work":
                data["deep_work_hours"] = max(10, data["deep_work_hours"])
                data["context_switches"] = min(15, data["context_switches"])

            modified.append(WorkPattern.model_validate(data))

        return modified

    def _classify_risk(self, score: float) -> RiskLevel:
        if score >= 70:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
