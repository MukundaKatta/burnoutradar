"""Tests for work-life balance checker."""

from datetime import date, timedelta

import pytest

from burnoutradar.analyzer.balance import WorkLifeBalanceChecker
from burnoutradar.models import WorkPattern


@pytest.fixture
def checker():
    return WorkLifeBalanceChecker()


def make_patterns(
    after_hours: int = 2,
    weekend: float = 0,
    late_nights: int = 0,
    pto: float = 0,
    hours: float = 40,
    weeks: int = 4,
):
    return [
        WorkPattern(
            week_start=date.today() - timedelta(weeks=weeks - i),
            hours_worked=hours,
            after_hours_events=after_hours,
            weekend_hours=weekend,
            late_night_count=late_nights,
            pto_days=pto,
            meeting_hours=10,
            email_count=200,
        )
        for i in range(weeks)
    ]


class TestOverallBalance:
    def test_healthy_balance(self, checker):
        patterns = make_patterns(after_hours=1, weekend=0, late_nights=0, pto=0.2)
        result = checker.assess(patterns)
        assert result.overall_score > 60
        assert result.balance_label in ("healthy", "strained")

    def test_collapsed_balance(self, checker):
        patterns = make_patterns(
            after_hours=20, weekend=8, late_nights=6, pto=0, hours=55
        )
        result = checker.assess(patterns)
        assert result.overall_score < 30
        assert result.balance_label in ("eroded", "collapsed")

    def test_empty_patterns(self, checker):
        result = checker.assess([])
        assert result.overall_score == 100.0


class TestBoundaryScore:
    def test_good_boundaries(self, checker):
        patterns = make_patterns(after_hours=1, weekend=0)
        result = checker.assess(patterns)
        assert result.boundary_score > 60

    def test_poor_boundaries(self, checker):
        patterns = make_patterns(after_hours=15, weekend=6)
        result = checker.assess(patterns)
        assert result.boundary_score < 40


class TestRecoveryScore:
    def test_good_recovery(self, checker):
        patterns = make_patterns(weekend=0, hours=38, pto=0.3)
        result = checker.assess(patterns)
        assert result.recovery_score > 50

    def test_no_recovery(self, checker):
        patterns = make_patterns(weekend=6, hours=55, pto=0)
        result = checker.assess(patterns)
        assert result.recovery_score < 30


class TestDisconnectionScore:
    def test_good_disconnection(self, checker):
        patterns = make_patterns(late_nights=0, after_hours=1, weekend=0)
        result = checker.assess(patterns)
        assert result.disconnection_score > 60

    def test_poor_disconnection(self, checker):
        patterns = make_patterns(late_nights=5, after_hours=15, weekend=5)
        result = checker.assess(patterns)
        assert result.disconnection_score < 30


class TestRiskFactors:
    def test_identifies_risk_factors(self, checker):
        patterns = make_patterns(after_hours=15, weekend=5, late_nights=5, pto=0)
        result = checker.assess(patterns)
        assert len(result.risk_factors) > 0
