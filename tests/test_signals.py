"""Tests for burnout signal detection."""

from datetime import date, timedelta

import pytest

from burnoutradar.detector.signals import BurnoutSignalDetector
from burnoutradar.models import WorkPattern


@pytest.fixture
def detector():
    return BurnoutSignalDetector()


def make_patterns(
    hours: float = 40,
    overtime: float = 0,
    meetings: float = 10,
    emails: int = 200,
    after_hours: int = 3,
    deep_work: float = 12,
    weekend: float = 0,
    late_nights: int = 0,
    pto: float = 0,
    switches: int = 15,
    weeks: int = 4,
) -> list[WorkPattern]:
    return [
        WorkPattern(
            week_start=date.today() - timedelta(weeks=weeks - i),
            hours_worked=hours,
            overtime_hours=overtime,
            meeting_hours=meetings,
            email_count=emails,
            after_hours_events=after_hours,
            deep_work_hours=deep_work,
            weekend_hours=weekend,
            pto_days=pto,
            late_night_count=late_nights,
            context_switches=switches,
        )
        for i in range(weeks)
    ]


class TestOvertimeSignal:
    def test_no_overtime(self, detector):
        patterns = make_patterns(overtime=0)
        signals = detector.analyze_signals(patterns)
        assert signals["overtime"] == 0

    def test_high_overtime(self, detector):
        patterns = make_patterns(hours=55, overtime=15)
        signals = detector.analyze_signals(patterns)
        assert signals["overtime"] > 50


class TestMeetingLoadSignal:
    def test_low_meeting_load(self, detector):
        patterns = make_patterns(hours=40, meetings=8)
        signals = detector.analyze_signals(patterns)
        assert signals["meeting_load"] == 0

    def test_high_meeting_load(self, detector):
        patterns = make_patterns(hours=40, meetings=28)
        signals = detector.analyze_signals(patterns)
        assert signals["meeting_load"] > 50


class TestAfterHoursSignal:
    def test_minimal_after_hours(self, detector):
        patterns = make_patterns(after_hours=2)
        signals = detector.analyze_signals(patterns)
        assert signals["after_hours"] == 0

    def test_excessive_after_hours(self, detector):
        patterns = make_patterns(after_hours=20)
        signals = detector.analyze_signals(patterns)
        assert signals["after_hours"] > 50


class TestDeepWorkDeficit:
    def test_adequate_deep_work(self, detector):
        patterns = make_patterns(deep_work=15)
        signals = detector.analyze_signals(patterns)
        assert signals["deep_work_deficit"] == 0

    def test_insufficient_deep_work(self, detector):
        patterns = make_patterns(deep_work=3)
        signals = detector.analyze_signals(patterns)
        assert signals["deep_work_deficit"] > 50


class TestChronicOverwork:
    def test_no_chronic_overwork(self, detector):
        patterns = make_patterns(hours=40, weeks=4)
        signals = detector.analyze_signals(patterns)
        assert signals["chronic_overwork"] == 0

    def test_chronic_overwork_detected(self, detector):
        patterns = make_patterns(hours=55, weeks=6)
        signals = detector.analyze_signals(patterns)
        assert signals["chronic_overwork"] > 0


class TestTopSignals:
    def test_returns_top_n(self, detector):
        patterns = make_patterns(hours=55, overtime=15, meetings=28, after_hours=18)
        signals = detector.analyze_signals(patterns)
        top = detector.get_top_signals(signals, n=3)
        assert len(top) <= 3
        # Should be sorted by severity
        if len(top) >= 2:
            assert top[0][1] >= top[1][1]

    def test_empty_patterns(self, detector):
        signals = detector.analyze_signals([])
        assert signals == {}
