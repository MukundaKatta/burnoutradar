"""BurnoutRadar CLI interface."""

from __future__ import annotations

import click
from rich.console import Console

from burnoutradar.analyzer.balance import WorkLifeBalanceChecker
from burnoutradar.analyzer.team import TeamHealthAnalyzer
from burnoutradar.analyzer.workload import WorkloadAnalyzer
from burnoutradar.detector.predictor import BurnoutPredictor
from burnoutradar.detector.scorer import BurnoutScorer
from burnoutradar.detector.signals import BurnoutSignalDetector
from burnoutradar.report import BurnoutReportGenerator
from burnoutradar.simulator import BurnoutSimulator

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """BurnoutRadar - AI Burnout Predictor."""
    pass


@cli.command()
@click.option("--profile", type=click.Choice([
    "healthy", "normal", "overworked", "meeting_heavy",
    "boundary_eroded", "burnout_track",
]), default="normal", help="Work profile to simulate")
@click.option("--weeks", type=int, default=8, help="Weeks of history")
@click.option("--seed", type=int, default=42, help="Random seed")
def analyze(profile: str, weeks: int, seed: int) -> None:
    """Analyze burnout risk for a simulated employee."""
    sim = BurnoutSimulator(seed=seed)
    employee = sim.simulate_employee(profile=profile, weeks=weeks)

    detector = BurnoutSignalDetector()
    signals = detector.analyze_signals(employee.work_patterns)

    scorer = BurnoutScorer()
    score = scorer.score(signals, employee.work_patterns)
    employee.current_score = score

    report = BurnoutReportGenerator(console)
    report.print_individual_report(employee, score)

    # Workload analysis
    workload_analyzer = WorkloadAnalyzer()
    assessment = workload_analyzer.analyze(employee.work_patterns)
    console.print(f"\n[bold]Workload:[/bold] {assessment.intensity_label.title()} "
                  f"({assessment.avg_weekly_hours:.0f}h avg, "
                  f"sustainability: {assessment.sustainability_score:.0f}/100)")

    # Balance analysis
    balance_checker = WorkLifeBalanceChecker()
    balance = balance_checker.assess(employee.work_patterns)
    console.print(f"[bold]Work-Life Balance:[/bold] {balance.balance_label.title()} "
                  f"({balance.overall_score:.0f}/100)")

    # Top signals
    top = detector.get_top_signals(signals)
    if top:
        console.print("\n[bold]Top Burnout Signals:[/bold]")
        for name, severity in top:
            color = "red" if severity > 50 else "yellow" if severity > 25 else "green"
            console.print(f"  [{color}]{name.replace('_', ' ').title()}: {severity:.0f}/100[/{color}]")


@cli.command(name="team-report")
@click.option("--size", type=int, default=8, help="Team size")
@click.option("--health", type=click.Choice(["healthy", "stressed", "mixed"]),
              default="mixed", help="Team health profile")
@click.option("--seed", type=int, default=42, help="Random seed")
def team_report(size: int, health: str, seed: int) -> None:
    """Generate a team-level burnout health report."""
    sim = BurnoutSimulator(seed=seed)
    employees = sim.simulate_team(size=size, health=health)

    detector = BurnoutSignalDetector()
    scorer = BurnoutScorer()

    for emp in employees:
        signals = detector.analyze_signals(emp.work_patterns)
        score = scorer.score(signals, emp.work_patterns)
        emp.current_score = score

    analyzer = TeamHealthAnalyzer()
    team_health = analyzer.analyze_team(employees, team_name="Engineering")

    report = BurnoutReportGenerator(console)
    report.print_team_report(team_health)

    # Team recommendations
    recs = analyzer.generate_team_recommendations(team_health)
    console.print("\n[bold]Recommendations:[/bold]")
    for r in recs:
        console.print(f"  - {r}")

    # Priority employees
    priority = analyzer.get_priority_employees(employees)
    if priority:
        console.print("\n[bold]Priority Interventions:[/bold]")
        for emp in priority:
            score = emp.current_score
            color = "red" if score.overall_risk > 50 else "yellow"
            console.print(
                f"  [{color}]{emp.name} ({emp.role}): "
                f"Risk {score.overall_risk:.0f}/100[/{color}]"
            )


@cli.command()
@click.option("--profile", default="burnout_track", help="Profile to predict")
@click.option("--weeks", type=int, default=12, help="Weeks to forecast")
@click.option("--seed", type=int, default=42, help="Random seed")
def predict(profile: str, weeks: int, seed: int) -> None:
    """Predict burnout trajectory for the next N weeks."""
    sim = BurnoutSimulator(seed=seed)
    employee = sim.simulate_employee(profile=profile, weeks=8)

    detector = BurnoutSignalDetector()
    signals = detector.analyze_signals(employee.work_patterns)

    scorer = BurnoutScorer()
    score = scorer.score(signals, employee.work_patterns)

    predictor = BurnoutPredictor()
    trajectory = predictor.predict_trajectory(score, employee.work_patterns, weeks)

    report = BurnoutReportGenerator(console)
    report.print_trajectory(trajectory)

    # Inflection point
    inflection = predictor.find_inflection_point(score, employee.work_patterns)
    if inflection:
        console.print(
            f"\n[bold red]Inflection Point:[/bold red] Week {inflection['week']} "
            f"({inflection['predicted_date']}) - Risk: {inflection['risk_score']:.0f}"
        )

    # Weeks to burnout
    wtb = predictor.weeks_to_burnout(score, employee.work_patterns)
    if wtb:
        console.print(f"[bold red]Estimated weeks to burnout: {wtb}[/bold red]")
    else:
        console.print("[green]Burnout threshold not predicted within 52 weeks.[/green]")


if __name__ == "__main__":
    cli()
