# ML Benchmark by Simreal (Simreal.co)

**An externally scored, verifiable evaluation environment for machine learning research agents.**
**Open protocol. Operated evaluation.**

An agent studies a dataset, develops a modeling approach, runs experiments, and submits predictions. ML Benchmark brings together **60 tasks across tabular learning, forecasting, vision, language, audio, multimodal learning, and structured scientific data**.

The benchmark targets the full research process: data understanding, feature engineering, validation design, model selection, hyperparameter tuning, ensembling, debugging, resource allocation, and reliable delivery.

| Tier | Tasks | Research budget | Compute |
| --- | ---: | ---: | --- |
| Easy | 20 | 6 hours | CPU |
| Medium | 20 | 12 hours | Heterogeneous GPU pool |
| Hard | 20 | 24 hours | Heterogeneous GPU pool |

## Positioning

ML Benchmark is built as two layers, and we release them differently on purpose.

**The open layer is the standard.** Task definitions, the evaluation protocol, the scoring rule, and the verification tooling are public under Apache-2.0. Anyone can read exactly how a number is produced and recompute every published score. A benchmark result should never depend on trusting us.

**The operated layer is the service.** The evaluation runtime is a commercial product operated by Simreal. It runs agents in isolated workers behind a restricted gateway, enforces budgets and the two-submission rule, freezes every artifact, and routes submissions to official scoring. Labs and teams evaluate agents through this service rather than self-hosting it.

This split keeps the rules transparent while the infrastructure that enforces them stays under operational control.

## What makes the numbers trustworthy

**The scorer is not us.** Test labels stay with the competition platform. We never hold the answers, so an agent cannot read them and we cannot get the split wrong. Suites that carve their own holdout out of training data inherit a class of bug this design does not have.

**Agents get a second submission, with a real score in between.** Most evaluations are one shot. Two submissions with honest feedback between them make a different question measurable: not only how well an agent performs, but whether it can act on the truth once it has it.

**Source-blind by enforcement, not by convention.** Task briefs are checked at load time for platform names, competition identities, and URLs, so the brief itself never reveals the source. This reduces, but cannot eliminate, the chance that an agent recognises a well-known dataset; the [report](reports/REPORT.md) states this limit explicitly.

**Every reward is attacked before it ships.** Rewards are probed with adversarial submissions before a task is admitted.
<!-- TODO: link the public bypass-count report here before restoring the claim "the bypass count is published". -->

**Full provenance.** Every number carries the submission id, artifact hash, and frozen reference snapshot it came from.

## Architecture

```
Agent (any model / framework)
   │  JSON tool calls via mleb-remote            ← public SDK
   ▼
Restricted gateway (forced-command SSH)          ┐
   │  validates run identity and file paths      │
   ▼                                             │  Simreal-operated
Controller + worker queues                       │  evaluation runtime
   │  containerised training jobs, resource      │
   │  accounting, checkpoint ledger              │
   ▼                                             │
Submission broker                                │
   │  freezes artifacts, enforces 2 submissions  ┘
   ▼
Official competition scoring                     ← external, holds the labels
   │
   ▼
Scoring + aggregation (100 × p²)                 ← public, recomputable
```

The agent only ever sees its own assigned run. It cannot reach training data outside its directory, the evaluation files, or the scoring credentials.

## Open-source scope

| Component | Availability |
| --- | --- |
| Task definitions and catalog | Public (Apache-2.0) |
| Evaluation protocol and budgets | Public (Apache-2.0) |
| Remote-client SDK (`mleb-remote`) | Public (Apache-2.0) |
| Scoring and aggregation utilities | Public (Apache-2.0) |
| Examples, tests, data-access tooling | Public (Apache-2.0) |
| Technical report and verification scripts | Public (Apache-2.0) |
| Gateway, controller, and worker queues | Simreal evaluation service |
| Submission broker and official-scoring route | Simreal evaluation service |
| Local graders, dashboard, deployment | Simreal evaluation service |

**What you can verify with the public package alone**

- Validate the task catalog and protocol configuration.
- Read the exact scoring code and recompute every published task score from saved reference counts.
- Check the submission id, artifact hash, and reference snapshot hash behind every reported number.

**What the evaluation service provides**

- End-to-end agent runs under the official protocol, on managed CPU and GPU workers.
- Official two-submission scoring with full provenance records.
- Results eligible for official benchmark reporting.

To evaluate an agent, contact us at [business@simreal.co](mailto:business@simreal.co). Integration uses the public SDK; see the [Gateway guide](docs/GATEWAY.md).

## Quick start

Python 3.11+; Python 3.12 is the locally tested version.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
mleb validate configs/catalog.json
mleb grade examples/snapshot.json examples/result.json
python scripts/verify_report.py
python -m pytest -q
```

These commands run local examples without credentials or model calls. See the [task catalog](CATALOG.md) and [data access guide](data-access/README.md) for the original competition datasets, which are acquired separately.

## Research and evaluation

Agents use all permitted original training data, select their own validation strategy, and receive at most two official submissions within the original deadline. The better official result is retained.

The task score is **100 × p²**, where `p` is the fraction of a matching frozen reference leaderboard outperformed, with half credit for ties. Report tier means together with coverage and actual resource usage. See [SCORING.md](SCORING.md).

## Release status

| Area | Status |
| --- | --- |
| 60-task catalog and protocol | Released |
| Scoring, aggregation, verification tooling | Released, 35 tests passing |
| Evaluation runtime (gateway, controller, broker, graders) | Implemented, operated by Simreal |
| Official-scoring baselines | 3 tasks verified end to end ([report](reports/REPORT.md)) |
| Full-suite admission and hardware calibration | In progress |
| Comparable 60-task agent leaderboard | Planned |

We publish only what has been verified. Numbers appear here when they carry full provenance, not before.

## Learning research agents

The task/tool loop provides an environment for sequential research decisions; executable evaluation provides a verifiable outcome. This supports RLVR experiments and agent-level recursive self-improvement through versioned research memory, skills, and agent code. See [RL, RLVR and RSI](docs/RL_RLVR_RSI.md) for the proposed learning protocol and required trainer integration. These are supported research directions; this release does not include trained results.

## Links

[Agent guide](AGENT_GUIDE.md) · [Environment setup](docs/SETUP.md) · [Gateway](docs/GATEWAY.md) · [Release structure](docs/RELEASING.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Inspired by [MLE-bench](https://github.com/openai/mle-bench), with a distinct task selection, resource protocol, and scoring scheme.
