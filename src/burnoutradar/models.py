"""Pydantic models for BurnoutRadar."""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Burnout risk classification levels."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def label(self) -> str:
        return self.value.title()


class WorkPattern(BaseModel):
    """Weekly work pattern metrics for a single employee."""

    week_start: date
    hours_worked: float = Field(ge=0, description="Total hours worked in the week")
    overtime_hours: float = Field(ge=0, default=0, description="Hours beyond standard 40h")
    meeting_hours: float = Field(ge=0, default=0, description="Hours spent in meetings")
    email_count: int = Field(ge=0, default=0, description="Total emails sent")
    after_hours_events: int = Field(
        ge=0, default=0,
        description="Number of work events (emails, messages, commits) outside 9-6",
    )
    deep_work_hours: float = Field(
        ge=0, default=0,
        description="Uninterrupted blocks >= 2 hours for focused work",
    )
    weekend_hours: float = Field(ge=0, default=0, description="Hours worked on weekends")
    pto_days: float = Field(ge=0, default=0, description="PTO days taken this week")
    late_night_count: int = Field(
        ge=0, default=0,
        description="Number of work events after 9 PM",
    )
    context_switches: int = Field(
        ge=0, default=0,
        description="Number of project/task switches during the day",
    )


class BurnoutScore(BaseModel):
    """MBI-inspired burnout score with three dimensions.

    Based on the Maslach Burnout Inventory (Maslach & Jackson, 1981):
    - Emotional Exhaustion (EE): 0-54 scale (high = more exhaustion)
    - Depersonalization/Cynicism (DP): 0-30 scale (high = more cynicism)
    - Personal Accomplishment/Efficacy (PA): 0-48 scale (low = reduced efficacy)

    Our scoring normalizes to 0-100 for each dimension.
    """

    # MBI dimensions (0-100 normalized)
    exhaustion: float = Field(
        ge=0, le=100,
        description="Emotional exhaustion score (higher = more exhausted)",
    )
    cynicism: float = Field(
        ge=0, le=100,
        description="Depersonalization/cynicism score (higher = more cynical)",
    )
    efficacy: float = Field(
        ge=0, le=100,
        description="Professional efficacy score (higher = better, lower = burnout sign)",
    )

    # Composite
    overall_risk: float = Field(
        ge=0, le=100,
        description="Overall burnout risk score 0-100",
    )
    risk_level: RiskLevel
    trend: str = Field(
        default="stable",
        description="Trend direction: improving, stable, worsening",
    )

    # Contributing factors
    primary_factor: str = Field(
        default="",
        description="The main contributing factor to burnout risk",
    )
    secondary_factors: list[str] = Field(
        default_factory=list,
        description="Other contributing factors",
    )

    @property
    def is_burnout(self) -> bool:
        """True if scoring in burnout range on all three MBI dimensions."""
        return self.exhaustion >= 60 and self.cynicism >= 60 and self.efficacy <= 40


class Employee(BaseModel):
    """An employee being monitored for burnout risk."""

    employee_id: str
    name: str
    role: str = ""
    team: str = ""
    start_date: Optional[date] = None
    standard_hours: float = Field(default=40.0, description="Expected weekly hours")
    work_patterns: list[WorkPattern] = Field(default_factory=list)
    current_score: Optional[BurnoutScore] = None

    @property
    def tenure_days(self) -> int | None:
        if self.start_date:
            return (date.today() - self.start_date).days
        return None

    @property
    def weeks_tracked(self) -> int:
        return len(self.work_patterns)


class Recommendation(BaseModel):
    """An actionable burnout mitigation recommendation."""

    title: str
    description: str
    priority: str = Field(description="high, medium, or low")
    category: str = Field(description="workload, boundaries, recovery, social, meaning")
    target: str = Field(
        default="individual",
        description="individual, manager, or organization",
    )
    expected_impact: str = ""
    timeframe: str = ""


class TeamHealth(BaseModel):
    """Aggregated team-level burnout metrics."""

    team_name: str
    team_size: int
    avg_risk_score: float = Field(ge=0, le=100)
    max_risk_score: float = Field(ge=0, le=100)
    employees_at_risk: int = Field(ge=0, description="Count with risk >= high")
    avg_exhaustion: float = Field(ge=0, le=100)
    avg_cynicism: float = Field(ge=0, le=100)
    avg_efficacy: float = Field(ge=0, le=100)
    risk_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count per risk level: {low: N, moderate: N, high: N, critical: N}",
    )
    top_risk_factors: list[str] = Field(default_factory=list)
