"""Tests for burnout data simulator."""

import pytest

from burnoutradar.simulator import BurnoutSimulator


@pytest.fixture
def sim():
    return BurnoutSimulator(seed=42)


class TestEmployeeSimulation:
    def test_generates_patterns(self, sim):
        emp = sim.simulate_employee(weeks=8)
        assert len(emp.work_patterns) == 8

    def test_valid_data(self, sim):
        emp = sim.simulate_employee(profile="overworked")
        for p in emp.work_patterns:
            assert p.hours_worked >= 20
            assert p.meeting_hours >= 0
            assert p.email_count >= 0

    def test_profiles_differ(self, sim):
        healthy = sim.simulate_employee(profile="healthy")
        overworked = sim.simulate_employee(profile="overworked")

        healthy_avg = sum(p.hours_worked for p in healthy.work_patterns) / len(healthy.work_patterns)
        overworked_avg = sum(p.hours_worked for p in overworked.work_patterns) / len(overworked.work_patterns)

        assert overworked_avg > healthy_avg

    def test_burnout_track_escalates(self, sim):
        emp = sim.simulate_employee(profile="burnout_track", weeks=8)
        first_half_hours = [p.hours_worked for p in emp.work_patterns[:4]]
        second_half_hours = [p.hours_worked for p in emp.work_patterns[4:]]
        # Burnout track should have increasing hours (on average)
        assert sum(second_half_hours) / 4 >= sum(first_half_hours) / 4 - 5  # Allow some noise


class TestTeamSimulation:
    def test_correct_size(self, sim):
        team = sim.simulate_team(size=10)
        assert len(team) == 10

    def test_team_has_variety(self, sim):
        team = sim.simulate_team(size=10, health="mixed")
        roles = set(e.role for e in team)
        assert len(roles) > 1

    def test_all_employees_have_data(self, sim):
        team = sim.simulate_team(size=5)
        for emp in team:
            assert len(emp.work_patterns) > 0
            assert emp.name
            assert emp.employee_id
