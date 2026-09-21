"""Release-report guard around :func:`scoring.aggregate`.

Manifest schema (one experiment/report per official or offline track)::

    {
        "experiment_id": "<nonblank experiment identifier>",
        "system_id": "<nonblank model-and-agent profile label>",
        "frozen": true,
        "closed": true,
        "profile_manifest_sha256": "<64 lowercase hexadecimal characters>",
        "protocol_sha256": "<64 lowercase hexadecimal characters>",
        "expected_task_ids": ["<task id>", "..."],
        "seeds": [17]
    }

Task IDs and integer seeds must be nonempty, unique lists. ``tasks`` must contain
exactly that task roster, with the task fields required by ``scoring.aggregate``.
Every result, including failures, must repeat ``experiment_id``, ``system_id``,
``profile_manifest_sha256``, and ``protocol_sha256`` alongside the existing
task_id/seed/status/score and test-provenance fields. Unknown or duplicate
task/seed pairs are rejected. Extra manifest and result metadata is permitted.

Closure is an explicit caller attestation that the scoring deadline has passed
and missing runs can be counted as zero. Failed and missing runs retain the
underlying scorer's semantics; infrastructure failures still make a report
pending. Task order is canonicalized to the manifest for reproducible bootstrap
sampling. Task/seed counts are not hardcoded because the tracks have separate
rosters; release admission must establish the intended full benchmark roster.

This checks report consistency, not runtime budgets, account billing, actual
model identity, manifest authenticity, or the contents referenced by hashes.
Inputs must come from the trusted experiment controller and evaluation service.
Reports include ``experiment_schema_version: 1`` for this wrapper's schema.
"""
from __future__ import annotations

import re

from .scoring import aggregate


EXPERIMENT_SCHEMA_VERSION = 1
_BINDING_FIELDS = ("experiment_id", "system_id", "profile_manifest_sha256", "protocol_sha256")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def aggregate_experiment(manifest: dict, tasks: list[dict], results: list[dict]) -> dict:
    """Validate a closed, frozen experiment and aggregate its complete roster."""
    if not isinstance(manifest, dict):
        raise ValueError("Experiment manifest must be an object")
    if manifest.get("closed") is not True:
        raise ValueError("Experiment must be explicitly closed before aggregation")
    if manifest.get("frozen") is not True:
        raise ValueError("Experiment manifest must be explicitly frozen")
    for field in ("experiment_id", "system_id"):
        if not _nonblank(manifest.get(field)):
            raise ValueError(f"Manifest requires a nonblank {field}")
    for field in ("profile_manifest_sha256", "protocol_sha256"):
        value = manifest.get(field)
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise ValueError(f"Manifest {field} must be a lowercase SHA256 digest")

    task_ids = manifest.get("expected_task_ids")
    if (not isinstance(task_ids, list) or not task_ids
            or any(not _nonblank(value) for value in task_ids)
            or len(task_ids) != len(set(task_ids))):
        raise ValueError("Expected task IDs must be a nonempty unique list of strings")
    seeds = manifest.get("seeds")
    if (not isinstance(seeds, list) or not seeds
            or any(type(value) is not int for value in seeds)
            or len(seeds) != len(set(seeds))):
        raise ValueError("Manifest seeds must be a nonempty unique list of integers")

    if not isinstance(tasks, list) or any(not isinstance(task, dict) for task in tasks):
        raise ValueError("Tasks must be a list of task objects")
    actual_ids = [task.get("id") for task in tasks]
    if any(not _nonblank(value) for value in actual_ids):
        raise ValueError("Every task requires a nonblank id")
    if len(actual_ids) != len(set(actual_ids)):
        raise ValueError("Duplicate task IDs")
    if set(actual_ids) != set(task_ids):
        raise ValueError("Tasks do not match the experiment's exact expected task roster")

    if not isinstance(results, list):
        raise ValueError("Results must be a list of result objects")
    seen = set()
    expected_ids, expected_seeds = set(task_ids), set(seeds)
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Every result must be an object")
        for field in _BINDING_FIELDS:
            if result.get(field) != manifest[field]:
                raise ValueError(f"Result {field} does not match the experiment manifest")
        task_id, seed = result.get("task_id"), result.get("seed")
        if (not _nonblank(task_id) or task_id not in expected_ids
                or type(seed) is not int or seed not in expected_seeds):
            raise ValueError("Result task/seed is outside the frozen experiment roster")
        key = (task_id, seed)
        if key in seen:
            raise ValueError("Duplicate result task/seed")
        seen.add(key)

    task_map = {task["id"]: task for task in tasks}
    report = aggregate([task_map[task_id] for task_id in task_ids], results, seeds)
    return {
        **report,
        "experiment_schema_version": EXPERIMENT_SCHEMA_VERSION,
        "experiment_id": manifest["experiment_id"],
        "system_id": manifest["system_id"],
        "profile_manifest_sha256": manifest["profile_manifest_sha256"],
        "protocol_sha256": manifest["protocol_sha256"],
    }
