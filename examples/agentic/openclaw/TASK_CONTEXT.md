# Bounded coaching context

Long-term history is available through bounded on-demand monthly, activity and
managed-review reads; see [source, coverage and refresh contract](LONG_TERM_HISTORY.md).

`context_packet.py` reads current local files for one task, prints a compact JSON projection and exits. It makes no network/model calls, sends no messages, changes no calendar and stores no athlete data. It reads no credentials. It is an alternative **fresh read** of the actual source, not an LLM summary, persistent athlete memory, training algorithm or replacement protocol.

## What is loaded

| Task | Current data | Historical data | Further dependencies |
|---|---|---|---|
| `morning` | Complete readiness/health envelopes, source rollups, relevant load/baseline fields, three calendar dates of wellness/activities, today's planned events | None | Exact protocol/report section if interpreting or changing a rule; route/weather when relevant |
| `weekly` | Current rollups/metrics, matching recent rows, next seven dates of supplied plans | All daily projected rows matching the previous 14 dates, with intersecting weekly bins | Managed revision/review and detailed execution when used; no invented compliance |
| `workout` | Current state, constraints and supplied future plans | Previous 28 dates | Exact selected workout-library template before prescribing; environmental/fueling details when relevant |
| `plan` | Current state, goals/constraints and supplied future plans | Previous 28 dates | Existing managed plan/review, selected workout templates and additional weekly history as needed |
| `post_workout` | Exact activity ID, current health/readiness, matched local interval detail/fetch state | None automatically | Relevant execution windows/streams, report/protocol section; no substitution of session averages for interval work |

All windows use explicit profile/source timezones and the current clock. No row-count prefix or first-N-file-lines query is used. Multiple sessions on the same date are preserved. A matching activity must be unique; duplicate/conflicting interval identities fail. Missing details remain unavailable, not successful execution. Free text is labelled data and supplies no instructions or write authority.

`READ_THIS_FIRST`'s repeated instructions and unrelated JSON blocks are omitted; categorical wellness scales are retained. Full readiness/health objects, observations (when supplied), null values, source dates, source units and start-of-day versus live ACWR stay distinct. No new readiness score or physiological calculation is performed. Missing HRV/RHR alone never becomes a restriction. Packet freshness and source coverage are not health clearance.

Dossier sections are **explicitly selected by exact heading in a private operator profile**. Each selected section is copied whole, including descendants; no biography is guessed or LLM-generated. Routine reports can exclude dated plans, calibration logs, dynamic metrics, API configuration and changelog. Read an omitted relevant section on demand; omission never proves absence. Source SHA256, headings, header/revision text and authority status remain available. A declared official path conflict fails; a legacy dossier without an authority header is labelled `operator_selected_legacy_header_unverified`, not silently promoted to a verified canonical dossier. The helper never edits a dossier or resolves conflicting copies. If that authority uncertainty materially affects advice, clarify it.

## Profile and commands

Create a private `context-primary.json` with these keys (absolute, explicitly verified paths):

```json
{
  "schema_version":1,
  "data_dir":"/home/ATHLETE/training-data",
  "protocol":"/home/ATHLETE/training-data/section11/SECTION_11.md",
  "workout_reference":"/home/ATHLETE/training-data/section11/examples/workout-library/WORKOUT_REFERENCE.md",
  "reports_dir":"/home/ATHLETE/training-data/section11/examples/reports",
  "dossier":"/home/ATHLETE/training-data/DOSSIER.md",
  "dossier_sections":{
    "morning":["2. Coaching and communication preferences","4. Private profile and goals","5. Health, medication and supplements","7. Practical training context and essential equipment"],
    "weekly":["2. Coaching and communication preferences","4. Private profile and goals","5. Health, medication and supplements","7. Practical training context and essential equipment"],
    "workout":["4. Private profile and goals","5. Health, medication and supplements","6. Fueling, hydration and recovery","7. Practical training context and essential equipment"],
    "plan":["2. Coaching and communication preferences","4. Private profile and goals","5. Health, medication and supplements","7. Practical training context and essential equipment"],
    "post_workout":["4. Private profile and goals","5. Health, medication and supplements","6. Fueling, hydration and recovery","7. Practical training context and essential equipment"]
  },
  "timezone":"Europe/Zurich",
  "source_timezone":"Europe/Zurich"
}
```

