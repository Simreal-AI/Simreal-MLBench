# ML Benchmark: design and verification report

## Scope

ML Benchmark is a 60-task collection for autonomous machine learning research: 20 easy, 20 medium, and 20 hard tasks. The task budgets are 6, 12, and 24 hours. Modalities include tabular data, time series, language, images, audio, and structured or multimodal scientific inputs.

An evaluated system is a model plus its agent implementation, version, configuration, and resource environment. Research includes data analysis, validation, feature engineering, model training, tuning, selection, and submission. The primary evidence is the frozen artifact's official metric, mapped against an identified frozen reference distribution.

## Evaluation contract

Use all permitted original training data; internal validation is chosen by the agent. Allow at most two immutable official submissions under the original deadline. Keep the better result and preserve both attempts. Compute `100 × p²`, with half credit for tied reference scores. Report tier means, coverage, actual hardware, and failures. See [SCORING.md](../SCORING.md).

## Available empirical evidence

The following records were saved on 2026-09-15. They are **local CPU admission baselines evaluated through official scoring**, not autonomous-agent results or a model leaderboard.

| Task | Official raw score (lower is better) | Reference teams | Task score / 100 |
| --- | ---: | ---: | ---: |
| leaf-classification | 0.10465 | 1,595 | 25.19 |
| spooky-author-identification | 0.43122 | 1,241 | 22.07 |
| bike-sharing-demand | 0.42634 | 3,242 | 70.13 |

Leaf Classification and Spooky Author Identification use multiclass log loss; Bike Sharing Demand uses RMSLE. The records identify the final private split, reference snapshot hash, and submitted artifact hash. [results.json](results.json) preserves these fields and the source artifact hash. `python scripts/verify_report.py` recomputes the three percentile/score mappings from saved counts; it does not authenticate scores against the live platform or redistribute the complete historical leaderboards.

No comparative model claim is inferred from these baselines. Other short diagnostic calls in the development workspace are excluded: they are not a closed 60-task experiment, and requested model names alone do not prove upstream model identity.

## Implemented components

- Public task catalog, remote client, reference scoring, and experiment aggregation.
- Administrator worker queues, restricted JSON gateway, resource accounting, submission freezing, checkpoint ledger, and local pilot graders.
- CPU/GPU Docker build definitions, download/inventory tools, dashboard, and recovery commands.
- A synthetic runtime self-test spanning file access, CPU training, two frozen evaluations, feedback, and best-result selection.

## Learning research agents

A research session naturally supplies observations, actions, transitions, and an executable outcome. For RLVR, attach trusted metrics from a separate training reward fold to research trajectories and connect them to a trainable policy. For API agents, improve a reusable research kit. For recursive self-improvement, allow agent-code revisions while keeping the verifier and acceptance policy fixed. The complete proposed architecture, setup, data partitions, reward contract, and controls are in [RL/RLVR/RSI](../docs/RL_RLVR_RSI.md).

These are supported research directions, not completed RL training results. The release does not provide a tested weight trainer or automatic recursive improvement loop.

## Limits and interpretation

Full-suite admission, data-access review, hardware calibration, and complete comparable agent runs remain unfinished. Hardware is heterogeneous and contention must be reported. Source blinding cannot establish absence of contamination. Repeated reward/promotion feedback is training information; it must remain separate from final evaluation. Official scoring availability must be rechecked when launching a campaign.

Public-package checks are recorded in `VALIDATION.json`; administrator runtime checks are recorded in the separate administrator package. Historical development checks are not presented as fresh Ubuntu, GPU, SSH, or provider verification.
