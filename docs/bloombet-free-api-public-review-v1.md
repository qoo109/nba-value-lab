# BloomBet Free API — Public Schema, Terms and Timestamp Review v1

Date: 2026-07-24  
Formal Stake: `0`

## Objective

Complete the public-only BloomBet review required by the no-cost timestamped-odds qualification line. This review must not create an account, connect a key, execute API requests, download quote rows or calculate market performance.

## Public evidence located

The official homepage publicly claims a free tier at USD 0 per month with 500 requests per month, NBA and NFL coverage, live and historical moneyline data, and 15+ providers. The official documentation landing page publicly states that a free key is available with 500 requests per month and no credit card.

## Unverified gates

Publicly accessible material did not establish the endpoint request schema, response field schema, explicit bookmaker key, same-bookmaker two-sided h2h structure, provider-level observation timestamp field or meaning, scheduled tipoff field, stable event identifier, historical coverage start, retention window, opening/closing identity, automated research-use rights, private retention rights or redistribution rights.

No public Terms of Service, API data-license or retention-rights page was located during this review. This records only that the material was not located and verified; it does not assert that no such terms exist behind account access.

## Formal decision

```text
BLOOMBET_FREE_API_PUBLIC_REVIEW_BLOCKED
```

BloomBet remains promising but is not qualified for historical backfill, point-in-time joining, forward collection, market backtesting or quote ingestion.

## Approval-gated next step

```text
BLOOMBET_FREE_API_ZERO_COST_SCHEMA_PROBE_AWAITING_EXPLICIT_USER_APPROVAL
```

A separate request design permits at most three official free-tier schema requests only after explicit user approval. The user must create the account and privately store `BLOOMBET_API_KEY`; the key must never be pasted into chat, committed, logged or uploaded as an Artifact.

The probe may retain only endpoint names, parameter names/types, response field names/types, a redacted single-response shape, timestamp-semantics evidence, historical coverage metadata, quota metadata and an aggregate gate result. It may not retain or publish raw quote-level rows.

## Boundaries

- No account has been created.
- No API key has been connected.
- No API request has been executed.
- No paid plan or credit card is authorized.
- No market metric is authorized.
- Market backtesting remains blocked.
- Formal Stake remains 0.
