"""Frozen reference-distribution scoring. No cross-test-set rank inference."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import json
import math
import random
from statistics import mean
from typing import Any


def decimal_score(value: Any, precision: int | None = None) -> Decimal:
    try:
        score = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Score must be numeric") from exc
    if not score.is_finite():
        raise ValueError("NaN and infinite scores are not allowed")
    if precision is not None:
        if type(precision) is not int or not 0 <= precision <= 15:
            raise ValueError("score_decimals must be 0..15 or null")
        try:
            score = score.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_EVEN)
        except InvalidOperation as exc:
            raise ValueError("Score exceeds supported decimal precision") from exc
    return score


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def seal_snapshot(snapshot: dict) -> dict:
    """Seal an already curator-approved snapshot; checksum is integrity, not authentication."""
    result = {k: v for k, v in snapshot.items() if k != "sha256"}
    return {**result, "sha256": canonical_sha256(result)}


@dataclass(frozen=True)
class RankResult:
    competition_id: str
    test_set_id: str
    split: str
    metric: str
    direction: str
    raw_score: str
    reference_count: int
    beaten: int
    tied: int
    better: int
    percentile: float
    quadratic_score: float
    midrank_if_inserted: float
    top_10_percent: bool
    top_1_percent: bool
    track: str
    snapshot_sha256: str

    def to_dict(self) -> dict:
        return asdict(self)


def grade(snapshot: dict, result: dict) -> RankResult:
    """p=(strictly beaten + 0.5 * tied)/N; score=100*p^2.

    Each reference is one eligible historical team (official) or one frozen
    reference system (offline). Caller supplies broker-authenticated records.
    """
    expected = seal_snapshot(snapshot)["sha256"]
    if snapshot.get("sha256") != expected:
        raise ValueError("Snapshot checksum missing or mismatched")
    if snapshot.get("frozen") is not True:
        raise ValueError("Reference distribution must be frozen")
    if snapshot.get("track") not in ("official", "offline"):
        raise ValueError("Unknown evaluation track")
    for field in ("competition_id", "metric", "direction", "test_set_id", "split", "track"):
        if not snapshot.get(field) or snapshot.get(field) != result.get(field):
            raise ValueError(f"Incomparable or missing {field}")
    if snapshot["split"] in ("unknown", "unverified") or snapshot["test_set_id"] in ("unknown", "unverified"):
        raise ValueError("Test set and split must be positively identified")
    if snapshot["direction"] not in ("higher", "lower"):
        raise ValueError("direction must be higher or lower")
    if not snapshot.get("source_url") or not snapshot.get("frozen_at"):
        raise ValueError("Snapshot provenance missing")
    if snapshot["track"] == "official":
        if snapshot.get("split") not in ("public", "private"):
            raise ValueError("Official split must be public or private")
        if snapshot.get("final") is not True or snapshot.get("complete") is not True:
            raise ValueError("Need a complete final leaderboard, not a top-N or live view")
        if snapshot.get("unit") != "team":
            raise ValueError("Official rank unit must be team")
    elif snapshot.get("unit") != "reference_system":
        raise ValueError("Offline references must be frozen reference systems")
    rows = snapshot.get("rows", [])
    if len(rows) < 2:
        raise ValueError("Need at least two reference rows (production admission requires more)")
    ids = [row["id"] for row in rows]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("Reference IDs must be non-empty and unique")
    precision = snapshot.get("score_decimals")
    scores = [decimal_score(row["score"], precision) for row in rows]
    if len(set(scores)) == 1:
        raise ValueError("Reference distribution has no score resolution")
    score = decimal_score(result["raw_score"], precision)
    tied = sum(x == score for x in scores)
    beaten = sum(x < score if snapshot["direction"] == "higher" else x > score for x in scores)
    better = len(scores) - beaten - tied
    p = (beaten + tied / 2) / len(scores)
    return RankResult(snapshot["competition_id"],snapshot["test_set_id"],snapshot["split"],
                      snapshot["metric"],snapshot["direction"],str(score), len(scores), beaten, tied, better, p, 100 * p * p,
                      1 + better + tied / 2, p >= .90, p >= .99,
                      snapshot["track"], snapshot["sha256"])


def aggregate(tasks: list[dict], results: list[dict], seeds: list[int], *,
              bootstrap_samples: int = 2000, bootstrap_seed: int = 0) -> dict:
    """Equal tasks within tiers, equal tiers. Fixed denominator; paired runs only.

    Input is trusted grader output with a task/seed/status/score record per run.
    Infrastructure outages make the aggregate pending; missing/agent failures
    count zero. Never silently drop difficult tasks or select the best seed.
    Bootstrap resamples tasks within tier, retaining all seeds per task.
    """
    if not tasks or not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("Non-empty tasks and unique seeds required")
    if type(bootstrap_samples) is not int or bootstrap_samples < 100:
        raise ValueError("At least 100 bootstrap samples required")
    task_map = {t["id"]: t for t in tasks}
    if len(task_map) != len(tasks):
        raise ValueError("Duplicate task IDs")
    if any(t["tier"] not in ("easy", "medium", "hard") for t in tasks):
        raise ValueError("Unknown tier")
    if len({t["track"] for t in tasks}) != 1:
        raise ValueError("Aggregate official and offline tracks separately")
    provenance = ("track", "test_set_id", "snapshot_sha256")
    for t in tasks:
        if any(not t.get(f) for f in provenance):
            raise ValueError("Manifest must freeze track, test set and snapshot for every task")
    lookup = {}
    for r in results:
        key = (r["task_id"], r["seed"])
        if key in lookup or key[0] not in task_map or key[1] not in seeds:
            raise ValueError("Duplicate or unexpected task/seed")
        if any(r.get(f) != task_map[key[0]][f] for f in provenance):
            raise ValueError("Result provenance does not match the frozen manifest")
        if r["status"] not in ("ok", "agent_failure", "invalid_submission", "budget_exceeded", "infra_failure"):
            raise ValueError("Unknown run status")
        if r["status"] == "ok":
            s = float(r["score"])
            if not math.isfinite(s) or not 0 <= s <= 100:
                raise ValueError("Scores must be finite and within 0..100")
        lookup[key] = r
    if any(r["status"] == "infra_failure" for r in results):
        return {"status": "pending_infrastructure_rerun", "overall": None}
    groups = {tier: [] for tier in ("easy", "medium", "hard")}
    missing = 0
    for task in tasks:
        values = []
        for seed in seeds:
            r = lookup.get((task["id"], seed))
            missing += r is None
            values.append(float(r["score"]) if r and r["status"] == "ok" else 0.)
        groups[task["tier"]].append(mean(values))
    if any(not values for values in groups.values()):
        raise ValueError("Each tier must contain at least one task")
    tier_means = {tier: mean(values) for tier, values in groups.items()}
    rng = random.Random(bootstrap_seed)
    boots = sorted(mean(mean(rng.choices(v, k=len(v))) for v in groups.values())
                   for _ in range(bootstrap_samples))
    return {"status": "complete_with_missing_as_zero" if missing else "complete",
            "overall": mean(tier_means.values()), "tier_means": tier_means,
            "missing_runs": missing, "expected_runs": len(tasks) * len(seeds),
            "track": tasks[0]["track"],
            "task_bootstrap_95_ci": [boots[int(.025 * bootstrap_samples)], boots[int(.975 * bootstrap_samples)]],
            "ci_scope": "task resampling within tier, all fixed seeds retained; not model stochasticity alone"}
