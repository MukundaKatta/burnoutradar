"""Tests for workload sustainability analysis."""

from datetime import date, timedelta

import pytest

from burnoutradar.analyzer.workload import WorkloadAnalyzer
from burnoutradar.models import WorkPattern


@pytest.fixture
def analyzer():
    return WorkloadAnalyzer()


def make_patterns(hours: float = 40, meetings: float = 10, deep: float = 12, weeks: int = 4):
    return [
        WorkPattern(
            week_start=date.today() - timedelta(weeks=weeks - i),
            hours_worked=hours,
            overtime_hours=max(0, hours - 40),
            meeting_hours=meetings,
            deep_work_hours=deep,
            email_count=200,
        )
        for i in range(weeks)
    ]


class TestSustainability:
    def test_normal_hours_sustainable(self, analyzer):
        patterns = make_patterns(hours=38)
        result = analyzer.analyze(patterns)
        assert result.is_sustainable is True
        assert result.sustainability_score > 60

    def test_excessive_hours_unsustainable(self, analyzer):
        patterns = make_patterns(hours=58)
        result = analyzer.analyze(patterns)
        assert result.is_sustainable is False
        assert result.intensity_label in ("heavy", "unsustainable")

    def test_empty_patterns(self, analyzer):
        result = analyzer.analyze([])
        assert result.is_sustainable is True
        assert result.sustainability_score == 100.0


class TestIntensityClassification:
    def test_light(self, analyzer):
        patterns = make_patterns(hours=35)
        result = analyzer.analyze(patterns)
        assert result.intensity_label == "light"

    def test_moderate(self, analyzer):
        patterns = make_patterns(hours=44)
        result = analyzer.analyze(patterns)
        assert result.intensity_label == "moderate"

    def test_heavy(self, analyzer):
        patterns = make_patterns(hours=52)
        result = analyzer.analyze(patterns)
        assert result.intensity_label in ("heavy", "unsustainable")


class TestComposition:
    def test_meeting_heavy_detected(self, analyzer):
        patterns = make_patterns(hours=45, meetings=30, deep=4)
        result = analyzer.analyze(patterns)
        assert result.meeting_to_deep_ratio > 3.0
        assert any("meeting" in r.lower() for r in result.recommendations)

    def test_good_composition(self, analyzer):
        patterns = make_patterns(hours=40, meetings=10, deep=15)
        result = analyzer.analyze(patterns)
        assert result.sustainability_score > 70


class TestRecommendations:
    def test_generates_recs_for_issues(self, analyzer):
        patterns = make_patterns(hours=56, meetings=25, deep=3)
        result = analyzer.analyze(patterns)
        assert len(result.recommendations) > 0

    def test_no_recs_for_healthy(self, analyzer):
        patterns = make_patterns(hours=38, meetings=8, deep=15)
        result = analyzer.analyze(patterns)
        # Healthy patterns should have no or few recommendations
        assert len(result.recommendations) <= 1