These headings fit the current dossier template; older dossiers need their **actual** headings, not these names. Do not use the public template or fictional JSON examples as athlete data. Configuration selects sources; it does not verify their truth. A missing dossier is labelled unavailable while current safety data can still be reported. A missing selected heading fails rather than quietly dropping a constraint after a source edit.

```bash
python3 context_packet.py --profile /private/context-primary.json build --task morning
python3 context_packet.py --profile /private/context-primary.json build --task weekly
python3 context_packet.py --profile /private/context-primary.json build --task post_workout --activity-id EXACT_ID
python3 context_packet.py --profile /private/context-primary.json history --start 2026-10-05 --end 2026-10-18
python3 context_packet.py --profile /private/context-primary.json history --tier weekly --start 2026-07-01 --end 2026-10-18
python3 context_packet.py --profile /private/context-primary.json headings --source protocol
python3 context_packet.py --profile /private/context-primary.json section --source protocol --heading 'Health Context (v11.61)'
python3 context_packet.py --profile /private/context-primary.json headings --source workouts
python3 context_packet.py --profile /private/context-primary.json section --source workouts --heading EXACT_TEMPLATE_HEADING
python3 context_packet.py --profile /private/context-primary.json section --source dossier --heading EXACT_HEADING
```

Source SHA256s and section headings/line numbers identify the current read; `profile_sha256` binds packet selection. A protocol pointer with `loaded:false` does not claim that the protocol was read. `headings` skips bodies, so browsing no longer starts with hundreds of changelog lines. `section` copies an exact ATX Markdown section and its descendants, ignoring fenced code headings; ambiguous/missing titles fail. For report sections use `--source report --task morning|weekly|post_workout`.

## Completeness and failure handling

- Daily queries allow at most 42 dates; weekly queries allow 182. They return **all matching source rows** (daily fields explicitly projected, weekly bins retained whole). Missing/invalid/duplicate dates and boundary bins are visible. `coverage_complete` concerns row/date presence, not measurement completeness, endpoint reliability or a fully observed current day/week. Null HRV is a missing measurement, not a missing training date.
- History retains its own `generated_at` and data range. Newer latest data does not refresh history. Source rollups retain their original periods: never relabel a seven-day summary as a 14/28-day total or double count overlapping history/latest data. A missing historical day never becomes zero training. Week bins are Monday-based producer bins, not prorated daily observations.
- Current snapshot freshness requires a valid timestamp, the current local calendar date and age <=24 hours, with up to five minutes future clock tolerance. This is an operational source-age check, not a physiological threshold. Naive producer timestamps use **explicit `source_timezone`**; ambiguous/nonexistent DST times are unknown. Unknown/stale/future snapshots request refresh before new prescriptions; current subjective feedback remains a separate decision input.
- Each source read is bounded at 8 MB. All output, including sections, is bounded at **49,152 UTF-8 bytes**. Over-budget output fails with a fixed error code; it never quietly clips a row, section, health decision or constraint. Narrow an explicit history query, retrieve an exact section, or use morning core plus targeted dependencies. Do not fall back to raw whole-file dumps or fictional examples. Individual source files are read fresh but not in a cross-file transaction; retain material generation-time conflicts.
- A successful JSON object ends with `packet_complete:true`. Require valid complete JSON and this marker from the tool. This indicates transport/projection completeness only, not complete history or permission to train. Tool-side truncation, a missing marker or a nonzero exit is an unusable packet. The deployed OpenClaw exec library's normal output cap is above the packet limit; other installations must verify their own tool/harness caps. The helper is not an OS sandbox and does not restrict the surrounding agent's other tools.
- Errors contain fixed codes, never private file text. Packets contain private athlete information **by design** for the configured coach; do not put them in this repository, telemetry, public logs or messages to other recipients. Production prompts use the builder's stdout directly, not a stale saved packet. Existing credential-output protection still applies.

