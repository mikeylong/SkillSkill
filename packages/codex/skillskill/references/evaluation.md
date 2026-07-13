# Skill Evaluation Protocol

Use this protocol for benchmarks, consequential revisions, regressions, and release decisions. Pre-register the basket and gates before viewing candidate results.

## Preserve Provenance

Record the candidate and incumbent paths, commit or content hash, installed runtime path, platform and agent version, date, available capabilities, prompt IDs, fixture sources or hashes, commands, evaluator, and scoring criteria. Preserve raw prompts, outputs, artifacts, logs, and failures. Mark any uncontrolled difference.

## Build Prompt Baskets

Use raw, realistic user requests. Include no diagnosis, intended fix, expected answer, or rubric language in trial prompts.

### Minimal Basket

Use for a fast audit or low-risk revision:

- Routing: 3 positive prompts covering direct, paraphrased, and implicit intent.
- Routing: 3 negative prompts covering the nearest competing skill, a false friend, and an out-of-scope request.
- Invocation: 1 explicit `$skill-name` prompt, scored separately from automatic routing.
- Execution: 2 representative tasks, 1 edge or fallback task, and 1 authority or safety task.

### Release Basket

Use before publishing a new version:

- Routing: at least 8 positives across direct, paraphrased, implicit, and ambiguous-boundary language.
- Routing: at least 8 negatives across nearest competitors, native-owner tasks, false friends, and broad domain mentions.
- Invocation: at least 2 explicit invocations.
- Execution: 5 representative tasks, 3 edge or fallback tasks, 2 capability-composition tasks, 2 authority or safety tasks, 2 packaging or portability tasks when applicable, and every known prior regression.

Increase the basket for high-risk or highly variable skills. Document and justify reductions.

## Test Metadata-Only Routing

Give a fresh agent only the raw user prompt plus registry metadata for the candidate and its nearest competitors. Do not provide any skill body. Ask it to select which skill, if any, should run. Randomize metadata order.

Score automatic routing with true positives, false negatives, true negatives, and false positives. Report positive recall and negative-case specificity. Score explicit invocation separately because it does not demonstrate metadata quality. Inspect every false positive and false negative; aggregate percentages alone can hide dangerous boundaries.

## Run Execution A/B Tests

Compare an incumbent or no-skill baseline (A) with the candidate (B); add another variant only when it answers a specific question.

1. Give each variant the same raw task, capability set, and clean copy of the fixture.
2. Start a fresh agent or thread for every trial. Do not call the task a test unless test framing is part of real usage.
3. Mention `$skill-name` only for explicit-invocation trials.
4. Prevent agents from seeing other outputs, prior trial files, suspected defects, intended fixes, or expected results.
5. Blind and randomize variant labels before judging when practical.
6. Score task success, contract compliance, authority, safety, correctness, and handoff quality with predeclared criteria.
7. Compare artifacts and side effects, not only prose style.

Treat a forward test as contaminated if success depends on leaked context. Rerun it with a fresh agent and clean fixture.

## Apply Release Gates

Set stricter task-specific gates when risk warrants. Use these defaults when none exist:

- **Static:** Pass the authoritative platform validator, documented commands, link and asset checks, and runtime/source drift check.
- **Routing:** Route every explicit invocation; achieve at least 90% positive recall and 90% negative specificity; allow no false positive on a safety-critical or native-owner prompt.
- **Execution:** Pass every critical and authority/safety case; introduce no critical regression; match or beat the incumbent on at least 90% of critical tasks and 80% of all tasks.
- **Provenance:** Preserve enough evidence for another evaluator to reproduce the result.
- **Findings:** Resolve every High finding or record an explicit release exception from the user.

Do not average away a failed safety or authority gate. Report unstable, tied, or underpowered results honestly.

## Protect Safety And Scope

Run write-capable tests in isolated temporary workspaces. Stub or sandbox destructive tools, external messaging, purchases, deployments, secrets, and production data unless the user explicitly authorizes live effects. Stop and request authority when evaluation would cause material external change, incur meaningful cost, or expose protected data.

## Report Results

Return the basket manifest, provenance, routing confusion counts, per-task A/B outcomes, gate results, regressions, limitations, and retained artifacts. Keep static validation separate from behavioral evidence and label unrun trials `Not tested`.
