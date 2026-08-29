"""Run one explicitly manifest-authorized, non-paper ToolRoute transport smoke.

The script reads a local dotenv file only into its process environment and
never prints credentials. It refuses A/B because tokenizer-matched controls
belong to the later balanced cohort, not this C-only transport diagnostic.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from scac_harness.toolroute_api import (
    AnthropicMessagesProvider, GeminiGenerateContentProvider, OpenAICompatibleProvider,
    Tokenizer, ToolRouteAPIEpisode, ToolRouteAuthorization, WhitespaceTokenizer,
)


def _load_dotenv(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'") )


def _provider(label: str, model: str):
    if label == "google":
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
        return GeminiGenerateContentProvider(api_key=key, model=model)
    if label == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required")
        return OpenAICompatibleProvider(endpoint="https://api.openai.com/v1/chat/completions", api_key=key, model=model)
    if label == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required")
        return AnthropicMessagesProvider(api_key=key, model=model, api_version="2023-06-01")
    raise ValueError(f"unknown provider label: {label}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("google", "openai", "anthropic"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dotenv", type=Path, default=Path(".env"))
    parser.add_argument("--manifest", type=Path, default=Path("manifests/toolroute_api_transport_smoke.v0.6.json"))
    parser.add_argument("--provenance", type=Path, default=Path("PROVENANCE.json"))
    args = parser.parse_args()
    _load_dotenv(args.dotenv)
    authorization = ToolRouteAuthorization.load(provenance_path=args.provenance, pilot_manifest_path=args.manifest)
    episode = ToolRouteAPIEpisode(seed=0, turn=1, condition="C", experiments_root=Path("experiments/api-transport-smoke"),
                                  tokenizer=Tokenizer(WhitespaceTokenizer.name, WhitespaceTokenizer.count),
                                  model_id=args.model, provider_label=args.provider)
    result = episode.run(_provider(args.provider, args.model), authorization=authorization)
    print(f"trial_directory={episode.directory}")
    print(f"classification={result['classification']}")


if __name__ == "__main__":
    main()
