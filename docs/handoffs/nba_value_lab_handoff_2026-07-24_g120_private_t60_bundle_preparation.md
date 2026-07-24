# NBA Value Lab Handoff — G1.2.0 Private T-60 Bundle Preparation v1

更新日期：2026-07-24  
Formal Stake：0

## Repository state before milestone

```text
main: ba6272c1f40076f13afcf6c7cd2e6e301c3efb6c
latest merged PR: 168
open PRs before branch creation: none
```

## Preserved user decisions

```text
HoopsAPI runtime path: DEFERRED_BY_USER_NO_EXECUTION
BloomBet schema probe: DEFERRED_BY_USER_NO_EXECUTION
paid odds path: NOT APPROVED
provider requests executed: 0
```

## Milestone

```text
PR #169 — Add G1.2.0 private T-60 bundle preparation helper v1
G1_2_0_PRIVATE_T60_BUNDLE_PREPARATION_HELPER_VALID
```

Created:

- offline `init` command for a private three-file bundle template;
- offline `seal` command binding normalized and raw SHA-256 evidence;
- hard refusal for any private path inside the public repository;
- fail-closed rights, timestamp-semantics, exact-mapping and redistribution checks;
- aggregate-only contract validation and GitHub Actions workflow.

## Dedicated validation and Artifact QA

```text
workflow run: 30063718569
job: 89390390572 / success
artifact: 8585461789
artifact digest: sha256:1b889354190c87ce720236a49e872a78b30bfe1bcc91418cca7c4d63aee62610
artifact formal state: G1_2_0_PRIVATE_T60_BUNDLE_PREPARATION_HELPER_VALID
contract tests: 18 / 18 PASS
artifact inspected: true
```

Aggregate QA confirms:

```text
offline only: true
private paths outside repository required: true
template is never real input: true
rights review required: true
provider timestamp semantics required: true
collector fetched_at substitution allowed: false
public quote rows emitted: 0
provider requests executed: 0
formal history write authorized: false
market metrics executed: false
Formal Stake：0
```

## No execution claims

```text
real provider selected: false
qualified timestamped odds source: none
provider requests executed: 0
real quote rows stored: 0
real input validated: false
real G1.2.0 dry-run executed: false
formal history write authorized: false
Market Backtest: false
Formal Stake：0
```

## Do not do

- Do not commit the initialized private directory.
- Do not place normalized input, sealed evidence or raw provider exports under the repository tree.
- Do not mark rights or timestamp semantics verified without personal review.
- Do not use collector receipt time as provider observed_at.
- Do not publish bookmaker prices, team IDs, raw payloads, keys or quote rows in Actions Artifacts.
- Do not execute G1.2.0 or market metrics merely because the bundle seals successfully.

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```

When one lawful source and a real 2026-27 T-60 bundle exist, prepare and seal the files privately, run the existing intake validator, and inspect aggregate-only QA. A passing intake requires a separate governed approval before one real G1.2.0 dry-run.
