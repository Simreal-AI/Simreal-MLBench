"""Synthetic RLVR reward-contract demonstration; no training or model calls."""
from mle_benchmark.scoring import grade, seal_snapshot

snapshot = seal_snapshot({
    "competition_id": "synthetic-learning-task", "metric": "rmse", "direction": "lower",
    "test_set_id": "synthetic-reward-fold-v1", "split": "reward", "track": "offline",
    "unit": "reference_system", "source_url": "https://example.test/synthetic-fixture",
    "frozen_at": "2026-09-21T00:00:00Z", "frozen": True, "score_decimals": 4,
    "rows": [{"id": "baseline-a", "score": 4}, {"id": "baseline-b", "score": 2},
             {"id": "baseline-c", "score": 1}],
})
result = {key: snapshot[key] for key in ("competition_id", "metric", "direction", "test_set_id", "split", "track")}
result["raw_score"] = 2
reward = grade(snapshot, result).quadratic_score / 100
assert reward == 0.25
print({"reward": reward, "scope": "synthetic learning example, not an official benchmark score"})
