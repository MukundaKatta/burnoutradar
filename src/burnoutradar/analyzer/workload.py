"""Workload sustainability analysis.

Determines whether current workload levels are sustainable based on
occupational health research.

Sustainable work thresholds based on:
- EU Working Time Directive: max 48h/week averaged over 17 weeks
- Kodz et al. (2003): >48h/week associated with health risks
- Virtanen et al. (2012): >55h/week increases stroke risk 33%

The analyzer evaluates both intensity and chronicity of workload.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from burnoutradar.models import WorkPattern


@dataclass
class WorkloadAssessment:
    """Result of workload sustainability analysis."""

    is_sustainable: bool
    sustainability_score: float  # 0-100, higher = more sustainable
    avg_weekly_hours: float
    peak_weekly_hours: float
    overwork_weeks_pct: float  # % of weeks exceeding threshold
    meeting_to_deep_ratio: float
    intensity_label: str  # "light", "moderate", "heavy", "unsustainable"
    recommendations: list[str]


class WorkloadAnalyzer:
    """Analyze whether current work levels are sustainable.

    Evaluates both the volume (hours) and composition (meetings vs
    deep work) of workload over time.
    """

    # Sustainability thresholds
    SUSTAINABLE_HOURS = 40.0       # Standard work week
    WARNING_HOURS = 48.0           # EU WTD threshold
    DANGER_HOURS = 55.0            # Health risk threshold
    MAX_MEETING_RATIO = 0.40       # Meetings should be <40% of time
    MIN_DEEP_WORK_RATIO = 0.25     # Deep work should be >25% of time

    # Overwork frequency thresholds
    OCCASIONAL_OVERWORK = 0.25     # <25% of weeks over threshold
    CHRONIC_OVERWORK = 0.50        # >50% of weeks over threshold

    def analyze(self, patterns: list[WorkPattern]) -> WorkloadAssessment:
        """Perform comprehensive workload sustainability analysis.

        Args:
            patterns: Weekly work patterns to analyze.

        Returns:
            WorkloadAssessment with sustainability metrics.
        """
        if not patterns:
            return WorkloadAssessment(
                is_sustainable=True,
                sustainability_score=100.0,
                avg_weekly_hours=0.0,
                peak_weekly_hours=0.0,
                overwork_weeks_pct=0.0,
                meeting_to_deep_ratio=0.0,
                intensity_label="light",
                recommendations=[],
            )

        hours = [p.hours_worked for p in patterns]
        avg_hours = float(np.mean(hours))
        peak_hours = float(np.max(hours))

        # Calculate overwork frequency
        overwork_weeks = sum(1 for h in hours if h > self.SUSTAINABLE_HOURS)
        overwork_pct = overwork_weeks / len(hours) * 100

        # Meeting vs deep work composition
        total_meeting = sum(p.meeting_hours for p in patterns)
        total_deep = sum(p.deep_work_hours for p in patterns)
        total_hours = sum(p.hours_worked for p in patterns)

        meeting_ratio = total_meeting / max(total_hours, 1)
        deep_ratio = total_deep / max(total_hours, 1)
        meeting_to_deep = meeting_ratio / max(deep_ratio, 0.01)

        # Compute sustainability score
        score = self._compute_sustainability_score(
            avg_hours, peak_hours, overwork_pct / 100,
            meeting_ratio, deep_ratio,
        )

        intensity = self._classify_intensity(avg_hours, overwork_pct / 100)
        is_sustainable = score >= 60 and avg_hours <= self.WARNING_HOURS

        recommendations = self._generate_recommendations(
            avg_hours, peak_hours, overwork_pct / 100,
            meeting_ratio, deep_ratio,
        )

        return WorkloadAssessment(
            is_sustainable=is_sustainable,
            sustainability_score=round(score, 1),
            avg_weekly_hours=round(avg_hours, 1),
            peak_weekly_hours=round(peak_hours, 1),
            overwork_weeks_pct=round(overwork_pct, 1),
            meeting_to_deep_ratio=round(meeting_to_deep, 2),
            intensity_label=intensity,
            recommendations=recommendations,
        )

    def _compute_sustainability_score(
        self,
        avg_hours: float,
        peak_hours: float,
        overwork_ratio: float,
        meeting_ratio: float,
        deep_ratio: float,
    ) -> float:
        """Compute overall sustainability score 0-100."""
        # Hours component (40 pts)
        if avg_hours <= self.SUSTAINABLE_HOURS:
            hours_score = 40.0
        elif avg_hours <= self.WARNING_HOURS:
            hours_score = 40 * (1 - (avg_hours - self.SUSTAINABLE_HOURS) /
                                (self.WARNING_HOURS - self.SUSTAINABLE_HOURS))
        else:
            hours_score = max(0, 10 * (1 - (avg_hours - self.WARNING_HOURS) /
                                       (self.DANGER_HOURS - self.WARNING_HOURS)))

        # Chronicity component (20 pts) - penalty for frequent overwork
        chronic_score = 20 * (1 - min(1.0, overwork_ratio / self.CHRONIC_OVERWORK))

        # Composition component (20 pts) - meeting/deep work balance
        if meeting_ratio <= self.MAX_MEETING_RATIO:
            meeting_score = 10.0
        else:
            meeting_score = max(0, 10 * (1 - (meeting_ratio - self.MAX_MEETING_RATIO) / 0.3))

        if deep_ratio >= self.MIN_DEEP_WORK_RATIO:
            deep_score = 10.0
        else:
            deep_score = 10 * deep_ratio / self.MIN_DEEP_WORK_RATIO

        # Peak hours penalty (20 pts)
        if peak_hours <= self.WARNING_HOURS:
            peak_score = 20.0
        elif peak_hours <= self.DANGER_HOURS:
            peak_score = 20 * (1 - (peak_hours - self.WARNING_HOURS) /
                                (self.DANGER_HOURS - self.WARNING_HOURS))
        else:
            peak_score = 0.0

        total = hours_score + chronic_score + meeting_score + deep_score + peak_score
        return float(np.clip(total, 0, 100))

    def _classify_intensity(
        self, avg_hours: float, overwork_ratio: float
    ) -> str:
        if avg_hours > self.DANGER_HOURS or overwork_ratio > self.CHRONIC_OVERWORK:
            return "unsustainable"
        elif avg_hours > self.WARNING_HOURS:
            return "heavy"
        elif avg_hours > self.SUSTAINABLE_HOURS:
            return "moderate"
        else:
            return "light"

    def _generate_recommendations(
        self,
        avg_hours: float,
        peak_hours: float,
        overwork_ratio: float,
        meeting_ratio: float,
        deep_ratio: float,
    ) -> list[str]:
        recs = []

        if avg_hours > self.WARNING_HOURS:
            recs.append(
                f"Average weekly hours ({avg_hours:.0f}h) exceed the 48h threshold "
                f"associated with increased health risks. Target a sustainable 40h week."
            )

        if peak_hours > self.DANGER_HOURS:
            recs.append(
                f"Peak week of {peak_hours:.0f}h is in the danger zone. "
                f"Weeks >55h are associated with 33% increased stroke risk."
            )

        if overwork_ratio > self.OCCASIONAL_OVERWORK:
            recs.append(
                f"Overwork occurs in {overwork_ratio*100:.0f}% of weeks. "
                f"This is chronic and compounds health risks over time."
            )

        if meeting_ratio > self.MAX_MEETING_RATIO:
            recs.append(
                f"Meetings consume {meeting_ratio*100:.0f}% of work time. "
                f"Audit recurring meetings and decline non-essential ones."
            )

        if deep_ratio < self.MIN_DEEP_WORK_RATIO:
            recs.append(
                f"Deep work is only {deep_ratio*100:.0f}% of time (target: 25%+). "
                f"Block 2-3 hour focus periods on your calendar."
            )

        return recs
