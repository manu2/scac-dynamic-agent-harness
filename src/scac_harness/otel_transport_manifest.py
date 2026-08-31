"""Validation for the frozen OTel/Toxiproxy cross-model pilot manifest."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Mapping


_CONDITIONS = {"A", "B", "C"}
_REGIMES = {"latency", "connection_error", "http_error"}
_ACTIONS = {"tool_alpha", "tool_beta", "wait"}


def validate_cross_model_pilot_manifest(manifest: Mapping[str, object]) -> None:
    """Reject incomplete, duplicate, or unbalanced v0.2 pilot declarations."""
    episodes = manifest.get("authorized_episodes")
    if not isinstance(episodes, list) or len(episodes) != 27:
        raise ValueError("v0.2 transport pilot must declare exactly 27 episodes")
    ids: set[str] = set()
    by_model: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    fault_counts: Counter[str] = Counter()
    first_action_counts: Counter[str] = Counter()
    for episode in episodes:
        if not isinstance(episode, Mapping):
            raise ValueError("episode must be an object")
        required = {"episode_id", "sequence", "provider_label", "model_id", "regime", "condition", "faulted_tool", "option_order"}
        if not required.issubset(episode):
            raise ValueError("episode is missing a frozen execution field")
        episode_id = episode["episode_id"]
        if not isinstance(episode_id, str) or episode_id in ids:
            raise ValueError("episode ids must be unique strings")
        ids.add(episode_id)
        if episode["regime"] not in _REGIMES or episode["condition"] not in _CONDITIONS:
            raise ValueError("episode has an unsupported regime or condition")
        if episode["faulted_tool"] not in {"tool_alpha", "tool_beta"}:
            raise ValueError("episode faulted_tool is invalid")
        order = episode["option_order"]
        if not isinstance(order, list) or set(order) != _ACTIONS or len(order) != 3:
            raise ValueError("episode option_order must contain every action exactly once")
        if not isinstance(episode["sequence"], int) or not 0 <= episode["sequence"] < 9:
            raise ValueError("episode sequence must be an integer in [0, 8]")
        by_model[(str(episode["provider_label"]), str(episode["model_id"]))].append(episode)
        fault_counts[str(episode["faulted_tool"])] += 1
        first_action_counts[str(order[0])] += 1
    if len(by_model) != 3:
        raise ValueError("v0.2 transport pilot must declare exactly three provider/model blocks")
    for key, block in by_model.items():
        if {episode["sequence"] for episode in block} != set(range(9)):
            raise ValueError(f"{key} does not have an exact 0..8 run sequence")
        if {(episode["regime"], episode["condition"]) for episode in block} != {
            (regime, condition) for regime in _REGIMES for condition in _CONDITIONS
        }:
            raise ValueError(f"{key} does not cover every regime/condition cell exactly once")
        for regime in _REGIMES:
            cells = [episode for episode in block if episode["regime"] == regime]
            if len({episode["faulted_tool"] for episode in cells}) != 1:
                raise ValueError(f"{key}/{regime} changes route assignment across conditions")
            if len({tuple(episode["option_order"]) for episode in cells}) != 1:
                raise ValueError(f"{key}/{regime} changes option order across conditions")
    # Route assignment must remain constant within the A/B/C triad for a
    # regime, so 27 cells can only be balanced to 15 versus 12.
    if abs(fault_counts["tool_alpha"] - fault_counts["tool_beta"]) > 3:
        raise ValueError("faulted route is not balanced across the 27 episodes")
    if abs(first_action_counts["tool_alpha"] - first_action_counts["tool_beta"]) > 3:
        raise ValueError("first listed tool is materially unbalanced across the 27 episodes")
