"""Burnout signal detection from work pattern data.

Analyzes behavioral signals that correlate with burnout:
- Overtime patterns (chronic overwork)
- Meeting load (collaboration overload)
- Email volume (communication burden)
- After-hours activity (boundary erosion)
- Deep work deficit (fragmentation)

References:
  - Maslach & Leiter (2016) Understanding the burnout experience
  - Perlow & Porter (2009) Making time off predictable and required
  - Mark et al. (2008) The cost of interrupted work
"""

from __future__ import annotations

import numpy as np

from burnoutradar.models import WorkPattern


class BurnoutSignalDetector:
    """Detect and quantify burnout signals from work pattern data.

    Each signal is scored 0-100 where higher = more concerning.
    """

    # Thresholds based on occupational health research
    OVERTIME_WARNING_HOURS = 5.0     # >5h overtime/week starts risk
    OVERTIME_DANGER_HOURS = 15.0     # >15h is high risk
    MEETING_WARNING_PCT = 0.40       # >40% of time in meetings
    MEETING_DANGER_PCT = 0.60        # >60% is high risk
    EMAIL_WARNING_PER_DAY = 50       # >50 emails/day
    EMAIL_DANGER_PER_DAY = 100       # >100 emails/day
    AFTER_HOURS_WARNING = 5          # >5 after-hours events/week
    AFTER_HOURS_DANGER = 15          # >15 is high risk
    DEEP_WORK_MINIMUM_HOURS = 10     # Need >= 10h deep work per week
    WEEKEND_WORK_WARNING = 4.0       # >4h on weekends

    def analyze_signals(
        self, patterns: list[WorkPattern]
    ) -> dict[str, float]:
        """Analyze all burnout signals across multiple weeks.

        Args:
            patterns: List of weekly work patterns.

        Returns:
            Dict mapping signal name to severity score (0-100).
        """
        if not patterns:
            return {}

        return {
            "overtime": self._overtime_signal(patterns),
            "meeting_load": self._meeting_load_signal(patterns),
            "email_volume": self._email_volume_signal(patterns),
            "after_hours": self._after_hours_signal(patterns),
            "deep_work_deficit": self._deep_work_deficit_signal(patterns),
            "weekend_work": self._weekend_work_signal(patterns),
            "late_nights": self._late_night_signal(patterns),
            "no_recovery": self._recovery_deficit_signal(patterns),
            "context_switching": self._context_switch_signal(patterns),
            "chronic_overwork": self._chronic_overwork_signal(patterns),
        }

    def _overtime_signal(self, patterns: list[WorkPattern]) -> float:
        """Score overtime severity. Chronic overtime is worse than occasional."""
        overtime_hours = [p.overtime_hours for p in patterns]
        avg_ot = np.mean(overtime_hours)

        if avg_ot <= 0:
            return 0.0

        # Linear scale from warning to danger threshold
        base = np.clip(
            (avg_ot - self.OVERTIME_WARNING_HOURS)
            / (self.OVERTIME_DANGER_HOURS - self.OVERTIME_WARNING_HOURS)
            * 100, 0, 100
        )

        # Chronicity multiplier: consecutive weeks of overtime increase risk
        consecutive = self._consecutive_above(overtime_hours, self.OVERTIME_WARNING_HOURS)
        chronicity = min(1.5, 1.0 + consecutive * 0.1)

        return float(min(100, base * chronicity))

    def _meeting_load_signal(self, patterns: list[WorkPattern]) -> float:
        """Score meeting overload."""
        meeting_pcts = [
            p.meeting_hours / max(p.hours_worked, 1) for p in patterns
        ]
        avg_pct = np.mean(meeting_pcts)

        return float(np.clip(
            (avg_pct - self.MEETING_WARNING_PCT)
            / (self.MEETING_DANGER_PCT - self.MEETING_WARNING_PCT)
            * 100, 0, 100
        ))

    def _email_volume_signal(self, patterns: list[WorkPattern]) -> float:
        """Score email burden."""
        daily_emails = [p.email_count / 5.0 for p in patterns]  # Assuming 5-day week
        avg_daily = np.mean(daily_emails)

        return float(np.clip(
            (avg_daily - self.EMAIL_WARNING_PER_DAY)
            / (self.EMAIL_DANGER_PER_DAY - self.EMAIL_WARNING_PER_DAY)
            * 100, 0, 100
        ))

    def _after_hours_signal(self, patterns: list[WorkPattern]) -> float:
        """Score after-hours work boundary erosion."""
        after_hours = [p.after_hours_events for p in patterns]
        avg_ah = np.mean(after_hours)

        return float(np.clip(
            (avg_ah - self.AFTER_HOURS_WARNING)
            / (self.AFTER_HOURS_DANGER - self.AFTER_HOURS_WARNING)
            * 100, 0, 100
        ))

    def _deep_work_deficit_signal(self, patterns: list[WorkPattern]) -> float:
        """Score lack of deep focused work time."""
        deep_hours = [p.deep_work_hours for p in patterns]
        avg_deep = np.mean(deep_hours)

        if avg_deep >= self.DEEP_WORK_MINIMUM_HOURS:
            return 0.0

        # Inverse: less deep work = higher signal
        deficit_ratio = 1.0 - avg_deep / self.DEEP_WORK_MINIMUM_HOURS
        return float(min(100, deficit_ratio * 100))

    def _weekend_work_signal(self, patterns: list[WorkPattern]) -> float:
        """Score weekend work frequency and intensity."""
        weekend_hours = [p.weekend_hours for p in patterns]
        avg_wh = np.mean(weekend_hours)
        weeks_with_weekend = sum(1 for w in weekend_hours if w > 0)
        frequency = weeks_with_weekend / max(len(patterns), 1)

        intensity = float(np.clip(avg_wh / self.WEEKEND_WORK_WARNING * 50, 0, 50))
        freq_score = frequency * 50

        return min(100, intensity + freq_score)

    def _late_night_signal(self, patterns: list[WorkPattern]) -> float:
        """Score late-night work activity (after 9 PM)."""
        late_counts = [p.late_night_count for p in patterns]
        avg_late = np.mean(late_counts)

        return float(np.clip(avg_late / 10.0 * 100, 0, 100))

    def _recovery_deficit_signal(self, patterns: list[WorkPattern]) -> float:
        """Score lack of recovery time (PTO usage)."""
        total_weeks = len(patterns)
        total_pto = sum(p.pto_days for p in patterns)

        # Expected: ~1 PTO day per 5 weeks (10 days/year)
        expected_pto = total_weeks / 5.0
        if expected_pto <= 0:
            return 50.0

        ratio = total_pto / expected_pto
        if ratio >= 1.0:
            return 0.0

        return float(min(100, (1.0 - ratio) * 100))

    def _context_switch_signal(self, patterns: list[WorkPattern]) -> float:
        """Score context-switching overhead."""
        switches = [p.context_switches for p in patterns]
        avg_switches = np.mean(switches)

        # >20 switches/week is concerning, >40 is dangerous
        return float(np.clip((avg_switches - 20) / 20 * 100, 0, 100))

    def _chronic_overwork_signal(self, patterns: list[WorkPattern]) -> float:
        """Detect sustained overwork (>50h/week for 3+ consecutive weeks)."""
        hours = [p.hours_worked for p in patterns]
        consecutive = self._consecutive_above(hours, 50.0)

        if consecutive < 3:
            return 0.0

        return float(min(100, (consecutive - 2) * 25))

    def _consecutive_above(
        self, values: list[float], threshold: float
    ) -> int:
        """Count max consecutive values above a threshold."""
        max_run = 0
        current_run = 0
        for v in values:
            if v > threshold:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        return max_run

    def get_top_signals(
        self, signals: dict[str, float], n: int = 3
    ) -> list[tuple[str, float]]:
        """Get the top N most concerning signals.

        Returns:
            List of (signal_name, score) tuples sorted by severity.
        """
        ranked = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        return [(name, score) for name, score in ranked[:n] if score > 0]
