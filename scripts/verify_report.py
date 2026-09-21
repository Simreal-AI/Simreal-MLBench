"""Verify report arithmetic, coverage and interpretation without network access."""
from pathlib import Path
import json, math
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]

def main():
    catalog = json.loads((ROOT / "configs/catalog.json").read_text())
    protocol = json.loads((ROOT / "configs/protocol.json").read_text())
    assert len(catalog) == len({r["id"] for r in catalog}) == 60
    assert Counter(r["tier"] for r in catalog) == {"easy": 20, "medium": 20, "hard": 20}
    for row in catalog:
        assert row["resource_profile"] == protocol["tiers"][row["tier"]]
    report = json.loads((ROOT / "reports/results.json").read_text())
    assert report["purpose"] == "admission_baselines_not_agent_evaluation"
    assert len(report["results"]) == 3
    for row in report["results"]:
        assert row["evaluation_kind"] == "local_cpu_admission_baseline_not_agent_result"
        assert row["beaten"] + row["tied"] + row["better"] == row["reference_count"]
        p = (row["beaten"] + row["tied"] * .5) / row["reference_count"]
        assert math.isclose(p, row["percentile"], rel_tol=1e-12)
        assert math.isclose(100 * p * p, row["quadratic_score"], rel_tol=1e-12)
    print(json.dumps({"passed": True, "tasks": 60, "verified_baseline_rows": 3,
                      "scope": "Saved reference counts and score arithmetic; no remote score reauthentication or agent leaderboard"}))
if __name__ == "__main__": main()
