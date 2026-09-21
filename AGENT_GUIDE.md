# Research-agent contract

Receive a neutral task description, reviewed input files, output schema, metric, and resource budget. The controller assigns one run. Solve the task independently: inspect data, choose validation, implement models, run experiments, and produce predictions matching the required schema.

## Files and artifacts

Inputs are read-only under `/data`; working files and training outputs are under `/work` in the worker. Keep `submission.csv` in the assigned work directory. Record experiments in `EXPERIMENTS.md` and explain final model selection in `SUMMARY.md`. Preserve code, seeds, dependency versions, and model artifacts required for reproduction. Task-specific formats take precedence over the illustrative CSV name when explicitly supported by the operator.

The agent cannot access evaluation labels, credentials, historical leaderboards, or other agents' results. Preload approved packages and weights: training workers do not have Internet access. Source blinding does not prove absence of pretraining contamination.

## Research loop

1. Read the assigned task and inspect input schemas.
2. Establish a valid baseline and an appropriate validation split.
3. Form a hypothesis, change the pipeline, run a bounded job, and inspect the result.
4. Keep a valid final artifact throughout the remaining budget.
5. Request at most two official evaluations; use raw feedback without extending the deadline.
6. Finish the run after selecting the final artifact.

Use the assigned JSON gateway operations in [sdk/requests.json](sdk/requests.json). Jobs return an ID and are polled through `job-status`. Evaluation retries reuse the same request ID to avoid duplicate submissions. File writes use base64 content. The client is described in [gateway setup](docs/GATEWAY.md).

`finish` requests terminal processing and stops further research. The ML gateway does not implement Trading's preview/confirmation-token protocol. Before finishing, save the selected submission and experiment records; the controller may use a remaining evaluation slot for a distinct trusted predeadline artifact.

## Resource limits

Easy: 6 hours; medium: 12 hours; hard: 24 hours. Queue and evaluation waiting count toward the original task deadline. Record resource use and failures; do not restart a run with a fresh budget to hide an unsuccessful attempt. Status responses identify the assigned deadline and any stop reason.
