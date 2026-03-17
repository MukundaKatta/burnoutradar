"""MBI-inspired burnout scoring.

Computes burnout scores across the three Maslach Burnout Inventory dimensions:
1. Emotional Exhaustion (EE) - feeling emotionally drained
2. Depersonalization/Cynicism (DP) - detachment from work
3. Personal Accomplishment/Efficacy (PA) - reduced sense of achievement

MBI cutoff scores (original scale):
  - EE: Low <= 16, Moderate 17-26, High >= 27 (max 54)
  - DP: Low <= 6, Moderate 7-12, High >= 13 (max 30)
  - PA: Low >= 39, Moderate 32-38, High (burnout) <= 31 (max 48)

Our implementation maps behavioral signals to these dimensions using
validated proxy indicators from organizational psychology research.

References:
  - Maslach & Jackson (1981) MBI Manual
  - Schaufeli et al. (2002) MBI-General Survey
  - Bakker & Demerouti (2007) Job Demands-Resources model
"""

from __future__ import annotations

import numpy as np

from burnoutradar.models import BurnoutScore, RiskLevel, WorkPattern


class BurnoutScorer:
    """Compute MBI-inspired burnout scores from work patterns and signals.

    Maps observable work behaviors to the three MBI dimensions using
    evidence-based proxy relationships from the JD-R (Job Demands-Resources)
    model.
    """

    # Dimension weights for overall risk
    WEIGHT_EXHAUSTION = 0.40   # Exhaustion is the core dimension
    WEIGHT_CYNICISM = 0.30     # Cynicism/depersonalization
    WEIGHT_EFFICACY = 0.30     # Reduced efficacy (inverted)

    # MBI threshold mappings (normalized to 0-100)
    EXHAUSTION_THRESHOLDS = {"low": 30, "moderate": 50, "high": 70}
    CYNICISM_THRESHOLDS = {"low": 20, "moderate": 40, "high": 60}
    EFFICACY_THRESHOLDS = {"high": 70, "moderate": 50, "low": 30}

    def score(
        self,
        signals: dict[str, float],
        patterns: list[WorkPattern],
    ) -> BurnoutScore:
        """Compute full MBI-inspired burnout score.

        Args:
            signals: Dict of signal name to severity score (0-100) from
                     BurnoutSignalDetector.
            patterns: Recent work patterns for context.

        Returns:
            BurnoutScore with all three MBI dimensions.
        """
        exhaustion = self._compute_exhaustion(signals, patterns)
        cynicism = self._compute_cynicism(signals, patterns)
        efficacy = self._compute_efficacy(signals, patterns)

        overall = self._compute_overall_risk(exhaustion, cynicism, efficacy)
        risk_level = self._classify_risk(overall)

        # Determine primary factor
        primary, secondary = self._identify_factors(signals)

        # Determine trend from patterns
        trend = self._assess_trend(patterns)

        return BurnoutScore(
            exhaustion=round(exhaustion, 1),
            cynicism=round(cynicism, 1),
            efficacy=round(efficacy, 1),
            overall_risk=round(overall, 1),
            risk_level=risk_level,
            trend=trend,
            primary_factor=primary,
            secondary_factors=secondary,
        )

    def _compute_exhaustion(
        self, signals: dict[str, float], patterns: list[WorkPattern]
    ) -> float:
        """Compute Emotional Exhaustion proxy score.

        EE is driven by: chronic overwork, overtime, meeting overload,
        lack of recovery, and sustained high workload.

        JD-R mapping: High job demands -> exhaustion
        """
        weights = {
            "overtime": 0.25,
            "chronic_overwork": 0.25,
            "meeting_load": 0.15,
            "no_recovery": 0.15,
            "late_nights": 0.10,
            "weekend_work": 0.10,
        }

        score = sum(
            signals.get(signal, 0) * weight
            for signal, weight in weights.items()
        )

        # Boost if sustained high hours
        if patterns:
            avg_hours = np.mean([p.hours_worked for p in patterns])
            if avg_hours > 50:
                score = min(100, score * 1.2)

        return float(np.clip(score, 0, 100))

    def _compute_cynicism(
        self, signals: dict[str, float], patterns: list[WorkPattern]
    ) -> float:
        """Compute Depersonalization/Cynicism proxy score.

        Cynicism is driven by: boundary erosion, after-hours demands,
        context switching (feeling like a cog), and email overload.

        JD-R mapping: Low resources + high demands -> cynicism
        """
        weights = {
            "after_hours": 0.25,
            "email_volume": 0.20,
            "context_switching": 0.20,
            "deep_work_deficit": 0.15,
            "weekend_work": 0.10,
            "meeting_load": 0.10,
        }

        score = sum(
            signals.get(signal, 0) * weight
            for signal, weight in weights.items()
        )

        # Boundary erosion compounds cynicism
        if signals.get("after_hours", 0) > 50 and signals.get("weekend_work", 0) > 50:
            score = min(100, score * 1.3)

        return float(np.clip(score, 0, 100))

    def _compute_efficacy(
        self, signals: dict[str, float], patterns: list[WorkPattern]
    ) -> float:
        """Compute Professional Efficacy proxy score.

        Higher = better (unlike EE and DP where higher = worse).
        Efficacy is reduced by: context switching, deep work deficit,
        meeting overload, and chronic overwork (no time for meaningful work).

        JD-R mapping: Low resources -> reduced efficacy
        """
        # Start at 100 (full efficacy) and subtract
        negative_weights = {
            "deep_work_deficit": 0.30,
            "context_switching": 0.25,
            "meeting_load": 0.20,
            "chronic_overwork": 0.15,
            "email_volume": 0.10,
        }

        reduction = sum(
            signals.get(signal, 0) * weight
            for signal, weight in negative_weights.items()
        )

        # PTO and recovery boost efficacy
        if patterns:
            total_pto = sum(p.pto_days for p in patterns)
            if total_pto > 0:
                reduction *= 0.9  # 10% buffer from recovery

        efficacy = 100.0 - reduction
        return float(np.clip(efficacy, 0, 100))

    def _compute_overall_risk(
        self, exhaustion: float, cynicism: float, efficacy: float
    ) -> float:
        """Compute overall burnout risk from three MBI dimensions.

        Risk = weighted combination of exhaustion, cynicism, and inverted efficacy.
        """
        inverted_efficacy = 100.0 - efficacy  # Higher = worse

        risk = (
            self.WEIGHT_EXHAUSTION * exhaustion
            + self.WEIGHT_CYNICISM * cynicism
            + self.WEIGHT_EFFICACY * inverted_efficacy
        )
        return float(np.clip(risk, 0, 100))

    def _classify_risk(self, overall: float) -> RiskLevel:
        """Classify overall risk score into a risk level."""
        if overall >= 70:
            return RiskLevel.CRITICAL
        elif overall >= 50:
            return RiskLevel.HIGH
        elif overall >= 30:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

    def _identify_factors(
        self, signals: dict[str, float]
    ) -> tuple[str, list[str]]:
        """Identify primary and secondary contributing factors."""
        if not signals:
            return ("unknown", [])

        ranked = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        active = [(name, score) for name, score in ranked if score > 10]

        if not active:
            return ("none", [])

        primary = active[0][0]
        secondary = [name for name, _ in active[1:4]]
        return (primary, secondary)

    def _assess_trend(self, patterns: list[WorkPattern]) -> str:
        """Assess whether burnout risk is trending up, down, or stable.

        Compares the first half of patterns to the second half.
        """
        if len(patterns) < 4:
            return "stable"

        mid = len(patterns) // 2
        first_half = patterns[:mid]
        second_half = patterns[mid:]

        first_load = np.mean([p.hours_worked + p.overtime_hours for p in first_half])
        second_load = np.mean([p.hours_worked + p.overtime_hours for p in second_half])

        diff_pct = (second_load - first_load) / max(first_load, 1) * 100

        if diff_pct > 10:
            return "worsening"
        elif diff_pct < -10:
            return "improving"
        else:
            return "stable"
