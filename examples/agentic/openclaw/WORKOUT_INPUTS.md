# Checked workout inputs

Call the directly exposed `section11_context` tool with:

```json
{"operation":"workout_inputs","environment":"indoor","templates":["AE-1","AE-2"]}
```

The operator-owned coaching profile binds credentials, account and installed
catalog. Environment selects only the fixed Ride/VirtualRide sport-settings GET;
the model cannot supply URLs, accounts, credential paths or settings changes.
One bounded request, no redirect/retry, and a maximum 8 KiB result. Auth/network,
missing settings, wrong account/type or catalog mismatch fail explicitly. This
operation writes no calendar/training data and calls no model.

The result contains the actual configured FTP basis (indoor_ftp when positive,
otherwise ftp), actual zone upper limits, a schema-ready uncertain fitness
reference and selected hash-verified numeric template constraints. Intervals
reports power-zone upper limits as percentages of FTP; the reader scales those
actual configured values arithmetically. It supplies no default percentages and
never fabricates a missing final zone. The [Intervals data model](https://www.npmjs.com/package/@intervals-icu/js-data-model)
and [zone API clarification](https://forum.intervals.icu/t/solved-athlete-power-zones-from-api-not-same-as-sports-profile/128277)
describe the source conventions.

A setting is not a fitness test. Assessment date/method/equipment/environment
remain unknown, status is uncertain, and selecting an indoor setting does not
establish indoor testing. This reader does not validate LT1/LT2, current capacity
or medical clearance. Fresh readiness/health, reported constraints, availability,
library design and the exact-step compiler still govern prescriptions. Existing
absolute prescriptions never change implicitly with a settings refresh.

The earlier task packet exported FTP settings without configured power-zone
bounds. Reading more pages of latest.json could not supply the missing bounds,
and repeatedly loading the validator/docs wasted model calls. This purpose-built
read replaces that search; the full source stays private and authoritative.
