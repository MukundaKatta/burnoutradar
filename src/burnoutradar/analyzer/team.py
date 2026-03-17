"""Team-level burnout risk aggregation and analysis.

Analyzes burnout risk at the team level to identify:
- Systemic workload issues vs individual patterns
- Team-wide risk distribution
- Collective burnout indicators
- Management action priorities

References:
  - Bakker et al. (2006) Crossover of burnout in work teams
  - Gonzalez-Roma et al. (2006) Burnout and work engagement in teams
  - Taris et al. (2005) Inequality among workers and teams
"""

from __future__ import annotations

import numpy as np

from burnoutradar.models import (
    BurnoutScore,
    Employee,
    RiskLevel,
    TeamHealth,
)


class TeamHealthAnalyzer:
    """Aggregate individual burnout signals into team-level risk assessment.

    Identifies whether burnout risk is systemic (team-wide patterns)
    or individual (isolated cases needing targeted support).
    """

    # Team risk thresholds
    TEAM_RISK_THRESHOLD = 0.30  # >30% of team at high risk = systemic issue
    CRITICAL_MASS = 0.50        # >50% = critical team-level intervention needed

    def analyze_team(
        self, employees: list[Employee], team_name: str = "Default"
    ) -> TeamHealth:
        """Compute team-level burnout health metrics.

        Args:
            employees: List of employees with current burnout scores.
            team_name: Name of the team.

        Returns:
            TeamHealth with aggregated metrics.
        """
        scored = [e for e in employees if e.current_score is not None]
        if not scored:
            return TeamHealth(
                team_name=team_name,
                team_size=len(employees),
                avg_risk_score=0,
                max_risk_score=0,
                employees_at_risk=0,
                avg_exhaustion=0,
                avg_cynicism=0,
                avg_efficacy=100,
                risk_distribution={"low": len(employees), "moderate": 0, "high": 0, "critical": 0},
                top_risk_factors=[],
            )

        scores = [e.current_score for e in scored]
        risks = [s.overall_risk for s in scores]

        # Risk distribution
        distribution = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
        for s in scores:
            distribution[s.risk_level.value] += 1

        # Employees at risk (high or critical)
        at_risk = distribution.get("high", 0) + distribution.get("critical", 0)

        # Aggregate MBI dimensions
        avg_exhaustion = float(np.mean([s.exhaustion for s in scores]))
        avg_cynicism = float(np.mean([s.cynicism for s in scores]))
        avg_efficacy = float(np.mean([s.efficacy for s in scores]))

        # Identify top risk factors across the team
        factor_counts: dict[str, int] = {}
        for s in scores:
            if s.primary_factor:
                factor_counts[s.primary_factor] = factor_counts.get(s.primary_factor, 0) + 1
            for f in s.secondary_factors:
                factor_counts[f] = factor_counts.get(f, 0) + 1

        top_factors = sorted(
            factor_counts.items(), key=lambda x: x[1], reverse=True
        )
        top_factor_names = [name for name, _ in top_factors[:5]]

        return TeamHealth(
            team_name=team_name,
            team_size=len(employees),
            avg_risk_score=round(float(np.mean(risks)), 1),
            max_risk_score=round(float(np.max(risks)), 1),
            employees_at_risk=at_risk,
            avg_exhaustion=round(avg_exhaustion, 1),
            avg_cynicism=round(avg_cynicism, 1),
            avg_efficacy=round(avg_efficacy, 1),
            risk_distribution=distribution,
            top_risk_factors=top_factor_names,
        )

    def is_systemic(self, health: TeamHealth) -> bool:
        """Determine if burnout risk is a systemic team issue.

        Systemic burnout occurs when a significant portion of the team
        shows elevated risk, indicating organizational/process problems
        rather than individual coping issues.
        """
        if health.team_size == 0:
            return False

        at_risk_ratio = health.employees_at_risk / health.team_size
        return at_risk_ratio >= self.TEAM_RISK_THRESHOLD

    def compare_to_benchmark(
        self, health: TeamHealth
    ) -> dict[str, str]:
        """Compare team metrics to organizational benchmarks.

        Uses industry averages as baseline:
        - Avg exhaustion: 35-40 (moderate)
        - Avg cynicism: 25-30 (moderate)
        - Avg efficacy: 65-70 (moderate)
        - % at risk: 15-20%

        Returns:
            Dict mapping metric to "above_average", "average", "below_average".
        """
        benchmarks = {
            "exhaustion": (35, 45),      # average range
            "cynicism": (25, 35),
            "efficacy": (60, 75),
            "risk_score": (25, 40),
        }

        results = {}

        for metric, (low, high) in benchmarks.items():
            if metric == "exhaustion":
                val = health.avg_exhaustion
                if val > high:
                    results[metric] = "above_average"
                elif val < low:
                    results[metric] = "below_average"
                else:
                    results[metric] = "average"
            elif metric == "cynicism":
                val = health.avg_cynicism
                if val > high:
                    results[metric] = "above_average"
                elif val < low:
                    results[metric] = "below_average"
                else:
                    results[metric] = "average"
            elif metric == "efficacy":
                val = health.avg_efficacy
                if val < low:
                    results[metric] = "below_average"
                elif val > high:
                    results[metric] = "above_average"
                else:
                    results[metric] = "average"
            elif metric == "risk_score":
                val = health.avg_risk_score
                if val > high:
                    results[metric] = "above_average"
                elif val < low:
                    results[metric] = "below_average"
                else:
                    results[metric] = "average"

        return results

    def get_priority_employees(
        self, employees: list[Employee], n: int = 3
    ) -> list[Employee]:
        """Get the N employees with highest burnout risk for priority intervention.

        Args:
            employees: All team members.
            n: Number of top-priority employees.

        Returns:
            List of employees sorted by risk, highest first.
        """
        scored = [e for e in employees if e.current_score is not None]
        ranked = sorted(
            scored,
            key=lambda e: e.current_score.overall_risk,
            reverse=True,
        )
        return ranked[:n]

    def generate_team_recommendations(
        self, health: TeamHealth
    ) -> list[str]:
        """Generate team-level recommendations based on aggregate metrics.

        Returns:
            List of actionable recommendations for management.
        """
        recs = []

        if self.is_systemic(health):
            recs.append(
                f"SYSTEMIC ALERT: {health.employees_at_risk}/{health.team_size} "
                f"team members are at high or critical burnout risk. This indicates "
                f"organizational/process issues, not just individual coping problems."
            )

        if health.avg_exhaustion > 50:
            recs.append(
                "High team exhaustion detected. Consider: reducing meeting load, "
                "implementing no-meeting days, or redistributing workload."
            )

        if health.avg_cynicism > 40:
            recs.append(
                "Elevated team cynicism. Focus on: reconnecting work to mission, "
                "improving team autonomy, and addressing process frustrations."
            )

        if health.avg_efficacy < 50:
            recs.append(
                "Low team efficacy. Consider: providing clearer goals, "
                "celebrating wins, ensuring adequate training and resources."
            )

        if health.top_risk_factors:
            top = ", ".join(health.top_risk_factors[:3])
            recs.append(
                f"Top risk factors across the team: {top}. "
                f"Address these at the organizational level."
            )

        if not recs:
            recs.append("Team burnout risk is within healthy range. Maintain current practices.")

        return recs
