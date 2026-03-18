"""CLI for burnoutradar."""
import sys, json, argparse
from .core import Burnoutradar

def main():
    parser = argparse.ArgumentParser(description="BurnoutRadar — AI Burnout Predictor. Detect burnout risk from work patterns and communication analysis.")
    parser.add_argument("command", nargs="?", default="status", choices=["status", "run", "info"])
    parser.add_argument("--input", "-i", default="")
    args = parser.parse_args()
    instance = Burnoutradar()
    if args.command == "status":
        print(json.dumps(instance.get_stats(), indent=2))
    elif args.command == "run":
        print(json.dumps(instance.detect(input=args.input or "test"), indent=2, default=str))
    elif args.command == "info":
        print(f"burnoutradar v0.1.0 — BurnoutRadar — AI Burnout Predictor. Detect burnout risk from work patterns and communication analysis.")

if __name__ == "__main__":
    main()
