# Event specificity and additional training

The optional `block.event_preparation`, `block.durability_context` and `block.strength_context` fields extend the private plan contract. These capture the athlete's context and enforce arithmetic/source distinctions; they do not prescribe a universal taper, fatigue threshold, heavy-lifting routine or guaranteed performance gain. Ordinary plans need none of them. The relevant [paper takeaways](../../literature/cycling-training/TAKEAWAYS.md) remain the evidence authority.

## Event preparation

`event_preparation` requires `goal_id` referring to a dated goal, nullable `expected_duration_minutes`, `terrain`, `decisive_demands`, `recent_training_reference` evidence entries and nullable `taper`. Priority never fills duration. Unknown duration surfaces a decision-relevant question; it does not automatically cancel cycling or invent a long-event plan.

A taper has `start_date`, `end_date` before the event, positive `reference_minutes` from stated completed-training evidence, `planned_minutes`, rationale and boolean `familiar_intensity`. Planned minutes must equal the full selected prescription durations in that explicit period, including all preparation/recovery and other sports. The chosen period/reference must be comparable; that is a supplied coaching judgment, not independently authenticated by the arithmetic. A taper cannot manufacture overload above its own stated reference. The output reports the resulting reduction, with no required 41–60% band, CTL multiplier, mandatory overload, fixed TSB goal or minimum demanding-session count.

[Wang's takeaway](../../literature/cycling-training/papers/37163550/takeaways.md) supports a taper benefit while retaining uncertain subgroup comparisons and small samples. Maintaining familiar intensity is a possible component, not an instruction to add hard work when symptoms, low prior training or availability make it inappropriate. Short and long A-events need their actual demands, not category-derived assumptions. Tapering and ordinary recovery remain different decisions.

Sync's race calendar now emits `policy_version: event_specific_v1`. Timing remains informational. Legacy CTL-derived budgets and TSB targets become null, and invalid/missing event duration remains unknown. Day prompts offer review topics rather than numerical doses. Read current readiness and athlete feedback; event importance never overrides active P0/P1 or health clarification. No new illness-return or detailed fueling algorithm is introduced.

## Durability

`durability_context` contains `fresh`, `fatigued` and `interpretation`. Each observation is nullable; a populated observation has source/date, assessment identity, `assessment_seconds`, `power_watts`, `prior_minutes`, `prior_work`, prior_intensity, environment, pacing, fueling and conditions. `prior_work` is null or `{"value": ..., "unit": "kJ_mechanical"}`. Dietary kcal are rejected. Mechanical work, where derived from a valid power timebase, is the integral of watts × seconds divided by 1000, not caloric expenditure.

The comparison is unavailable when essential context is missing or assessment duration/method, environment, pacing, fueling or conditions differ. It never fills missing values with zero. A qualified power-window difference is descriptive, not a causal fitness change, a comparison of whole-session averages or an equivalence to HR:power decoupling. Prior intensity and duration remain visible; no universal accumulated-kJ threshold defines fatigue. Existing decoupling eligibility gates remain. Do not require exhaustive testing or long rides where unrelated to the objective.

[Sánchez-Jiménez's takeaway](../../literature/cycling-training/papers/40613880/takeaways.md) concerns acute performance under prior work, not a proven optimal long-term training program. Use suitable existing rides first and preserve context before changing fitness estimates.

## Optional strength

`strength_context` records goal, experience, equipment, technique, soreness, `arrangement` (`add`/`replace`), `displaced_sessions`, recovery_plan and `evidence_certainty: low`. Replacement must name displaced/reduced training; the description is supplied judgment. Actual timed WeightTraining sessions count in combined session/day/week capacity. Low-cadence cycling remains distinct from heavy resistance training.

Unknown lifting preparation surfaces a targeted question and does not by itself veto ordinary cycling. Experience, technique, symptoms, soreness and recovery affect exercise selection/progression; the timed plan entry alone is not an exercise prescription or clearance. Adding strength is a different decision from replacing cycling under fixed time. Review its sustainability and effect on goal-relevant riding.

[Llanos-Lagos's takeaway](../../literature/cycling-training/papers/40632222/takeaways.md) reports possible benefits with low certainty. It does not justify a universal routine, guaranteed gain or cost-free extra load. The application stores context and checks capacity; it does not automate heavy-load exercise technique.

## Worked context

[Synthetic input](../json-examples/event_context.example.json) and [output](../json-examples/event_context_output.example.json) show a 20% chosen taper reduction, a qualified power comparison and an explicitly budgeted optional strength context. These are engineering examples, not recommendations to copy or evidence that the application improves performance. Missing-context and incompatible-unit cases are tested separately.
