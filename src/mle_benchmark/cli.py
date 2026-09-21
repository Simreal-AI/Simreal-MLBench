"""Public, local-only scoring CLI. No model calls or official uploads."""
import argparse
import json
from pathlib import Path
from .registry import validate_catalog
from .scoring import grade, seal_snapshot, aggregate
from .experiment import aggregate_experiment

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fields = {"validate": ["catalog"], "grade": ["snapshot", "result"],
              "seal": ["snapshot"], "aggregate": ["tasks", "results"],
              "aggregate-experiment": ["manifest", "tasks", "results"]}
    for command, names in fields.items():
        sub = commands.add_parser(command)
        for name in names: sub.add_argument(name, type=Path)
        if command == "aggregate": sub.add_argument("--seeds", nargs="+", type=int, default=[17])
    args = parser.parse_args()
    try:
        values = [json.loads(getattr(args, name).read_text()) for name in fields[args.command]]
        if args.command == "validate": output = validate_catalog(*values)
        elif args.command == "grade": output = grade(*values).to_dict()
        elif args.command == "seal": output = seal_snapshot(*values)
        elif args.command == "aggregate": output = aggregate(*values, args.seeds)
        else: output = aggregate_experiment(*values)
        print(json.dumps(output, indent=2, allow_nan=False))
        return 2 if output.get("valid") is False else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"mleb: {error}\n")

if __name__ == "__main__":
    raise SystemExit(main())
