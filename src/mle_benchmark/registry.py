"""Candidate and release admission checks, deliberately failing closed."""
from collections import Counter


def validate_catalog(tasks: list[dict], expected_per_tier: int | None = None) -> dict:
    # The current design has 60 tasks; the immutable historical roster has 90.
    # Other sizes still require the caller to explicitly declare a tier count.
    if expected_per_tier is None:
        expected_per_tier = 20 if len(tasks) == 60 else 30
    errors = []
    ids = [t.get("id") for t in tasks]
    if len(set(ids)) != len(ids):
        errors.append("Duplicate competition IDs")
    counts = Counter(t.get("tier") for t in tasks)
    for tier in ("easy", "medium", "hard"):
        if counts[tier] != expected_per_tier:
            errors.append(f"{tier}: expected {expected_per_tier}, found {counts[tier]}")
    if set(counts) - {"easy", "medium", "hard"}:
        errors.append("Unknown tiers")
    required = ("id", "title", "platform", "url", "tier", "modality", "task_type",
                "metric", "metric_direction", "evidence_urls", "remote_submission_status")
    for task in tasks:
        for field in required:
            if field not in task or task[field] is None or task[field] == "" or task[field] == []:
                errors.append(f"{task.get('id')}: missing {field}")
        if task.get("metric_direction") not in ("higher", "lower", "unknown"):
            errors.append(f"{task.get('id')}: bad metric direction")
    return {"valid": not errors, "errors": errors, "total": len(tasks),
            "tiers": dict(counts), "modalities": dict(Counter(t.get("modality") for t in tasks)),
            "remote_submission_status": dict(Counter(t.get("remote_submission_status") for t in tasks)),
            "note": "Structural validity does not imply competition admission or successful remote runs"}


def admission_blockers(task: dict, track: str) -> list[str]:
    if track not in ("official", "offline"):
        raise ValueError("Unknown track")
    a = task.get("admission", {}).get(track, {})
    required = ["rules_reviewed", "data_downloaded_and_hashed", "submission_schema_validated",
                "grader_validated", "hardware_pilot_passed", "leakage_audit_passed",
                "reference_snapshot_frozen"]
    if track == "official":
        required += ["remote_submission_tested", "score_split_identity_verified",
                     "complete_final_leaderboard_verified", "external_compute_allowed"]
    else:
        required += ["hidden_split_validated", "reference_systems_calibrated"]
    return [key for key in required if a.get(key) is not True]
