# ToolRoute v1.0 Execution-Configuration Clarification

## Scope

This record clarifies, without altering, the frozen paper manifest
`manifests/toolroute_api_paper.v1.0.json` (SHA-256
`9fb8003e4742b3e94afd872a88522cbe5d238d13ae631c1f0f30c78705789218`).
The machine-enforced companion is
`manifests/toolroute_api_paper.v1.0.execution-config.json` (SHA-256
`d1cba39f9aec08082d52207aef79a8c0845ff2fccecf528dcf7ebb8bfec45f78`);
its SHA-256 must be bound in `PROVENANCE.json` before a later cohort episode is
authorized.
It applies to the seed-8 paper block only and to any later authorized episode
that is explicitly bound to this clarification.

## Observed effective request configuration

| Provider/model | Effective sampling setting |
| --- | --- |
| OpenAI `gpt-5.6-sol` | no temperature field supplied |
| Anthropic `claude-sonnet-5` | no temperature field supplied |
| Google `gemini-3.7-flash` | `generationConfig.temperature: 0.0` supplied |

All providers used the frozen output limit of 1024 and no provider-native tool,
function, server-side state, or retry field. The Gemini setting is visible in
all 12 sanitized seed-8 `provider-request.json` artifacts.

## Interpretation and continuation rule

The manifest's phrase "sampling controls omitted; provider defaults" was
incorrect for Gemini. This is a documentation deviation, not a treatment
confound: Gemini's A, B, and C decision requests all used exactly the same
`temperature: 0.0`, and the artifacts make the setting auditable. Seed 8 stays
in the paper denominator.

Do not remove or change Gemini's temperature for later cohort episodes: doing
so would introduce the actual cohort discontinuity. Before any resumption, the
authorization record must bind this clarification along with the original
manifest and must state that all remaining Gemini calls retain
`temperature: 0.0`. The paper methods and artifact release must report the
effective settings above and this clarification. This first continuation
configuration intentionally permits only seeds 9–10 (72 decisions); seeds
11–13 require a later, separately reviewed continuation configuration.

The final reviewed continuation companion is
`manifests/toolroute_api_paper.v1.0.execution-config.seeds11-13.json`. It has
the same provider request expectations, but authorizes only seeds 11–13 (108
decisions). Its SHA-256 is
`0a12df01886f7e33f362cb7b23dba691efdbfea1bc11c98d44a409193f1bd35c` and
must be independently verified and bound in `PROVENANCE.json` immediately
before those calls; authorization remains false in the committed repository.
