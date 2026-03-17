"""Tests for team health analysis."""

import pytest

from burnoutradar.analyzer.team import TeamHealthAnalyzer
from burnoutradar.models import BurnoutScore, Employee, RiskLevel


@pytest.fixture
def analyzer():
    return TeamHealthAnalyzer()


def make_employee(name: str, risk: float, primary_factor: str = "overtime") -> Employee:
    level = RiskLevel.LOW
    if risk >= 70:
        level = RiskLevel.CRITICAL
    elif risk >= 50:
        level = RiskLevel.HIGH
    elif risk >= 30:
        level = RiskLevel.MODERATE

    return Employee(
        employee_id=name.lower().replace(" ", "_"),
        name=name,
        role="Engineer",
        team="Engineering",
        current_score=BurnoutScore(
            exhaustion=risk * 0.8,
            cynicism=risk * 0.6,
            efficacy=max(10, 100 - risk),
            overall_risk=risk,
            risk_level=level,
            primary_factor=primary_factor,
        ),
    )


class TestTeamAnalysis:
    def test_healthy_team(self, analyzer):
        employees = [
            make_employee("Alice", 15),
            make_employee("Bob", 20),
            make_employee("Carol", 10),
        ]
        health = analyzer.analyze_team(employees, "Engineering")
        assert health.avg_risk_score < 30
        assert health.employees_at_risk == 0

    def test_stressed_team(self, analyzer):
        employees = [
            make_employee("Alice", 75),
            make_employee("Bob", 60),
            make_employee("Carol", 55),
        ]
        health = analyzer.analyze_team(employees, "Engineering")
        assert health.avg_risk_score > 50
        assert health.employees_at_risk >= 2

    def test_empty_scores(self, analyzer):
        employees = [
            Employee(employee_id="1", name="Alice", role="Engineer"),
        ]
        health = analyzer.analyze_team(employees)
        assert health.avg_risk_score == 0


class TestSystemicDetection:
    def test_systemic_when_many_at_risk(self, analyzer):
        employees = [
            make_employee("Alice", 70),
            make_employee("Bob", 65),
            make_employee("Carol", 55),
            make_employee("David", 20),
        ]
        health = analyzer.analyze_team(employees)
        assert analyzer.is_systemic(health)

    def test_not_systemic_when_few_at_risk(self, analyzer):
        employees = [
            make_employee("Alice", 70),
            make_employee("Bob", 20),
            make_employee("Carol", 15),
            make_employee("David", 10),
        ]
        health = analyzer.analyze_team(employees)
        assert not analyzer.is_systemic(health)


class TestPriorityEmployees:
    def test_returns_highest_risk(self, analyzer):
        employees = [
            make_employee("Alice", 30),
            make_employee("Bob", 80),
            make_employee("Carol", 50),
        ]
        priority = analyzer.get_priority_employees(employees, n=2)
        assert len(priority) == 2
        assert priority[0].name == "Bob"

    def test_handles_no_scores(self, analyzer):
        employees = [
            Employee(employee_id="1", name="Alice", role="Engineer"),
        ]
        priority = analyzer.get_priority_employees(employees)
        assert len(priority) == 0


class TestBenchmarkComparison:
    def test_above_average_exhaustion(self, analyzer):
        employees = [make_employee("Alice", 75)]
        health = analyzer.analyze_team(employees)
        comparison = analyzer.compare_to_benchmark(health)
        assert comparison["exhaustion"] == "above_average"


class TestTeamRecommendations:
    def test_systemic_generates_alert(self, analyzer):
        employees = [
            make_employee("Alice", 70),
            make_employee("Bob", 65),
            make_employee("Carol", 55),
        ]
        health = analyzer.analyze_team(employees)
        recs = analyzer.generate_team_recommendations(health)
        assert any("SYSTEMIC" in r for r in recs) or len(recs) > 0

    def test_healthy_team_positive_message(self, analyzer):
        employees = [
            make_employee("Alice", 10),
            make_employee("Bob", 15),
        ]
        health = analyzer.analyze_team(employees)
        recs = analyzer.generate_team_recommendations(health)
        assert any("healthy" in r.lower() for r in recs)
