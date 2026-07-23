# Historical Silver 2023-24 Source-gap Exception Integration — Real-reference Validation Result v1

## Outcome

```text
request id:
HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001

formal state:
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_PASS

checks failed: 0
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
Stake: 0
```

The single approved aggregate-only real-reference validation completed successfully on `main`.
The exported result payload was supplied by the repository owner after GitHub Actions Run `#2`
showed `execute-once / success` and one Artifact.

## Evidence provenance

```text
workflow:
Run approved Historical Silver source gap exception real-reference validation once v1

workflow file:
.github/workflows/run-approved-historical-silver-source-gap-exception-integration-real-reference-validation-once-v1.yml

run number: 2
head SHA: 596ade65cd26cb148f8a3b9a0ffa6092b16a6737
job: execute-once / success
observed duration: 20 seconds
observed Artifact count: 1
```

The exported JSON does not contain the GitHub workflow run ID, Artifact ID, or Artifact archive digest.
Those values are therefore recorded as unavailable and are not guessed.

The committed result payload is bound by:

```text
payload SHA-256:
sha256:048149cd058c74c1ab441a99f3a4eec0972668500e469ff81ce663b3e5264340

payload size:
4349 bytes
```

## Immutable request and implementation bindings

```text
request file SHA-256:
sha256:192a06862fe830027686d149d36572b4ad76ea609f489c6a3d540b7ea4b27e97

transformer SHA-256:
sha256:c4bd7ccb05bcf78747a7210e0eefad083d599de2ca8b0d44c9c455006f084cbc
```

The three approved aggregate input hashes are preserved inside the result record.

## Aggregate result

```text
raw Historical Silver games: 5,826
raw Historical Gold matchups: 5,824
raw missing Gold for Silver: 2
documented source-gap exceptions: 2
unexplained missing after documentation: 0
covered or documented: 5,826
Gold dataset complete: false
recognition gate passed: true
```

The documented exception remains:

```text
SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
```

This means the two missing Gold-eligible games are explained by the already validated upstream
PBP Stats source-archive absence. The result does not convert them into Gold rows and does not
rewrite the Gold dataset as complete.

## Consumption state

Request `001` is permanently consumed:

```text
execution attempted: true
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
workflow_dispatch only: true
execution enabled after consumption: false
```

Do not re-run or re-dispatch this request.

## Preserved boundaries

The result confirms all of the following remained false:

- database, network, source-archive, or raw CSV access;
- raw-row reads or emissions;
- Silver or Gold writes;
- analyzer or transformer modification;
- cross-source audit rerun;
- market backtest;
- model training or retraining;
- betting-edge claim;
- Stake above `0`.

Opening／Closing semantics and CLV／EV／ROI／Drawdown remain unauthorized.

## Downstream interpretation

The validated research corpus may now be described as:

```text
5,824 Gold matchups eligible for a future separately governed corpus freeze
2 documented source exceptions excluded from Gold eligibility
Gold dataset complete: false
```

This result does not itself freeze the corpus and does not authorize market backtesting.

## Next controlled lane

```text
HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN
```

The next PR may design an aggregate-only eligibility and exclusion policy. It must not rebuild
Gold, rerun the cross-source audit, train models, perform market backtests, or raise Stake above `0`.
