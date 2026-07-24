# HoopsAPI Private Forward Adapter — Synthetic Shell v1

## Formal scope

This milestone implements only the offline HoopsAPI-shaped synthetic adapter shell authorized by the first-provider qualification gate.

It does **not** create an account, accept provider terms, read an API key, issue a network request, retain a real quote, qualify provider timestamp semantics, join Frozen Gold, run market metrics or authorize betting.

## Data path

```text
Synthetic HoopsAPI-shaped fixture
  -> hoopsapi_private_forward_adapter_v1.py
  -> provider-neutral private collector input
  -> private_forward_odds_collector_v1.py
  -> temporary private SQLite
  -> aggregate-only QA
```

## Fail-closed timestamp policy

Public evidence does not establish a provider snapshot or bookmaker last-update timestamp. The adapter therefore emits:

```text
quote_time_authority = unverified
provider_snapshot_at_utc = null
bookmaker_last_update_utc = null
mapping_state = unmapped
source_rights_state = unreviewed
```

The provider-neutral collector then derives:

```text
quote_observed_at_utc = null
point_in_time_eligible = false
```

`collector_fetched_at_utc` is receipt evidence only and may never substitute for provider-origin `observed_at`.

## Structural rules

- NBA only.
- Moneyline key is `h2h`.
- Same-provider home and away prices are required.
- Single-sided markets are rejected.
- Prices must be valid decimal odds.
- Synthetic event identity remains unmapped.
- Raw payload retention is disabled.
- Public quote rows are prohibited.

## Validation

The dedicated validator checks:

- one synthetic same-book two-sided Moneyline row is emitted;
- missing provider timestamp semantics remain unverified and null;
- point-in-time eligible rows remain zero;
- single-sided Moneyline is rejected;
- no network client, secret reader, account workflow or scheduler is introduced;
- no provider requests or real payloads are processed;
- no public quote rows or market metrics are produced;
- Formal Stake remains 0.

## Next governed step

```text
DESIGN_HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_V1
```

That next step is design-only. Runtime requests remain unauthorized until the user personally accepts provider terms, supplies a private key through an approved secret path and separately approves a capped preflight. The existing maximum is three requests, but this shell does not execute any of them.
