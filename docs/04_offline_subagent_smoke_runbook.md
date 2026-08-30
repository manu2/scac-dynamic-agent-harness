# Offline Fresh-Subagent Smoke Runbook

This runbook is for development-only checks. It does not authorize provider
calls and it does not create paper-study data. Fresh Codex subagents share the
repository filesystem and therefore are not blinded to hidden schedules.

## One trajectory

1. Start exactly one condition and save the emitted `trial_dir` and
   `subject_prompt`:

   ```sh
   .venv/bin/python -m scac_harness.smoke_cli start --seed 101 --condition C
   ```

2. Spawn a fresh subagent with `fork_turns="none"`. Give it only the emitted
   `subject_prompt`, verbatim. Do not concatenate, trim, reformat, or add an
   instruction. The CLI freezes the exact condition message plus a constant
   double-newline delimiter and subject-only instruction in
   `turn-XX-handoff.json`.

3. Submit its exact, unedited response. The command rejects extra prose or an
   invalid action, archives the malformed response as a rejection artifact, and
   leaves the turn pending for a fresh replacement subagent:

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
per condition; do not compare different seeds as matched trajectories. Run
whole six-seed blocks (`0–5`, `6–11`, and so on) so all option permutations are
balanced. Record every malformed or refused response as-is. Do not edit or
delete any `experiments/dev-smoke/` directory.

## Interpretation boundary

Use these records to find broken capture, prompt, parsing, or evaluator logic.
Do not report them as blinded model evidence, pool them with a later API study,
or claim a treatment effect from them.
