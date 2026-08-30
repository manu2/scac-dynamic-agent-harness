"""Model-visible RetryBudget v0.2 observation and A/B/C prompt contract.

This is intentionally a pure renderer. It neither changes the host-owned state
machine nor invokes a model, which keeps future agent execution isolated from
the scenario oracle and observation construction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from scac_harness.scenarios.retry_budget import RetryAction, RetryBudgetOracle, RetryState


RetryBudgetCondition = Literal["A", "B", "C"]
_CONDITIONS: tuple[RetryBudgetCondition, ...] = ("A", "B", "C")
_FIELD_NAMES: tuple[str, ...] = (
    "work_item",
    "decision_steps_remaining",
    "deadline_remaining_ms",
    "primary_status",
    "remaining_quota",
    "retry_after_ms",
    "fallback_available",
    "fallback_utility",
    "checkpoint_available",
    "checkpointed",
    "checkpoint_recovery_utility",
)


@dataclass(frozen=True)
class RetryBudgetObservationModel:
    """Versioned full-checkpoint observation assumptions for v0.2 development."""

    version: str = "synthetic_host_lifecycle_v0.2"
    delivery_delay_ms: int = 0
    missing_field_probability: float = 0.0
    value_corruption_probability: float = 0.0

    def __post_init__(self) -> None:
        if self.delivery_delay_ms < 0:
            raise ValueError("delivery_delay_ms must be non-negative")
        for value in (self.missing_field_probability, self.value_corruption_probability):
            if not 0.0 <= value < 1.0:
                raise ValueError("observation probabilities must be in [0, 1)")


def _option_order(seed: int, state: RetryState) -> tuple[RetryAction, ...]:
    """Rotate all labels deterministically so fixed label position is unhelpful."""
    actions = list(RetryBudgetOracle.ACTIONS)
    # Across any five adjacent seeds every action occupies every position for
    # the same work-item/step state. This stronger property is preferable to a
    # pseudo-random permutation for the initial balanced seed block.
    shift = (seed + state.work_item + state.decision_steps_remaining) % len(actions)
    return tuple(actions[shift:] + actions[:shift])


def observable_projection(state: RetryState, model: RetryBudgetObservationModel) -> dict[str, object]:
    """Return the complete host-owned v0.2 primary-oracle input projection.

    The current baseline has no observation loss/corruption; non-zero model
    settings are rejected for now rather than silently fabricating a sensitivity
    model. A later calibrated implementation must replace this fail-closed
    boundary before it can use non-zero settings.
    """
    if model.missing_field_probability != 0.0 or model.value_corruption_probability != 0.0:
        raise NotImplementedError("RetryBudget v0.2 non-zero observation perturbation is not calibrated")
    projection = asdict(state)
    projection["observation_source"] = model.version
    projection["delivery_delay_ms"] = model.delivery_delay_ms
    projection["state_delivery"] = "independent_full_checkpoint"
    return projection


def _render_state_block(values: dict[str, object], *, neutral: bool) -> str:
    lines = ["[HOST-OWNED RETRYBUDGET STATE — FULL CHECKPOINT]"]
    for name in _FIELD_NAMES:
        value = "NEUTRAL" if neutral else values[name]
        lines.append(f"{name}={value}")
    lines.append("observation_source=NEUTRAL" if neutral else f"observation_source={values['observation_source']}")
    lines.append("delivery_delay_ms=NEUTRAL" if neutral else f"delivery_delay_ms={values['delivery_delay_ms']}")
    lines.append("state_delivery=NEUTRAL" if neutral else f"state_delivery={values['state_delivery']}")
    return "\n".join(lines) + "\n"


def build_prompt(
    *,
    condition: RetryBudgetCondition,
    seed: int,
    state: RetryState,
    observation_model: RetryBudgetObservationModel = RetryBudgetObservationModel(),
) -> str:
    """Build one exact-label decision prompt without a hidden recommendation."""
    if condition not in _CONDITIONS:
        raise ValueError(f"unknown RetryBudget condition: {condition}")
    options = _option_order(seed, state)
    task = (
        "Task: choose the next operational action for one pending work item. "
        "retry attempts the primary service; wait preserves work until a declared recovery; "
        "fallback uses the declared alternative; checkpoint preserves recoverable progress; "
        "terminate safely ends the work item. Return exactly one listed action label and no other text.\n"
        "Options: " + ", ".join(options) + "\n"
    )
    if condition == "A":
        return task
    projection = observable_projection(state, observation_model)
    return task + _render_state_block(projection, neutral=condition == "B")


def prompt_record(
    *,
    condition: RetryBudgetCondition,
    seed: int,
    state: RetryState,
    observation_model: RetryBudgetObservationModel = RetryBudgetObservationModel(),
) -> dict[str, object]:
    """Create an auditable, side-effect-free record for a future episode."""
    prompt = build_prompt(
        condition=condition, seed=seed, state=state, observation_model=observation_model,
    )
    return {
        "kind": "retrybudget_v0_2_independent_full_checkpoint_prompt",
        "condition": condition,
        "seed": seed,
        "work_item": state.work_item,
        "decision_steps_remaining": state.decision_steps_remaining,
        "option_order": list(_option_order(seed, state)),
        "prompt": prompt,
        "prompt_characters": len(prompt),
        "visible_projection": observable_projection(state, observation_model) if condition == "C" else None,
        "observation_model": asdict(observation_model),
    }
