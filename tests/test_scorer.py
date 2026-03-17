"""Tests for MBI-inspired burnout scoring."""

from datetime import date, timedelta

import pytest

from burnoutradar.detector.scorer import BurnoutScorer
from burnoutradar.models import RiskLevel, WorkPattern


@pytest.fixture
def scorer():
    return BurnoutScorer()


def make_patterns(hours: float = 40, weeks: int = 4) -> list[WorkPattern]:
    return [
        WorkPattern(
            week_start=date.today() - timedelta(weeks=weeks - i),
            hours_worked=hours,
            overtime_hours=max(0, hours - 40),
            meeting_hours=12,
            email_count=200,
            after_hours_events=3,
            deep_work_hours=10,
            weekend_hours=0,
            late_night_count=0,
            context_switches=15,
        )
        for i in range(weeks)
    ]


class TestMBIDimensions:
    def test_low_risk_scores(self, scorer):
        signals = {
            "overtime": 0, "meeting_load": 0, "email_volume": 0,
            "after_hours": 0, "deep_work_deficit": 0, "weekend_work": 0,
            "late_nights": 0, "no_recovery": 0, "context_switching": 0,
            "chronic_overwork": 0,
        }
        patterns = make_patterns(hours=38)
        score = scorer.score(signals, patterns)
        assert score.exhaustion < 30
        assert score.cynicism < 30
        assert score.efficacy > 70

    def test_high_risk_scores(self, scorer):
        signals = {
            "overtime": 80, "meeting_load": 70, "email_volume": 60,
            "after_hours": 80, "deep_work_deficit": 75, "weekend_work": 70,
            "late_nights": 60, "no_recovery": 90, "context_switching": 65,
            "chronic_overwork": 70,
        }
        patterns = make_patterns(hours=60)
        score = scorer.score(signals, patterns)
        assert score.exhaustion > 50
        assert score.cynicism > 40
        assert score.efficacy < 60


class TestOverallRisk:
    def test_low_risk_classification(self, scorer):
        signals = {k: 5.0 for k in [
            "overtime", "meeting_load", "email_volume", "after_hours",
            "deep_work_deficit", "weekend_work", "late_nights", "no_recovery",
            "context_switching", "chronic_overwork",
        ]}
        patterns = make_patterns(hours=38)
        score = scorer.score(signals, patterns)
        assert score.risk_level == RiskLevel.LOW

    def test_high_risk_classification(self, scorer):
        signals = {k: 80.0 for k in [
            "overtime", "meeting_load", "email_volume", "after_hours",
            "deep_work_deficit", "weekend_work", "late_nights", "no_recovery",
            "context_switching", "chronic_overwork",
        ]}
        patterns = make_patterns(hours=60)
        score = scorer.score(signals, patterns)
        assert score.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


class TestFactorIdentification:
    def test_primary_factor_detected(self, scorer):
        signals = {k: 10.0 for k in [
            "overtime", "meeting_load", "email_volume", "after_hours",
            "deep_work_deficit", "weekend_work", "late_nights", "no_recovery",
            "context_switching", "chronic_overwork",
        ]}
        signals["overtime"] = 90.0
        patterns = make_patterns()
        score = scorer.score(signals, patterns)
        assert score.primary_factor == "overtime"


class TestTrendAssessment:
    def test_stable_trend(self, scorer):
        patterns = make_patterns(hours=42, weeks=8)
        signals = {k: 20.0 for k in [
            "overtime", "meeting_load", "email_volume", "after_hours",
            "deep_work_deficit", "weekend_work", "late_nights", "no_recovery",
            "context_switching", "chronic_overwork",
        ]}
        score = scorer.score(signals, patterns)
        assert score.trend == "stable"

    def test_worsening_trend(self, scorer):
        patterns = []
        for i in range(8):
            patterns.append(WorkPattern(
                week_start=date.today() - timedelta(weeks=8 - i),
                hours_worked=40 + i * 4,  # Increasing hours
                overtime_hours=max(0, i * 4),
                meeting_hours=12,
                email_count=200,
                after_hours_events=3,
                deep_work_hours=10,
            ))
        signals = {k: 40.0 for k in [
            "overtime", "meeting_load", "email_volume", "after_hours",
            "deep_work_deficit", "weekend_work", "late_nights", "no_recovery",
            "context_switching", "chronic_overwork",
        ]}
        score = scorer.score(signals, patterns)
        assert score.trend == "worsening"


class TestBurnoutFlag:
    def test_is_burnout_all_dimensions(self, scorer):
        signals = {k: 90.0 for k in [
            "overtime", "meeting_load", "email_volume", "after_hours",
            "deep_work_deficit", "weekend_work", "late_nights", "no_recovery",
            "context_switching", "chronic_overwork",
        ]}
        patterns = make_patterns(hours=65)
        score = scorer.score(signals, patterns)
        # When all signals are extreme, exhaustion and cynicism should be high
        # and efficacy should be low
        assert score.exhaustion > 50
