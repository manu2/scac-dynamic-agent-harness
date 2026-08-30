"""Run the separately authorized RetryBudget v0.2 Gemini development canary."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from scac_harness.retry_budget_api import RetryBudgetAPITrajectory, RetryBudgetAuthorization
from scac_harness.toolroute_api import GeminiGenerateContentProvider


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiments-root", default="experiments")
    parser.add_argument("--manifest", default="manifests/retrybudget_api_canary.v0.2.json")
    parser.add_argument("--provenance", default="PROVENANCE.json")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    authorization = RetryBudgetAuthorization.load(
        provenance_path=Path(args.provenance), manifest_path=manifest_path,
    )
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"required API key environment variable {args.api_key_env!r} is unset")
    provider = GeminiGenerateContentProvider(
        api_key=api_key, model="gemini-3.7-flash", temperature=0.0, max_output_tokens=16,
    )
    trajectory = RetryBudgetAPITrajectory(
        seed=61,
        condition="C",
        experiments_root=Path(args.experiments_root),
        model_id="gemini-3.7-flash",
        provider_label="google",
        pilot_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )
    print(trajectory.run(provider, authorization=authorization))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
