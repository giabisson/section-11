# Long-term training evidence

## Three implementation steps

1. **Facts and coverage.** `examples/training_history.py` keeps private compact
   activity/wellness facts in SQLite and builds monthly summaries immediately.
   No six-month minimum, padded pre-training zero months or inferred rest days.
   The repository sync uses the same projection to repair its monthly tiers.
2. **Selective retrieval.** The existing `section11_context` tool gains
   `long_term`, monthly `history`, exact `history_detail`, and `review` reads.
   Routine task packets include retrieval instructions, not every monthly row.
3. **Primary runtime.** A separate hourly service refreshes the private companion
   source. This allows narrow deployment alongside the older installed sync;
   it does not require installing the broader pending coaching release.

## Refresh and reliability

The private runner profile contains `state_dir`, `credentials_file`, `timezone`,
and optionally a dated `athlete_attestation` with `source:athlete_statement`,
`confirmed_at`, `first_training_date`, and `complete_through`. The credential file
is the existing primary `.sync_config.json`; no credentials enter summaries,
the database, prompts or repository. Install profiles outside the checkout.

The first refresh requests up to three years. Later runs reconcile the last 14
calendar dates; once every 24 hours they reconcile the entire original queried
range through today. Each run makes two bounded GETs, activities and wellness,
with 35-second timeouts, a 32 MB response bound and no redirect forwarding.
There are no immediate retries, model calls, calendar writes or messages. The
hourly service has a 120-second ceiling and a nonblocking per-store lock.

Reconciliation replaces the successfully fetched date range, including deletions,
only after both responses pass validation. Conflicting duplicate identities,
invalid dates, account changes and out-of-range rows fail. Identical duplicate
activities are counted once. Old facts persist outside the recent window until
the next full reconciliation checks them. `last_full` is separate from the
projection timestamp. A failed fetch leaves the good summary intact and records
a sanitized failure status. JSON projection replacement is atomic; SQLite updates
are transactional. A rare failure between database commit and projection export
causes exact activity reads to fail their generation check until a successful
refresh; it never mixes generations silently. Read results expose age, refresh
status and reconciliation scope; over 36 hours old is explicitly stale.

Missing duration/load is not zero. Complete totals become null when inputs are
missing; `known_sum` and observed/missing counts remain available. Sport counts
and cycling totals are separate. Indoor/outdoor/unknown are explicit. Power and
HR source zones have separate totals and activity coverage, without translating
them into an invented physiological intensity model. Activity FTP settings are
labelled settings, not verified fitness tests or comparable measurements.
Feedback coverage is factual counts; lack of feedback is not tolerability.
Monthly HRV/RHR observations are optional descriptive data, never prerequisites
for training or same-day readiness measurements. No causal adaptation claims,
plan intent, adherence or block decisions are inferred from activity patterns.

First and current months are partial. Closed calendar bins and confirmed logging
completeness are separate properties. Empty interior months mean no recorded
activity unless an explicit athlete statement covers that period. A dated claim
of complete training history is not extended to future dates. No older training
is manufactured when the athlete confirms none.
The statement is bound to the confirmed activity identities/dates. Later additions,
deletions or redating within its period flag completeness for reconfirmation;
they cannot silently turn a formerly recorded workout into confirmed rest.

## Context contract

Add optional absolute `long_term_source` (the companion `summary.json`) and
`review_store` (an **existing** managed `coaching_plan.sqlite3`) to the private
context profile. No store is initialized or plan reconstructed by the reader.

- `{"operation":"long_term"}`: six available closed months plus current,
  cycling volume/load/longest session, coverage, environment, feedback counts,
  setting references and an index of the latest two actual managed reviews.
  Maximum **8 KiB** of complete JSON; older months are counted as omitted and
  remain locally available. This is the default long-term view, not loaded on
  every Telegram turn or morning report.
- `{"operation":"history","tier":"monthly","start":"YYYY-MM-DD","end":"YYYY-MM-DD"}`:
  whole intersecting monthly bins, cycling/all-sport detail, optional wearable
  observation counts and source-zone totals; at most three years per request.
- `{"operation":"history_detail","activity_id":"EXACT_ID"}`:
  exact compact activity facts from the same generation; no interval streams.
- `{"operation":"review"}` or with `review_id`: latest two persisted reviews
  or one exact older review. Original objective/starting evidence, observations,
  decisions/reasons/next observations and revision links are returned. Use these
  before claiming why a block changed; patterns of completed rides are insufficient.

Detailed reads retain the existing 48 KiB whole-packet bound, 15-second tool
deadline and six-call report budget. Oversize is an explicit error, never clipped
JSON or a fabricated complete record. Narrow monthly dates or retrieve an exact
review. Prompt text in records remains untrusted data. `MEMORY.md` should contain
only the source pointer and dated stable athlete clarification, not dynamic totals.
Legacy `history.json` still supplies existing daily/weekly views; its timestamp
does not change when the companion updates. On a narrow deployment its old empty
monthly arrays remain legacy data: the new monthly tool reads the companion.

## Validation

`test_training_history.py` covers short/empty histories, partial/empty months,
athlete attestations, missing versus zero metrics, sports, separate intensity
bases, optional wearables, deduplication, source reconciliation, historical edits
and deletions, failure retention, account isolation and private file modes.
`test_long_term_context.py` covers selection, coverage, age, generation matching,
original causal review records, exact older references, typed paths, actual CLI
JSON and fail-closed bounds. Node tests exercise the typed tool argument contract.
Synthetic tests establish data/retrieval behavior, not physiological validity or
measured LLM token savings. Live validation should compare source activity counts
and sums to the projection, verify actual typed-tool transport without an LLM,
and record private rollback material and primary/secondary scope checks.
