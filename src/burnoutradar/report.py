"""Burnout report generation with rich terminal output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from burnoutradar.models import BurnoutScore, Employee, RiskLevel, TeamHealth


class BurnoutReportGenerator:
    """Generate formatted burnout analysis reports."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def print_individual_report(
        self, employee: Employee, score: BurnoutScore
    ) -> None:
        """Print individual burnout risk assessment."""
        risk_color = self._risk_color(score.risk_level)

        header = f"[bold]{employee.name}[/bold] ({employee.role})\n"
        header += f"Risk Level: [{risk_color}]{score.risk_level.label}[/{risk_color}] "
        header += f"({score.overall_risk:.0f}/100) | Trend: {score.trend}"

        self.console.print(Panel(
            header,
            title="BurnoutRadar Individual Report",
            border_style=risk_color,
        ))

        # MBI dimensions
        table = Table(show_header=True, header_style="bold")
        table.add_column("MBI Dimension", style="bold")
        table.add_column("Score", justify="center")
        table.add_column("Level", justify="center")
        table.add_column("Bar", min_width=20)

        for name, value, invert in [
            ("Exhaustion", score.exhaustion, False),
            ("Cynicism", score.cynicism, False),
            ("Efficacy", score.efficacy, True),
        ]:
            display_val = value if not invert else 100 - value
            color = self._severity_color(display_val)
            bar_len = int(value / 100 * 20)
            bar = "#" * bar_len + "-" * (20 - bar_len)
            level = self._mbi_level(value, invert)
            table.add_row(name, f"[{color}]{value:.0f}[/{color}]", level, f"[{color}]{bar}[/{color}]")

        self.console.print(table)

        # Contributing factors
        if score.primary_factor:
            self.console.print(
                f"\n[bold]Primary Risk Factor:[/bold] {score.primary_factor.replace('_', ' ').title()}"
            )
        if score.secondary_factors:
            secondary = ", ".join(
                f.replace("_", " ").title() for f in score.secondary_factors
            )
            self.console.print(f"[bold]Secondary Factors:[/bold] {secondary}")

    def print_team_report(self, health: TeamHealth) -> None:
        """Print team-level burnout health report."""
        color = self._team_risk_color(health.avg_risk_score)

        self.console.print(Panel(
            f"[bold]Team: {health.team_name}[/bold] | "
            f"Size: {health.team_size} | "
            f"Avg Risk: [{color}]{health.avg_risk_score:.0f}/100[/{color}] | "
            f"At Risk: {health.employees_at_risk}/{health.team_size}",
            title="BurnoutRadar Team Report",
            border_style=color,
        ))

        # Risk distribution
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Risk Level")
        table.add_column("Count", justify="center")
        table.add_column("Distribution", min_width=20)

        for level in ["low", "moderate", "high", "critical"]:
            count = health.risk_distribution.get(level, 0)
            pct = count / max(health.team_size, 1) * 100
            bar = "#" * int(pct / 5)
            color = self._risk_color(RiskLevel(level))
            table.add_row(
                f"[{color}]{level.title()}[/{color}]",
                str(count),
                f"[{color}]{bar}[/{color}] {pct:.0f}%",
            )

        self.console.print(table)

        # MBI dimensions
        self.console.print("\n[bold]Team MBI Dimensions (averages):[/bold]")
        dims = Table(show_header=False)
        dims.add_column("Dimension", style="bold")
        dims.add_column("Score")

        dims.add_row("Exhaustion", f"{health.avg_exhaustion:.0f}/100")
        dims.add_row("Cynicism", f"{health.avg_cynicism:.0f}/100")
        dims.add_row("Efficacy", f"{health.avg_efficacy:.0f}/100")
        self.console.print(dims)

        if health.top_risk_factors:
            factors = ", ".join(
                f.replace("_", " ").title() for f in health.top_risk_factors[:3]
            )
            self.console.print(f"\n[bold]Top Risk Factors:[/bold] {factors}")

    def print_trajectory(self, trajectory: list[dict]) -> None:
        """Print burnout risk trajectory forecast."""
        self.console.print("\n[bold]Risk Trajectory Forecast[/bold]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Week", justify="center")
        table.add_column("Date")
        table.add_column("Risk", justify="center")
        table.add_column("Level", justify="center")
        table.add_column("Trend", min_width=20)

        for point in trajectory:
            risk = point["risk_score"]
            color = self._severity_color(risk)
            bar_len = int(risk / 100 * 20)
            bar = "#" * bar_len
            table.add_row(
                f"W+{point['week']}",
                point["predicted_date"],
                f"[{color}]{risk:.0f}[/{color}]",
                point["risk_level"].title(),
                f"[{color}]{bar}[/{color}]",
            )

        self.console.print(table)

    def _risk_color(self, level: RiskLevel) -> str:
        return {
            RiskLevel.LOW: "green",
            RiskLevel.MODERATE: "yellow",
            RiskLevel.HIGH: "dark_orange",
            RiskLevel.CRITICAL: "red",
        }.get(level, "white")

    def _team_risk_color(self, score: float) -> str:
        if score < 30:
            return "green"
        elif score < 50:
            return "yellow"
        elif score < 70:
            return "dark_orange"
        else:
            return "red"

    def _severity_color(self, value: float) -> str:
        if value < 30:
            return "green"
        elif value < 50:
            return "yellow"
        elif value < 70:
            return "dark_orange"
        else:
            return "red"

    def _mbi_level(self, value: float, inverted: bool = False) -> str:
        if inverted:
            value = 100 - value
        if value < 30:
            return "[green]Low[/green]"
        elif value < 50:
            return "[yellow]Moderate[/yellow]"
        elif value < 70:
            return "[dark_orange]High[/dark_orange]"
        else:
            return "[red]Very High[/red]"
