"""Execute one frozen ToolRoute provider cohort without retries.

Every model decision receives an independent full checkpoint.  Condition B is
constructed with the selected provider's native token counter; the episode
constructor fails before generation if B cannot exactly match C.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from scac_harness.toolroute_api import (
    AnthropicMessagesProvider, GeminiGenerateContentProvider,
    AuthorizationBoundTokenizer, OpenAICompatibleProvider, ToolRouteAPIEpisode,
    ToolRouteAuthorization,
)


def _load_dotenv(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _provider(label: str, model: str):
    if label == "openai":
        return OpenAICompatibleProvider(endpoint="https://api.openai.com/v1/chat/completions", api_key=os.environ["OPENAI_API_KEY"], model=model)
    if label == "anthropic":
        return AnthropicMessagesProvider(api_key=os.environ["ANTHROPIC_API_KEY"], model=model, api_version="2023-06-01")
    if label == "google":
        return GeminiGenerateContentProvider(api_key=os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"], model=model)
    raise ValueError(f"unknown provider: {label}")


def _episodes(manifest: dict[str, object], label: str, model: str) -> list[tuple[int, int, str]]:
    result = []
    for grid in manifest.get("authorized_episode_grids", []):
        if not isinstance(grid, dict) or grid.get("provider_label") != label or grid.get("model_id") != model:
            continue
        for seed in grid["seeds"]:
            for turn in grid["turns"]:
                for condition in grid["conditions"]:
                    result.append((seed, turn, condition))
    # Deterministic execution randomization, frozen by the manifest's salt.
    salt = str(manifest["execution_randomization_salt"])
    return sorted(result, key=lambda item: hashlib.sha256(f"{salt}:{label}:{model}:{item}".encode()).hexdigest())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("openai", "anthropic", "google"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, default=Path("PROVENANCE.json"))
    parser.add_argument("--dotenv", type=Path, default=Path(".env"))
    parser.add_argument("--experiments-root", type=Path, default=Path("experiments/api-cohort"))
    args = parser.parse_args()
    _load_dotenv(args.dotenv)
    authorization = ToolRouteAuthorization.load(provenance_path=args.provenance, pilot_manifest_path=args.manifest)
    authorization.verify_live()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    provider = _provider(args.provider, args.model)
    tokenizer = AuthorizationBoundTokenizer(
        authorization, f"{args.provider}-native-count-endpoint:{args.model}", provider.count_tokens,
    )
    episodes = _episodes(manifest, args.provider, args.model)
    if not episodes:
        raise RuntimeError("no authorized episodes for requested provider/model")
    for seed, turn, condition in episodes:
        authorization.verify_live()
        episode = ToolRouteAPIEpisode(seed=seed, turn=turn, condition=condition, experiments_root=args.experiments_root,
                                      tokenizer=tokenizer, model_id=args.model, provider_label=args.provider)
        result = episode.run(provider, authorization=authorization)
        print(json.dumps({"seed": seed, "turn": turn, "condition": condition,
                          "classification": result["classification"], "directory": str(episode.directory)}, flush=True)


if __name__ == "__main__":
    main()
