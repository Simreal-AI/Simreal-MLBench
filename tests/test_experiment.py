from copy import deepcopy
import unittest

from mle_benchmark.experiment import aggregate_experiment
from mle_benchmark.scoring import aggregate


def fixture():
    manifest = {
        "experiment_id": "fixture-experiment",
        "system_id": "fixture-system",
        "frozen": True,
        "closed": True,
        "profile_manifest_sha256": "a" * 64,
        "protocol_sha256": "b" * 64,
        "expected_task_ids": ["easy-task", "medium-task", "hard-task"],
        "seeds": [17, 42, 101],
    }
    tasks = [
        {
            "id": f"{tier}-task", "tier": tier, "track": "official",
            "test_set_id": "fixture-test", "snapshot_sha256": "c" * 64,
        }
        for tier in ("easy", "medium", "hard")
    ]
    bindings = {field: manifest[field] for field in (
        "experiment_id", "system_id", "profile_manifest_sha256", "protocol_sha256"
    )}
    results = [
        {
            **bindings, "task_id": task["id"], "seed": seed,
            "status": "ok", "score": 90,
            "track": task["track"], "test_set_id": task["test_set_id"],
            "snapshot_sha256": task["snapshot_sha256"],
        }
        for task in tasks for seed in manifest["seeds"]
    ]
    return manifest, tasks, results


