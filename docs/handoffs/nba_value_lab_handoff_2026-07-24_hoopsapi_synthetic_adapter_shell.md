# NBA Value Lab — HoopsAPI Synthetic Adapter Shell Handoff

更新日期：2026-07-24

## Milestone

```text
IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1
```

## Implemented

- Added `scripts/hoopsapi_private_forward_adapter_v1.py`.
- Added one synthetic public-shape-only fixture.
- Added a dedicated aggregate-only validator and GitHub Actions workflow.
- Preserved the provider-neutral private collector as the only SQLite writer.
- Required same-provider two-sided Moneyline.
- Rejected single-sided markets.
- Kept missing provider timestamp semantics fail-closed.

## Formal boundaries

```text
synthetic fixture only: true
network client included: false
secret reader included: false
account workflow included: false
provider requests executed: 0
real provider payloads processed: 0
quote time authority: unverified
quote observed_at: null
point-in-time eligible rows: 0
raw payloads retained: 0
public quote rows emitted: 0
market metrics executed: false
formal Stake: 0
```

## Not authorized

- account creation;
- provider terms acceptance on behalf of the user;
- API-key connection;
- HTTP requests;
- real quote ingestion or retention;
- provider runtime or point-in-time qualification;
- Frozen Gold join;
- Market Backtest, CLV, EV, ROI or betting claims.

## Next unique sub-mainline

```text
DESIGN_HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_V1
```

The next step must remain design-only unless the user separately completes provider terms/account actions and explicitly authorizes a capped runtime preflight. The maximum preflight remains three requests.
