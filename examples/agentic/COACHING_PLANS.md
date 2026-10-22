# Persistent coaching plans

`coaching_plan.py` stores the athlete's goals, block intent, dated availability, sessions and revisions in a private local directory. Each selected prescription is an immutable snapshot: exact workout steps, resolved native watt targets, original intensity reference, template/catalog hashes, full duration, purpose and alternatives. Changing current FTP or a saved workout cannot rewrite that record.

This is an engineering implementation of the [coaching update plan](../../COACHING_UPDATE_PLAN.md), not a scientifically validated planning algorithm. The [adaptive review workflow](ADAPTIVE_REVIEWS.md) consumes completion/response and can atomically propose an explained future revision. Exact doses remain coaching choices; reviews never publish automatically. Readiness, health clarification, current athlete feedback, suitability, event specificity and approval still require the existing coaching process. No HRV, RHR or nightly wear requirement is added.

## Private storage and setup

Use Python 3.9+ on a POSIX system with a **durable private filesystem**. The local store uses only the standard library; calendar operations use `push.py` and its normal `requests` dependency. Install `coaching_plan.py`, `coaching_review.py`, `coaching_context.py`, `coaching_check.py`, `push.py` and `workout_validation.py` beside one another, with the matching workout library/catalog in one of the [supported locations](WORKOUT_VALIDATION.md#scope-and-installation). The candidate manifest and offline installed-path tests include these dependencies. See [deployment verification](COACHING_DEPLOYMENT.md); the actual external runtime remains unverified and these changes are not deployed.

Pass `--data-dir` explicitly. Choose a dedicated directory outside the source/update checkout and outside any public export. It is created with mode 0700; existing directories must already be private. The database and lock use mode 0600. Symlinked stores/database/locks and public permissions fail rather than changing another folder's permissions. No path is inferred from the dossier or a Telegram conversation. Configure the path in the agent's private runtime settings; never assume this repository knows the user's actual OpenClaw storage location.

The source of truth is **`coaching_plan.sqlite3`**, with append-only revision, prescription, preview and decision tables. SQLite transactions keep a proposal and all its snapshots together, and commit an operation's start before a calendar mutation. This replaces the originally proposed pair of independently written `coaching_plan.json` and `coaching_decisions.jsonl` files to avoid split updates after a crash. JSON is the interchange/read format, not a second authoritative database. A lock serializes mutations through the whole publication operation; a second process fails promptly. SQLite's normal transaction durability applies. Back up the database while idle or using SQLite's backup facilities, and restore its identity/history together. Do not operate two writable copies of one store.

One store belongs to one explicit athlete ID and one continuing plan ID. Alias `0` is rejected because it identifies the current API-key owner rather than a stable account. The configured calendar client must use the same explicit ID; actual server authorization remains the API's responsibility. A random store namespace and logical session IDs provide stable `external_id`s within that store. A newly created store has a new namespace and does not recover control of existing events; restore the original backup rather than recreate it. Separate stores can still schedule duplicate training, so configure one active store. No API key is stored.

Do not put this database into a public sync repository or a transient GitHub Actions runner. Existing direct `push.py` calls, calendar edits through another client and external OpenClaw memory are **not journaled** by this store. For a managed plan, route publication, rescheduling and cancellation through this CLI. An environment without durable local storage cannot claim automatic persistence; return a reviewable plan artifact and state the limitation.

## Local workflow

The [input example](../json-examples/coaching_plan.example.json) is synthetic and must be adapted before prescribing. It represents a month-long objective with only one near-term week fully specified. The [worked output](../json-examples/coaching_plan_output.example.json) comes from local propose/show commands, with no calendar call. Generated identities differ in a fresh store because its namespace is unique.

```bash
coaching_data_dir="$HOME/.local/share/section11-coaching"
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" propose --json my-plan.json
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" show --compact
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" show --prescription-id rx-EXACT_ID
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" show --revision rev-EXACT_ID
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" history --limit 10
```

These commands require no credentials and perform no HTTP. `show --compact` is the normal context-recovery view: intent, revision references, session summaries and publication state. Retrieve exact prescriptions only when needed; do not inject the entire decision history into every conversation. Full `show` includes all selected snapshots. Historical reads do not recompile against today's fitness, catalog or date. `show --event-id 123` lists verified prescription versions linked to that calendar ID, including updates/removal. Select the relevant version using the authoritative completed-activity pairing and execution context; the last publication alone does not prove what the athlete did or exclude intervening external edits.

## Schema 1 contract

The root has `schema_version: 1`, `planning_policy: "athlete_specific_v1"`, `athlete_id`, `plan_id`, `revision`, `goals`, `block`, `weeks` and `sessions`. `detected_phase` is optional and separate from planned intent. Unknown fields fail. This persisted representation complements the Section 11 B audit header: the header still records data-fetch status/confidence; the store represents goals, block, availability, selections and revisions explicitly. Neither a stored plan nor supplied metadata independently proves those inputs true or establishes health clearance.

| Field | Required contents |
|---|---|
| `revision` | Caller-selected unique `request_id`, current `parent_revision` (null initially), reason and nonempty evidence references |
| `goals[]` | Unique `goal_id`, description, priority `general`/`A`/`B`/`C`, date (nullable for general fitness), demands, success measure, constraints |
| `block` | Objective, linked goal IDs, planned phase, start/end dates, starting evidence, progression hypothesis, recovery opportunities, review date, change conditions |
| `weeks[]` | Unique Monday start, `weekly_minutes`, dated `session_windows` with `date`/`max_minutes`, intensity approach (`intent`, `zone_model`, `basis`, `rationale`) and compromises |
| New `sessions[]` entry | Stable `session_id`, purpose, alternatives, `session_budget_minutes` and workout |
| Reused session entry | The same `session_id` plus a `prescription_id` already belonging to this plan's history |
| Evidence reference | `source`, observation `as_of` date and summary; never fabricate a successful fetch or future observation |
| Optional `detected_phase` | Observed `value`, `as_of`, `source`; a mismatch does not silently rewrite the block |

The compiler normalizes selected sessions to references to immutable `rx-...` records. A revised workout creates a new prescription ID under the same logical session ID; a new training occurrence needs a new logical ID. Reused snapshots preserve their purpose, alternatives and original fitness. To change those, submit an explicit revised session object. Never reconstruct an earlier prescription from today's saved-workout inventory.

Every cycling prescription currently requires the checked Ride/VirtualRide power schema from [workout validation](WORKOUT_VALIDATION.md); other cycling type aliases/formats require a reviewed extension rather than bypassing it. Other sports may carry explicit timed workouts, count toward capacity and remain `not_checked` for dose. The store does not certify their exercise technique or physiology. Native workout fields are restricted to documented push fields; the store assigns `external_id`.

Capacity validation counts complete prescribed durations across sports against the individual session budget, **combined daily availability** and weekly ceiling. There is one availability entry per date, representing that day's total capacity, not a clock-specific appointment. Explicit start times must not overlap or cross midnight. Untimed sessions remain flexible; collisions with outside activities/work and calendar constraints outside the managed plan still need review. Empty/rest weeks and flexible later weeks are valid. No minimum hours, intensity ratio, demanding-session quota, fixed weekly increase, CTL-derived capacity or wearable requirement is imposed.

Operational input limits are 2 MB, 104 specified weeks and 1,000 selected sessions. Dates are local, using the process timezone as in `push.py`; configure it to the athlete's timezone. These bounds and the schema are engineering choices, not training recommendations.

Optional [event preparation, durability and strength context](EVENT_PREPARATION.md) lives in the block. It uses the same capacity/revision contract; it does not impose extra wearable requirements or universal taper doses.

## Revisions

Read the current plan first. Copy its normalized `plan`, use a fresh `request_id`, set `parent_revision` to the current returned `revision_id`, state the reason/evidence and change affected goals, availability or sessions. Unchanged sessions can retain their prescription IDs. Submit through `propose`; it validates the entire candidate before atomically appending anything. Concurrent/stale parents fail, preventing silent lost revisions. A retry of the identical original request returns its original revision; reusing its request ID for different content fails.

Changing an event date or availability produces an attributable revision even when no prescription changes. Reducing a time window without reducing/removing an incompatible session fails. Missing a ride creates no automatic replacement, training debt or retrospective prescription change. A past snapshot may remain in the plan as context. Published historical sessions cannot be rewritten or repurposed; removing one from current selections does not delete it from the calendar/history.

## Calendar preview and publication

Credentials follow the existing push CLI: explicit top-level `--athlete-id`/`--api-key`, local `.sync_config.json`, or environment. Do not put credentials into plan JSON or approval references.

```bash
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" preview --revision rev-EXACT_ID
# Only after the athlete approves this exact preview:
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" publish --preview preview-EXACT_ID --approval-ref "Approval message reference" --confirm
```

Preview validates plan capacity and each changing prescription before any calendar mutation. It reads affected calendar state and persists a content-bound preview containing exact before/after payloads, creates, updates and deletes. Deleting a removed future session appears explicitly. Current catalog/prescription hashes must still match; stale provisional fitness reviews require a reviewed revision, not a silent change. Confirmation is bound to that preview and current plan/publication state; tokens cannot be replayed. Approval references are caller attestations, not independently authenticated Telegram messages. No approval or write is inferred from this implementation task.

Published events are updated by their verified event IDs, preserving external identity when moved. Before changes/deletion, the old managed payload must still match and the event must not be paired to a completed activity. Conflicts, failed reads and historical dates close the gate. Optional fields previously controlled by the prescription are explicitly cleared with null when removed; the desired read-back must confirm it. Real API/device handling of those fields remains an integration check.

Each operation commits its start before calling the existing push transport. Writes are never retried. New creates use its pre-read/bulk-write machinery; updates use its single-write/outcome helpers after the managed exact-baseline check; deletes retain its convergence rules. A read-back must establish exact desired payload and a unique usable event ID, or absence after deletion, before the store marks it published. Outcomes are `applied`, `not_applied`, `partially_applied` or `unknown`; processing stops on the first failure/uncertainty. A partial batch retains what succeeded and a new preview covers remaining changes. There is no atomic remote transaction or rollback promise.

Creation checks external-ID uniqueness in the target date window, following push's established limits, not across the entire calendar. Distributed edits can still race between the last read and a mutation: the server's upsert key/global uniqueness and conditional update semantics are not established here. Do not operate another writer against the same managed sessions. Live Intervals.icu behavior, Telegram/OpenClaw invocation and deployed storage have not been tested.

## Uncertainty and recovery

```bash
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" reconcile
```

Reconciliation reads the calendar and appends evidence locally; it sends **no calendar writes**. An interrupted process or disk failure after sending leaves a durable pending operation and blocks further publication, including another revision. Drafting a new revision remains possible. Exact desired state resolves an operation as applied. A missing create, old payload, duplicate identity, failed read or mismatch does **not** prove non-application and cannot authorize a retry. A deletion is resolved by verified absence of its event ID.

If a genuinely unresolvable operation has been externally established not to have applied, `resolve-not-applied --operation-id ... --evidence-ref ... --approval-ref ... --confirm` records that explicit determination. It is not automatic reconciliation: the evidence and approval are caller attestations, clearly labeled unverified by the store. Do not use it solely because an event is absent or a timeout elapsed. A fresh preview/approval is required before another attempt.

`show` separates proposed, confirmed, partially published, published, previously published and uncertain states. Calendar bindings report **last verification**, not continuous freshness. Successful publication never implies workout completion, adherence, recovery or training effectiveness. The adaptive review path consumes authoritative completion/feedback and creates explained future revisions while preserving these boundaries.
