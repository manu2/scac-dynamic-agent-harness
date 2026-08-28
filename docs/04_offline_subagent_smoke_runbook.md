# Offline Fresh-Subagent Smoke Runbook

This runbook is for development-only checks. It does not authorize provider
calls and it does not create paper-study data. Fresh Codex subagents share the
repository filesystem and therefore are not blinded to hidden schedules.

## One trajectory

1. Start exactly one condition and save the emitted `trial_dir` and `message`:

   ```sh
   .venv/bin/python -m scac_harness.smoke_cli start --seed 101 --condition C
   ```

2. Spawn a fresh subagent with `fork_turns="none"`. Give it only the emitted
   `message` and this instruction: “Do not inspect the workspace or use tools.
   Reply with exactly one action label and nothing else.”

3. Submit its exact, unedited response. The command rejects extra prose or an
   invalid action:

   ```sh
   .venv/bin/python -m scac_harness.smoke_cli submit \
     --trial-dir '<emitted trial_dir>' --subject-id '<fresh agent id>' \
     --response '<exact response>'
   ```

4. If the result is not terminal, generate the next message and repeat from
   step 2:

   ```sh
   .venv/bin/python -m scac_harness.smoke_cli next --trial-dir '<trial_dir>'
   ```

## Required development matrix

Run complete trajectories for A, B, and C at each seed. Use the same seed once
per condition; do not compare different seeds as matched trajectories. Start
with 8–12 seeds, counterbalance the condition order, and record every malformed
or refused response as-is. Do not edit or delete any `experiments/dev-smoke/`
directory.

## Interpretation boundary

Use these records to find broken capture, prompt, parsing, or evaluator logic.
Do not report them as blinded model evidence, pool them with a later API study,
or claim a treatment effect from them.
