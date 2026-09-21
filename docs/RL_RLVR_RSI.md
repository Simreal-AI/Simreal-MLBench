# ML Benchmark as a learning environment for research agents

ML Benchmark can support learning at the level of **research decisions**: inspecting data, designing validation, writing training code, interpreting results, and selecting a final model. The learning policy is the research agent; the fitted predictor is its output.

## 1. Environment and implementation boundary

| Concept | ML research interpretation |
| --- | --- |
| Observation | Task objective, permitted inputs, schema, experiment history, tool outputs, resource status |
| Action | Read/write files, request training or inference, inspect logs, request permitted evaluation, finish |
| Transition | Controller-validated execution in a restricted worker |
| Terminal artifact | Frozen predictions, code, and reproducibility metadata |
| Verifier | Trusted metric computation on an identified validation partition |
| Budget | Wall-clock time and allocated CPU/GPU resources |

The administrator package implements the worker, restricted JSON gateway, submission freezing, two-attempt evaluation ledger, and local grading utilities. The public package supplies the client and scoring contracts. **It does not include a tested Gym adapter, RL weight trainer, or automatic RSI loop.**

Actions have variable duration and the agent sees only part of the environment state. A rollout adapter must preserve action IDs, timestamps, observations, remaining budget, generated artifacts, and termination reasons. Do not model every tool call as equal-cost progress.

## 2. Build a research environment

Follow [environment setup](SETUP.md) and [gateway setup](GATEWAY.md). The administrator first runs `mle_benchmark.runtime_selftest` without Docker: this checks the control flow on a synthetic regression task using a local fixture executor. Then run the same self-test with `--docker` on the actual worker host.

The default official benchmark uses 60 tasks with 6/12/24-hour budgets and official scoring. Build a **separate learning configuration** for shorter rollouts, local reward evaluation, or altered feedback frequency. Assign it a different experiment ID and record the differences. Reusing runtime components does not make a learning episode an official benchmark run.

The current remote wrapper is built for an externally orchestrated agent and permits one active remote Codex run per controller state root. An RL sampler needing parallel candidates must use independently provisioned state roots/controllers with a fixed shared resource scheduler, or implement and validate a dedicated multi-session adapter. Do not remove the existing concurrency guard casually.

## 3. Split data before learning

Use four roles:

1. **Exploration inputs:** visible to the agent, including its own internal validation.
2. **Reward fold:** controller-owned targets used to score training trajectories.
3. **Promotion fold/tasks:** compare agent revisions or checkpoints; its feedback also participates in selection.
4. **Final evaluation:** untouched tasks/splits used only after the agent, memory, reward, and protocol are frozen.

Split time series chronologically; group repeated subjects, patients, users, devices, entities, or near-duplicates together. Related modalities from the same underlying sample must stay in the same partition. For general research ability, reserve whole tasks or domains, not only rows of repeatedly visited tasks. Hash all split manifests.

The public competition test sets and their final leaderboard scores are not a reusable training reward oracle. Do not train against private benchmark test labels or adapt a research kit using final-test feedback. Official scoring remains official-only; local reward folds do not replace that protocol.

## 4. RLVR: learn from verified outcomes

The verifier validates prediction IDs, shapes and values, runs the declared metric, and checks artifact hashes and budgets. It evaluates predictions, not how convincing a model's explanation sounds. Verifiability means reproducibility under a pinned metric and dataset; it is not immunity to reward hacking or data leakage.

For a separate learning experiment, freeze a reference distribution of training-only baseline systems on the **same reward fold**. One candidate reward is:

```text
p_train = (strictly worse reference systems + 0.5 × tied systems) / N
reward = p_train²
```

This reuses the benchmark's percentile shape but not its official human leaderboard. Configure the supplied scoring library with `track="offline"`, `unit="reference_system"`, the exact reward-fold identity, and `frozen=true`; hash the reference with `seal_snapshot`. Divide its returned `quadratic_score` by 100. Require a nondegenerate reference distribution, matching metric direction and precision, and trusted predictions. This is a proposed learning reward, not a new official leaderboard score. Run `python examples/learning_reward.py` from an installed source checkout for a synthetic, credential-free demonstration (expected reward: 0.25).

Invalid agent outputs can receive zero under a predeclared validity rule. Infrastructure failures have missing reward and must be reconciled or explicitly excluded from the update, never recast as wrong predictions. Sparse percentile rewards may require training-only warm-start demonstrations or separately declared auxiliary feedback; ablate such changes.

A weight-training loop:

1. Sample an eligible task and frozen split; generate K trajectories from the current trainable policy under equal budgets.
2. Freeze each candidate artifact; the trusted reward service scores it on the reward fold.
3. Record assistant-generated tokens, tool calls/results, behavior-policy information required by the trainer, and reward provenance.
4. Update the policy with an appropriate algorithm such as GRPO. Apply language-model loss to generated assistant tokens, not externally returned tool outputs.
5. Compare checkpoints on promotion tasks; freeze the selected one before final evaluation.

[TRL's GRPO documentation](https://huggingface.co/docs/trl/grpo_trainer) provides a trainer integration reference. A benchmark-specific rollout/reward adapter and version-pinned integration tests still need to be built. [DeepSeek-R1](https://arxiv.org/abs/2501.12948) motivates outcome-based RL on verifiable tasks; it is not evidence of an RL-trained agent on this benchmark.

## 5. API agents and reusable research skills

An inference-only API does not expose model-weight updates. It can still support experiments that improve a versioned research kit: validation templates, feature pipelines, diagnostic scripts, error-repair procedures, experiment-selection heuristics, and compact evidence-based memory.

```text
research trajectories -> verified reward-fold outcomes
  -> proposed research-kit revision
  -> fresh equal-budget promotion runs
  -> accept or reject revision
```

Measure whether the revised kit helps solve new tasks, rather than simply retaining predictions or labels from a previous task. Keep hidden labels, official test outcomes, and source-specific solution leakage out of reusable memory. Report token/tool costs and additional learning compute separately from per-task evaluation budgets.

## 6. Recursive self-improvement (RSI)

Here RSI means improving the **research agent**, potentially including the code that proposes and tests its own successors. Ordinary predictor hyperparameter tuning is not evidence of recursive agent improvement.

Allow revisions to the planner, task decomposition, context management, experiment selection, reusable skills, and explicitly allowlisted improvement code. Keep dataset access, deadlines, metric code, verifier, acceptance threshold, and final evaluation under a fixed external controller.

For each generation, the champion proposes a challenger. Test both on the same promotion tasks, seeds, budgets, and resource policy in fresh workspaces. Predeclare acceptance criteria covering mean reward, task completion, cost, and unacceptable regressions. Retain the parent if the challenger fails; archive lineage, code hashes, outcomes, and rejection reasons. The accepted successor proposes the next generation. Freeze the final lineage and memory before the untouched final evaluation.

[Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) studies empirical self-improvement of agent code. It motivates this experimental design; its published results do not establish ML Benchmark gains.

Use matched controls: fixed agent, strategy-search-only, memory-only adaptation, and agent-code revisions. Report per-task paired results, multiple independent runs when feasible, hardware contention, rollout count, failure handling, and total search cost. Improvements must survive fresh tasks and an unchanged verifier. This release contains a protocol for such an experiment, not a claim of measured RLVR or RSI improvement.
