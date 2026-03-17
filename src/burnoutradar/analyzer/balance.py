"""Work-life balance assessment.

Evaluates boundary quality and recovery time using behavioral indicators:
- After-hours disconnection quality
- Weekend protection
- PTO usage patterns
- Recovery-to-demand ratio

References:
  - Sonnentag & Fritz (2007) Recovery Experience Questionnaire
  - Derks & Bakker (2014) Smartphone use and work-home interference
  - Meijman & Mulder (1998) Effort-Recovery model
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from burnoutradar.models import WorkPattern


@dataclass
class BalanceAssessment:
    """Result of work-life balance analysis."""

    overall_score: float          # 0-100, higher = better balance
    boundary_score: float         # 0-100, how well boundaries are maintained
    recovery_score: float         # 0-100, quality of recovery time
    disconnection_score: float    # 0-100, ability to disconnect
    pto_utilization_pct: float    # % of expected PTO actually used
    avg_after_hours_events: float
    weekend_free_pct: float       # % of weekends with no work
    balance_label: str            # "healthy", "strained", "eroded", "collapsed"
    risk_factors: list[str]


class WorkLifeBalanceChecker:
    """Assess work-life balance quality from behavioral patterns.

    Evaluates three core recovery mechanisms:
    1. Daily detachment (after-hours boundaries)
    2. Weekly recovery (weekend protection)
    3. Extended recovery (PTO usage)
    """

    # Expected PTO: ~10 days/year = ~0.2 days/week
    EXPECTED_PTO_PER_WEEK = 0.2

    # Thresholds
    GOOD_AFTER_HOURS = 3     # <= 3 events/week is good
    BAD_AFTER_HOURS = 10     # >= 10 is concerning
    GOOD_LATE_NIGHTS = 1     # <= 1 per week
    BAD_LATE_NIGHTS = 4      # >= 4 per week

    def assess(self, patterns: list[WorkPattern]) -> BalanceAssessment:
        """Assess work-life balance from work patterns.

        Args:
            patterns: Weekly work patterns to analyze.

        Returns:
            BalanceAssessment with detailed scoring.
        """
        if not patterns:
            return BalanceAssessment(
                overall_score=100.0, boundary_score=100.0,
                recovery_score=100.0, disconnection_score=100.0,
                pto_utilization_pct=100.0, avg_after_hours_events=0.0,
                weekend_free_pct=100.0, balance_label="healthy",
                risk_factors=[],
            )

        boundary = self._score_boundaries(patterns)
        recovery = self._score_recovery(patterns)
        disconnection = self._score_disconnection(patterns)

        overall = boundary * 0.35 + recovery * 0.35 + disconnection * 0.30
        label = self._classify_balance(overall)

        # PTO analysis
        total_pto = sum(p.pto_days for p in patterns)
        expected_pto = len(patterns) * self.EXPECTED_PTO_PER_WEEK
        pto_pct = (total_pto / max(expected_pto, 0.01)) * 100

        # After-hours
        avg_ah = float(np.mean([p.after_hours_events for p in patterns]))

        # Weekend-free weeks
        weekend_free = sum(1 for p in patterns if p.weekend_hours == 0)
        weekend_free_pct = (weekend_free / len(patterns)) * 100

        risk_factors = self._identify_risk_factors(patterns, boundary, recovery, disconnection)

        return BalanceAssessment(
            overall_score=round(overall, 1),
            boundary_score=round(boundary, 1),
            recovery_score=round(recovery, 1),
            disconnection_score=round(disconnection, 1),
            pto_utilization_pct=round(min(pto_pct, 100), 1),
            avg_after_hours_events=round(avg_ah, 1),
            weekend_free_pct=round(weekend_free_pct, 1),
            balance_label=label,
            risk_factors=risk_factors,
        )

    def _score_boundaries(self, patterns: list[WorkPattern]) -> float:
        """Score how well work boundaries are maintained (0-100)."""
        scores = []
        for p in patterns:
            # After-hours boundary
            ah_score = float(np.clip(
                (1 - (p.after_hours_events - self.GOOD_AFTER_HOURS)
                 / (self.BAD_AFTER_HOURS - self.GOOD_AFTER_HOURS)) * 50,
                0, 50,
            ))

            # Weekend boundary
            wk_score = 50.0 if p.weekend_hours == 0 else max(0, 50 - p.weekend_hours * 8)

            scores.append(ah_score + wk_score)

        return float(np.mean(scores))

    def _score_recovery(self, patterns: list[WorkPattern]) -> float:
        """Score recovery time quality (0-100).

        Based on Effort-Recovery model: adequate recovery prevents
        strain from accumulating.
        """
        scores = []
        for p in patterns:
            # PTO contribution (30 pts)
            pto_score = min(30, p.pto_days * 30)

            # Weekend freedom (40 pts)
            weekend_score = 40.0 if p.weekend_hours == 0 else max(0, 40 - p.weekend_hours * 10)

            # Reasonable hours allow evening recovery (30 pts)
            if p.hours_worked <= 40:
                hours_score = 30.0
            elif p.hours_worked <= 50:
                hours_score = 30 * (1 - (p.hours_worked - 40) / 10)
            else:
                hours_score = 0.0

            scores.append(pto_score + weekend_score + hours_score)

        return float(np.mean(scores))

    def _score_disconnection(self, patterns: list[WorkPattern]) -> float:
        """Score ability to psychologically disconnect from work (0-100).

        Based on Sonnentag's Recovery Experience model.
        """
        scores = []
        for p in patterns:
            # Late night work is the strongest anti-disconnection signal
            late_score = float(np.clip(
                (1 - (p.late_night_count - self.GOOD_LATE_NIGHTS)
                 / (self.BAD_LATE_NIGHTS - self.GOOD_LATE_NIGHTS)) * 40,
                0, 40,
            ))

            # After-hours email/messaging
            ah_score = float(np.clip(
                (1 - p.after_hours_events / 15) * 30,
                0, 30,
            ))

            # Weekend work prevents full disconnection
            wk_score = 30.0 if p.weekend_hours == 0 else max(0, 30 - p.weekend_hours * 6)

            scores.append(late_score + ah_score + wk_score)

        return float(np.mean(scores))

    def _classify_balance(self, score: float) -> str:
        if score >= 75:
            return "healthy"
        elif score >= 50:
            return "strained"
        elif score >= 25:
            return "eroded"
        else:
            return "collapsed"

    def _identify_risk_factors(
        self,
        patterns: list[WorkPattern],
        boundary: float,
        recovery: float,
        disconnection: float,
    ) -> list[str]:
        factors = []

        if boundary < 50:
            avg_ah = np.mean([p.after_hours_events for p in patterns])
            factors.append(
                f"Weak boundaries: avg {avg_ah:.0f} after-hours events/week"
            )

        if recovery < 50:
            total_pto = sum(p.pto_days for p in patterns)
            factors.append(
                f"Insufficient recovery: only {total_pto:.1f} PTO days "
                f"in {len(patterns)} weeks"
            )

        if disconnection < 50:
            avg_late = np.mean([p.late_night_count for p in patterns])
            factors.append(
                f"Poor disconnection: avg {avg_late:.0f} late-night work events/week"
            )

        avg_weekend = np.mean([p.weekend_hours for p in patterns])
        if avg_weekend > 2:
            factors.append(
                f"Weekend erosion: avg {avg_weekend:.1f}h worked on weekends"
            )

        return factors
