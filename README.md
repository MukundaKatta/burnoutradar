# BurnoutRadar

AI Burnout Predictor - Comprehensive burnout risk assessment using the Maslach Burnout Inventory (MBI) framework.

## Features

- **Burnout Signal Detection**: Analyze work patterns including overtime, meeting load, email volume, and after-hours activity
- **MBI-Inspired Scoring**: Compute exhaustion, cynicism, and professional efficacy scores based on the Maslach Burnout Inventory
- **Risk Prediction**: Forecast burnout trajectory and identify inflection points
- **Workload Analysis**: Determine sustainable vs unsustainable work levels
- **Work-Life Balance**: Score boundaries, recovery time, and disconnection quality
- **Team Health**: Aggregate individual burnout signals for team-level risk assessment

## MBI Dimensions

BurnoutRadar uses the three validated MBI dimensions:

1. **Emotional Exhaustion (EE)**: Feeling emotionally drained and depleted by work
2. **Depersonalization/Cynicism (DP)**: Detachment, negativism, and reduced engagement
3. **Personal Accomplishment/Efficacy (PA)**: Reduced sense of competence and achievement

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Run a burnout risk analysis with simulated data
burnoutradar analyze --simulate

# Generate a team health report
burnoutradar team-report --size 10

# Check individual burnout risk
burnoutradar check --weeks 4
```

## Dependencies

- numpy
- pydantic
- click
- rich
