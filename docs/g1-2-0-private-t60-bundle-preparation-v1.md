# G1.2.0 Private T-60 Bundle Preparation v1

更新日期：2026-07-24  
Formal Stake：0

## Purpose

This offline helper prepares the three-file private package required by the existing G1.2.0 real-governed T-60 intake validator:

```text
1. normalized T-60 input JSON
2. source evidence JSON
3. untouched raw provider response or export
```

It does not choose a provider, execute requests, retain real quotes in the repository, write formal history or calculate Market Backtest／CLV／EV／ROI／Drawdown.

## Safety boundary

All private paths must remain outside the repository. The helper rejects any input or output path located under the public repo root.

The generated template is deliberately invalid as a real intake until every marker is replaced and `template_only` is removed. A template cannot be renamed into a real bundle.

## Initialize a private directory

```bash
python scripts/g1_2_0_private_t60_bundle_preparation_v1.py init \
  --output-dir /private/path/g120-t60-bundle
```

The directory must be empty. The command creates:

```text
t60-input.template.json
source-evidence.draft.json
README_PRIVATE.txt
```

No raw quote or provider export is generated.

## Complete the normalized input privately

Use the existing intake schema and validator contract. The real normalized input must use:

```text
data_mode = real_governed
contract_fixture_only = false
season = 2026-27
competition_type = regular_season
evaluation_stage = T-60m
market_id = moneyline_ot_included
includes_overtime = true
```

It must contain a real bookmaker identity, exact two-sided same-bookmaker prices, provider-origin observed_at, exact game mapping and complete model／injury／information fields.

## Review the evidence personally

Before sealing, the user must personally confirm:

```text
source_rights_state = private_research_allowed
rights_reviewed_by_user = true
provider_timestamp_semantics_verified = true
quote_time_authority = provider_snapshot | bookmaker_last_update
canonical_game_mapping_method = exact
public_redistribution_allowed = false
```

`collector_fetched_at` is never accepted as quote-time authority.

## Seal SHA-256 evidence

After saving the untouched provider export privately:

```bash
python scripts/g1_2_0_private_t60_bundle_preparation_v1.py seal \
  --input /private/path/t60-input.json \
  --evidence-draft /private/path/source-evidence.draft.json \
  --raw-source /private/path/raw-provider-export.json \
  --output-evidence /private/path/source-evidence.sealed.json
```

The command validates the high-level governance assertions and binds:

```text
normalized_input_sha256
raw_source_sha256
```

It never prints or emits quote-level rows.

## Run the intake validator

A sealed bundle is not yet a passing intake. Run the existing validator privately:

```bash
python scripts/g1_2_0_real_t60_intake_validator_v1.py \
  --input /private/path/t60-input.json \
  --evidence /private/path/source-evidence.sealed.json \
  --raw-source /private/path/raw-provider-export.json \
  --output /private/path/intake-aggregate-qa.json
```

Only aggregate QA may leave the private environment.

## Formal boundaries

```text
qualified timestamped odds source: none
real input validated: false
real G1.2.0 dry-run executed: false
formal history write authorized: false
provider requests executed: 0
Market Backtest: false
CLV / EV / ROI / Drawdown: false
betting edge claim: false
Formal Stake：0
```

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```
