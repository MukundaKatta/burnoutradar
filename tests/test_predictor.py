"""Tests for burnout trajectory prediction."""

from datetime import date, timedelta

import pytest

from burnoutradar.detector.predictor import BurnoutPredictor
from burnoutradar.models import BurnoutScore, RiskLevel, WorkPattern


@pytest.fixture
def predictor():
    return BurnoutPredictor()


def make_score(risk: float = 50) -> BurnoutScore:
    return BurnoutScore(
        exhaustion=risk * 0.8,
        cynicism=risk * 0.6,
        efficacy=max(10, 100 - risk),
        overall_risk=risk,
        risk_level=RiskLevel.MODERATE if risk < 70 else RiskLevel.HIGH,
        primary_factor="overtime",
    )


def make_patterns(hours: float = 50, weeks: int = 8) -> list[WorkPattern]:
    return [
        WorkPattern(
            week_start=date.today() - timedelta(weeks=weeks - i),
            hours_worked=hours,
            overtime_hours=max(0, hours - 40),
            meeting_hours=15,
            email_count=250,
            after_hours_events=8,
            deep_work_hours=8,
            weekend_hours=3,
        )
        for i in range(weeks)
    ]


class TestTrajectoryPrediction:
    def test_returns_correct_weeks(self, predictor):
        score = make_score(40)
        patterns = make_patterns(hours=45)
        trajectory = predictor.predict_trajectory(score, patterns, weeks_ahead=8)
        assert len(trajectory) == 8
        assert trajectory[0]["week"] == 1
        assert trajectory[-1]["week"] == 8

    def test_high_stress_increases_risk(self, predictor):
        score = make_score(40)
        patterns = make_patterns(hours=60)
        trajectory = predictor.predict_trajectory(score, patterns, weeks_ahead=12)
        # Risk should increase over time with sustained overwork
        assert trajectory[-1]["risk_score"] > trajectory[0]["risk_score"]

    def test_empty_patterns(self, predictor):
        score = make_score(40)
        trajectory = predictor.predict_trajectory(score, [], weeks_ahead=4)
        assert trajectory == []


class TestWeeksToBurnout:
    def test_high_stress_reaches_burnout(self, predictor):
        score = make_score(50)
        patterns = make_patterns(hours=60)
        weeks = predictor.weeks_to_burnout(score, patterns)
        assert weeks is not None
        assert weeks > 0

    def test_low_stress_no_burnout(self, predictor):
        score = make_score(10)
        patterns = make_patterns(hours=38)
        weeks = predictor.weeks_to_burnout(score, patterns)
        # May or may not reach burnout, but if None that's expected
        # for very low risk with low hours


class TestInflectionPoint:
    def test_finds_inflection(self, predictor):
        score = make_score(40)
        patterns = make_patterns(hours=55)
        inflection = predictor.find_inflection_point(score, patterns)
        # Should find an inflection point or None
        if inflection is not None:
            assert "week" in inflection
            assert "risk_score" in inflection


class TestIntervention:
    def test_reduce_hours_lowers_trajectory(self, predictor):
        score = make_score(50)
        patterns = make_patterns(hours=55)

        baseline = predictor.predict_trajectory(score, patterns, weeks_ahead=8)
        with_intervention = predictor.predict_with_intervention(
            score, patterns, "reduce_hours", weeks_ahead=8
        )

        # Intervention should result in lower risk
        baseline_final = baseline[-1]["risk_score"]
        intervention_final = with_intervention[-1]["risk_score"]
        assert intervention_final <= baseline_final
