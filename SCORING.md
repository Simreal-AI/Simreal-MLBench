# Scoring

Use the raw official competition metric and a frozen reference distribution matching the exact competition, metric, direction, test set, and split. A public score cannot be ranked against a private leaderboard. Official references must be complete final leaderboards, not top-N extracts or rolling standings.

```text
p = (strictly worse reference scores + 0.5 × tied reference scores) / N
TaskScore = 100 × p²
```

Quantize scores at the frozen decimal precision before identifying ties. The supplied scoring module checks these contracts and snapshot integrity. A checksum does not authenticate an official result: the trusted controller must establish its origin.

Each task has one run, with training seed 17 where applicable. At most two immutable submissions are evaluated before the unchanged task deadline; keep the better metric, breaking exact ties in favor of the earlier submission. Preserve both artifact hashes, feedback, timestamps, and statuses. Waiting for evaluation consumes the original task budget. A result arriving after the deadline does not permit additional training.

Report mean scores by tier, task coverage, raw metrics, failures, model/agent versions, and actual hardware. A missing valid final artifact receives zero under the completion policy. Infrastructure failures or unavailable official evaluation remain explicit pending/blocked outcomes, not invented zero scores. Never drop difficult tasks to improve an aggregate.

`mleb aggregate-experiment` requires a closed, frozen manifest bound to the task roster, system identity, protocol, and test provenance. The examples contain fictional scores. The protocol allows only the official track for benchmark reporting; library support for offline reference systems is available for separate learning experiments, not an automatic fallback for official evaluation.

The current heterogeneous resource pool does not establish a GPU-matched comparison. Medium/hard GPU allocation caps remain calibration proposals. Exact budgets and limitations are retained in [configs/protocol.json](configs/protocol.json).