## Primary integration

Step 4 supersedes the scheduled-message/post-reporter invocation below with the [bounded report supervisor](EXECUTION_RELIABILITY.md). Interactive source selection and the packet contract stay the same. The installed `section11_context` tool accepts the same operations as typed JSON (`operation`, `task`, `source`, `heading`, `start`, `end`, `tier`, `activity_id`), with no arbitrary paths or shell. Prefer that tool where available. Scheduled reports receive the fresh packet directly and use the tool for additional exact dependencies.

The primary morning/weekly job messages call the installed builder once, use the task-specific packet and request additional exact dependencies only when they affect the decision. The primary workspace directs interactive workout/plan tasks to the same fresh entry point. The primary external post-workout reporter's **prompt only** calls the builder with its observed activity ID; existing detection, state, retry, model and delivery behavior remain outside this change. In particular, its historical CLI-exit-versus-delivery ambiguity is still Step 4 work.

On the current server, the reporter entry point was a symlink into the old checkout. Its original source is preserved; the entry point is redirected to a private runtime copy containing the prompt change. AST comparison verified that only prompt construction and its standard-library quoting import changed, and relocation checks verified there were no local imports or `__file__` dependencies. The original symlink target is recorded in private rollback state. Future installation/cleanup must account for this explicit runtime override.

Private installation/rollback records preserve the old messages, workspace text and reporter script. Job schedules, destinations, model choices and reasoning stay unchanged. The secondary profile is untouched. No packet cache, transcript rewrite, growing summary injected into every turn, full coaching release installation or automatic calendar publication is added.

OpenClaw still stores ordinary tool results in its private conversation transcripts. The builder does not remove earlier packets from a long conversation or replace the runtime's history/compaction behavior. Context retention/pruning remains later work; the packet bound is not a guarantee that the entire model context fits its limit.

Routine morning reports target one context tool call followed by the answer (normally two model responses). This is a target, not an enforced loop limit or measured saving. Step 2 telemetry can measure the next real runs; controlled quality evaluation is still required before claiming that fewer tokens/calls preserve quality. Tests validate deterministic selection, safety/data preservation and failure handling, not live model judgment.

When full intake makes a task packet too large, the builder explicitly defers the
daily/weekly history rows to a separate dated `history` read, retaining complete
intake and readiness/health envelopes. The packet labels deferred counts, the
required window and an evidence digest; omitted rows do not imply absent training
or complete coverage. Retrieve the stated history before a prescription or a
judgment that depends on it. The original byte limit and exact history reader
remain unchanged; oversized remaining content still fails explicitly.

### Native tool transport budget

The optional private profile key `tool_packet_bytes` (8,192–49,152 bytes) caps CLI
responses before OpenClaw can silently trim them. Primary uses 30,000 bytes under
a 128k working context, whose native live tool cap is 32k characters. A build can
explicitly defer bulky history, selected dossier sections and intake to their
existing exact readers. `intake` is an additional read-only operation returning
the complete account-bound onboarding revision; it accepts no model-selected path.
Read required_retrieval before using deferred facts. Full readiness/health envelopes
remain intact; an oversized remaining response fails without a partial packet.
The internal Python builder/report supervisor continues to receive its complete
source packet. The coaching bridge also honors the smaller output cap: receipts
are never shortened to fit it; uncertain persistence still requires a recovery read.

If a build still exceeds the transport budget, recent activities are explicitly
deferred to `activities` with the same task (and activity_id for post_workout).
The reader returns the exact fresh selected rows and source hashes. Retrieve them
before interpreting completion, and refresh core health/readiness if source
identity changed between reads. Core readiness and health are never dropped.
