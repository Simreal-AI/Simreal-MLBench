# ML Benchmark

**A verifiable environment for machine learning research agents.**

An agent studies a dataset, develops a modeling approach, runs experiments, and submits predictions. ML Benchmark brings together **60 tasks across tabular learning, forecasting, vision, language, audio, multimodal learning, and structured scientific data**.

The benchmark targets the full research process: data understanding, feature engineering, validation design, model selection, hyperparameter tuning, ensembling, debugging, resource allocation, and reliable delivery.

| Tier | Tasks | Research budget | Compute |
| --- | ---: | ---: | --- |
| Easy | 20 | 6 hours | CPU |
| Medium | 20 | 12 hours | Heterogeneous GPU pool |
| Hard | 20 | 24 hours | Heterogeneous GPU pool |

## What makes the numbers trustworthy

**The scorer is not us.** Test labels stay with the competition platform. We
never hold the answers, so an agent cannot read them and we cannot get the
split wrong. Suites that carve their own holdout out of training data inherit
a class of bug this design does not have.

**Agents get a second submission, with a real score in between.** Most
evaluations are one shot. Two submissions with honest feedback between them
make a different question measurable: not only how well an agent performs,
but whether it can act on the truth once it has it.

**Source-blind by enforcement, not by convention.** Task briefs are checked at
load time for platform names, competition identities, and URLs. An agent
cannot recognise which competition it is solving and recall a published
solution.

**Every reward is attacked before it ships, and the bypass count is
published** — including the false positive our own attack tool produced on
its first run. A report that measures overclaiming cannot overclaim.

**Full provenance.** Every number carries the submission id, artifact hash,
and frozen reference snapshot it came from.

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

The [technical report](reports/REPORT.md) records three verified admission baselines and the current implementation boundary. Full-suite admission and hardware calibration are ongoing; this release does not claim a completed 60-task agent leaderboard.

## Learning research agents

The task/tool loop provides an environment for sequential research decisions; executable evaluation provides a verifiable outcome. This supports RLVR experiments and agent-level recursive self-improvement through versioned research memory, skills, and agent code. See [RL, RLVR and RSI](docs/RL_RLVR_RSI.md) for the proposed learning protocol and required trainer integration.

## Repository contents

This public package includes task definitions, the remote-client SDK, scoring and aggregation utilities, examples, tests, data-access tooling, and the report. The separate administrator distribution contains the worker controller, submission broker, local graders, dashboard, and deployment files. It is not included in the public repository.

[Agent guide](AGENT_GUIDE.md) · [Environment setup](docs/SETUP.md) · [Gateway](docs/GATEWAY.md) · [Release structure](docs/RELEASING.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Inspired by [MLE-bench](https://github.com/openai/mle-bench), with a distinct task selection, resource protocol, and scoring scheme.