class ExperimentAggregationTests(unittest.TestCase):
    def test_success_preserves_scorer_and_adds_identity(self):
        manifest, tasks, results = fixture()
        before = deepcopy((manifest, tasks, results))
        report = aggregate_experiment(manifest, tasks, results)
        expected = aggregate(tasks, results, manifest["seeds"])
        self.assertEqual({field: report[field] for field in expected}, expected)
        self.assertEqual(report["overall"], 90)
        self.assertEqual(report["expected_runs"], 9)
        self.assertEqual(report["system_id"], manifest["system_id"])
        self.assertEqual(report["experiment_id"], manifest["experiment_id"])
        self.assertEqual(report["experiment_schema_version"], 1)
        self.assertEqual((manifest, tasks, results), before)

    def test_open_or_unfrozen_experiment_rejected(self):
        for field in ("closed", "frozen"):
            for value in (False, None, 1, "true"):
                with self.subTest(field=field, value=value):
                    manifest, tasks, results = fixture()
                    manifest[field] = value
                    with self.assertRaises(ValueError):
                        aggregate_experiment(manifest, tasks, results)

    def test_manifest_requires_nonblank_system_and_experiment(self):
        for field in ("system_id", "experiment_id"):
            for value in (None, "", "  ", 7):
                with self.subTest(field=field, value=value):
                    manifest, tasks, results = fixture()
                    manifest[field] = value
                    with self.assertRaisesRegex(ValueError, "nonblank"):
                        aggregate_experiment(manifest, tasks, results)

    def test_manifest_requires_sha256_hashes(self):
        for field in ("profile_manifest_sha256", "protocol_sha256"):
            for value in (None, "", "not-a-hash", "a" * 63, "g" * 64):
                with self.subTest(field=field, value=value):
                    manifest, tasks, results = fixture()
                    manifest[field] = value
                    with self.assertRaisesRegex(ValueError, "SHA256"):
                        aggregate_experiment(manifest, tasks, results)

    def test_every_result_binds_experiment_profile_and_protocol(self):
        for status in ("ok", "agent_failure", "infra_failure"):
            for field in ("experiment_id", "system_id", "profile_manifest_sha256", "protocol_sha256"):
                for value in (None, "different"):
                    with self.subTest(status=status, field=field, value=value):
                        manifest, tasks, results = fixture()
                        results[0]["status"] = status
                        if value is None:
                            del results[0][field]
                        else:
                            results[0][field] = value
                        with self.assertRaisesRegex(ValueError, field):
                            aggregate_experiment(manifest, tasks, results)

    def test_exact_task_roster_required(self):
        for change in ("missing", "extra", "substituted", "duplicate"):
            with self.subTest(change=change):
                manifest, tasks, results = fixture()
                if change == "missing":
                    tasks.pop()
                elif change == "extra":
                    tasks.append({**tasks[0], "id": "extra-task"})
                elif change == "substituted":
                    tasks[0]["id"] = "different-task"
                else:
                    tasks.append(tasks[0])
                with self.assertRaises(ValueError):
                    aggregate_experiment(manifest, tasks, results)

    def test_manifest_rosters_must_be_nonempty_and_unique(self):
        invalid = {
            "expected_task_ids": ([], ["a", "a"], [" "], "a", [None]),
            "seeds": ([], [17, 17], [True], [17.0], "17", [None]),
        }
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    manifest, tasks, results = fixture()
                    manifest[field] = value
                    with self.assertRaises(ValueError):
                        aggregate_experiment(manifest, tasks, results)

    def test_unexpected_task_or_seed_rejected(self):
        for field, value in (("task_id", "unexpected"), ("seed", 999), ("seed", 17.0)):
            with self.subTest(field=field, value=value):
                manifest, tasks, results = fixture()
                results[0][field] = value
                with self.assertRaisesRegex(ValueError, "roster"):
                    aggregate_experiment(manifest, tasks, results)

    def test_duplicate_run_rejected_even_when_failure(self):
        manifest, tasks, results = fixture()
        results.append({**results[0], "status": "agent_failure"})
        with self.assertRaisesRegex(ValueError, "Duplicate result"):
            aggregate_experiment(manifest, tasks, results)

    def test_failed_runs_count_zero_without_becoming_missing(self):
        for status in ("agent_failure", "invalid_submission", "budget_exceeded"):
            with self.subTest(status=status):
                manifest, tasks, results = fixture()
                results[0]["status"] = status
                del results[0]["score"]
                report = aggregate_experiment(manifest, tasks, results)
                self.assertEqual(report["overall"], 80)
                self.assertEqual(report["missing_runs"], 0)
                self.assertEqual(report["status"], "complete")

    def test_missing_runs_count_zero_only_in_closed_experiment(self):
        manifest, tasks, results = fixture()
        results.pop()
        report = aggregate_experiment(manifest, tasks, results)
        self.assertEqual(report["overall"], 80)
        self.assertEqual(report["missing_runs"], 1)
        self.assertEqual(report["expected_runs"], 9)
        self.assertEqual(report["status"], "complete_with_missing_as_zero")
        manifest["closed"] = False
        with self.assertRaisesRegex(ValueError, "closed"):
            aggregate_experiment(manifest, tasks, results)

    def test_infrastructure_failure_remains_pending(self):
        manifest, tasks, results = fixture()
        results[0]["status"] = "infra_failure"
        report = aggregate_experiment(manifest, tasks, results)
        self.assertIsNone(report["overall"])
        self.assertEqual(report["status"], "pending_infrastructure_rerun")
        self.assertEqual(report["profile_manifest_sha256"], manifest["profile_manifest_sha256"])

    def test_underlying_test_provenance_still_checked_for_failures(self):
        manifest, tasks, results = fixture()
        results[0].update(status="agent_failure", snapshot_sha256="d" * 64)
        with self.assertRaisesRegex(ValueError, "provenance"):
            aggregate_experiment(manifest, tasks, results)

    def test_input_order_does_not_change_report(self):
        manifest, tasks, results = fixture()
        manifest["expected_task_ids"].append("easy-task-2")
        tasks.append({**tasks[0], "id": "easy-task-2"})
        results.extend({**results[0], "task_id": "easy-task-2", "seed": seed, "score": 10}
                       for seed in manifest["seeds"])
        self.assertEqual(
            aggregate_experiment(manifest, tasks, results),
            aggregate_experiment(manifest, list(reversed(tasks)), list(reversed(results))),
        )


if __name__ == "__main__":
    unittest.main()
