"""Simulate realistic employee work pattern data for testing.

Generates work pattern data with configurable profiles:
- Healthy: sustainable hours, good boundaries
- Overworked: high hours, chronic overtime
- Meeting-heavy: excessive meeting load
- Boundary-eroded: constant after-hours work
- Burnout-track: escalating workload trajectory
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import numpy as np

from burnoutradar.models import Employee, WorkPattern


class BurnoutSimulator:
    """Generate realistic simulated employee and work pattern data."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = np.random.default_rng(seed)

    def simulate_employee(
        self,
        profile: str = "normal",
        weeks: int = 8,
        name: str | None = None,
        role: str = "Software Engineer",
        team: str = "Engineering",
    ) -> Employee:
        """Simulate a single employee with work pattern history.

        Args:
            profile: Work profile - "healthy", "normal", "overworked",
                     "meeting_heavy", "boundary_eroded", "burnout_track".
            weeks: Number of weeks of history.
            name: Employee name (auto-generated if None).
            role: Job role.
            team: Team name.

        Returns:
            Employee with populated work_patterns.
        """
        if name is None:
            first_names = ["Alice", "Bob", "Carol", "David", "Eve", "Frank",
                          "Grace", "Hank", "Ivy", "Jack"]
            last_names = ["Smith", "Chen", "Patel", "Kim", "Garcia", "Brown",
                         "Wilson", "Lee", "Taylor", "Singh"]
            name = f"{self.rng.choice(first_names)} {self.rng.choice(last_names)}"

        start_date = date.today() - timedelta(weeks=weeks)
        patterns = []

        for w in range(weeks):
            week_start = start_date + timedelta(weeks=w)
            pattern = self._generate_week(profile, w, weeks)
            pattern_data = pattern.copy()
            pattern_data["week_start"] = week_start
            patterns.append(WorkPattern.model_validate(pattern_data))

        return Employee(
            employee_id=str(uuid.uuid4())[:8],
            name=name,
            role=role,
            team=team,
            start_date=start_date - timedelta(days=365),
            work_patterns=patterns,
        )

    def simulate_team(
        self,
        size: int = 8,
        team_name: str = "Engineering",
        health: str = "mixed",
    ) -> list[Employee]:
        """Simulate a team of employees.

        Args:
            size: Number of team members.
            team_name: Team name.
            health: Team health profile - "healthy", "stressed", "mixed".

        Returns:
            List of Employee objects.
        """
        profiles = self._team_profile_mix(size, health)
        employees = []

        roles = ["Software Engineer", "Senior Engineer", "Tech Lead",
                "Product Manager", "Designer", "QA Engineer",
                "DevOps Engineer", "Data Scientist"]

        for i, profile in enumerate(profiles):
            role = roles[i % len(roles)]
            emp = self.simulate_employee(
                profile=profile, weeks=8, role=role, team=team_name,
            )
            employees.append(emp)

        return employees

    def _generate_week(
        self, profile: str, week_num: int, total_weeks: int
    ) -> dict:
        """Generate a single week's work pattern data."""
        params = self._profile_params(profile, week_num, total_weeks)

        hours = max(20, self.rng.normal(params["hours_mean"], params["hours_std"]))
        overtime = max(0, hours - 40)
        meeting_hours = max(0, self.rng.normal(
            params["meeting_mean"], params["meeting_std"]
        ))
        meeting_hours = min(meeting_hours, hours * 0.8)

        deep_work = max(0, self.rng.normal(
            params["deep_work_mean"], params["deep_work_std"]
        ))
        deep_work = min(deep_work, hours - meeting_hours)

        return {
            "week_start": date.today(),  # Placeholder
            "hours_worked": round(hours, 1),
            "overtime_hours": round(overtime, 1),
            "meeting_hours": round(meeting_hours, 1),
            "email_count": max(0, int(self.rng.normal(
                params["email_mean"], params["email_std"]
            ))),
            "after_hours_events": max(0, int(self.rng.normal(
                params["after_hours_mean"], params["after_hours_std"]
            ))),
            "deep_work_hours": round(deep_work, 1),
            "weekend_hours": max(0, round(
                self.rng.normal(params["weekend_mean"], params["weekend_std"]), 1
            )),
            "pto_days": params["pto_days"],
            "late_night_count": max(0, int(self.rng.normal(
                params["late_night_mean"], params["late_night_std"]
            ))),
            "context_switches": max(0, int(self.rng.normal(
                params["switches_mean"], params["switches_std"]
            ))),
        }

    def _profile_params(
        self, profile: str, week_num: int, total_weeks: int
    ) -> dict:
        """Get parameters for a given work profile."""
        profiles = {
            "healthy": {
                "hours_mean": 39, "hours_std": 2,
                "meeting_mean": 10, "meeting_std": 2,
                "deep_work_mean": 15, "deep_work_std": 3,
                "email_mean": 150, "email_std": 30,
                "after_hours_mean": 2, "after_hours_std": 1,
                "weekend_mean": 0, "weekend_std": 0.5,
                "late_night_mean": 0, "late_night_std": 0.5,
                "switches_mean": 12, "switches_std": 3,
                "pto_days": 0.2 if self.rng.random() > 0.7 else 0,
            },
            "normal": {
                "hours_mean": 43, "hours_std": 3,
                "meeting_mean": 14, "meeting_std": 3,
                "deep_work_mean": 12, "deep_work_std": 3,
                "email_mean": 220, "email_std": 40,
                "after_hours_mean": 5, "after_hours_std": 2,
                "weekend_mean": 1, "weekend_std": 1.5,
                "late_night_mean": 1, "late_night_std": 1,
                "switches_mean": 18, "switches_std": 4,
                "pto_days": 0.2 if self.rng.random() > 0.8 else 0,
            },
            "overworked": {
                "hours_mean": 55, "hours_std": 5,
                "meeting_mean": 18, "meeting_std": 3,
                "deep_work_mean": 8, "deep_work_std": 3,
                "email_mean": 350, "email_std": 50,
                "after_hours_mean": 12, "after_hours_std": 3,
                "weekend_mean": 6, "weekend_std": 2,
                "late_night_mean": 4, "late_night_std": 2,
                "switches_mean": 28, "switches_std": 5,
                "pto_days": 0,
            },
            "meeting_heavy": {
                "hours_mean": 45, "hours_std": 3,
                "meeting_mean": 28, "meeting_std": 4,
                "deep_work_mean": 4, "deep_work_std": 2,
                "email_mean": 300, "email_std": 40,
                "after_hours_mean": 6, "after_hours_std": 2,
                "weekend_mean": 2, "weekend_std": 1,
                "late_night_mean": 2, "late_night_std": 1,
                "switches_mean": 35, "switches_std": 5,
                "pto_days": 0,
            },
            "boundary_eroded": {
                "hours_mean": 48, "hours_std": 4,
                "meeting_mean": 16, "meeting_std": 3,
                "deep_work_mean": 10, "deep_work_std": 3,
                "email_mean": 280, "email_std": 50,
                "after_hours_mean": 18, "after_hours_std": 4,
                "weekend_mean": 5, "weekend_std": 2,
                "late_night_mean": 5, "late_night_std": 2,
                "switches_mean": 22, "switches_std": 4,
                "pto_days": 0,
            },
            "burnout_track": {
                "hours_mean": 42 + week_num * 2, "hours_std": 3,
                "meeting_mean": 14 + week_num, "meeting_std": 2,
                "deep_work_mean": max(3, 14 - week_num), "deep_work_std": 2,
                "email_mean": 200 + week_num * 20, "email_std": 30,
                "after_hours_mean": 4 + week_num, "after_hours_std": 2,
                "weekend_mean": week_num * 0.8, "weekend_std": 1,
                "late_night_mean": week_num * 0.5, "late_night_std": 1,
                "switches_mean": 15 + week_num * 2, "switches_std": 3,
                "pto_days": 0,
            },
        }
        return profiles.get(profile, profiles["normal"])

    def _team_profile_mix(self, size: int, health: str) -> list[str]:
        """Generate a mix of profiles for a team."""
        mixes = {
            "healthy": {"healthy": 0.5, "normal": 0.4, "overworked": 0.1},
            "stressed": {"normal": 0.2, "overworked": 0.3, "meeting_heavy": 0.2,
                         "boundary_eroded": 0.2, "burnout_track": 0.1},
            "mixed": {"healthy": 0.25, "normal": 0.35, "overworked": 0.15,
                      "meeting_heavy": 0.15, "boundary_eroded": 0.1},
        }

        mix = mixes.get(health, mixes["mixed"])
        profiles = []
        for profile, ratio in mix.items():
            count = max(0, round(size * ratio))
            profiles.extend([profile] * count)

        # Pad or trim to exact size
        while len(profiles) < size:
            profiles.append("normal")
        profiles = profiles[:size]

        self.rng.shuffle(profiles)
        return list(profiles)
