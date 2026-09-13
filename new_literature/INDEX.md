# New Literature Index — Run + Bike Expansion for Section 11

Purpose: map the `new_literature/` papers onto the Section 11 coach so run-plus-bike
gets the same "science, not speculation" footing cycling already has.

Status: **21 papers present** (20 unique MD topics + 1 PDF companion), **2 to fetch** (Kenneally 2018 elite-TID review, Daniels VDOT book — both deliberately skipped, see below).

## Rename execution status (read first)

Most renames are applied; four files are still pending (Billat 2000 + 2001,
Barnes-Kilding 2015, Hreljac 2004 — top-level listing confirms nothing else
remains unmoved). History: the first `rename.sh` run moved everything present
at the time; later-added files stranded re-runs because the original script
aborted on already-moved entries (`set -e` + unconditional `mv`). Fixed
2026-09-12: `rename.sh` is idempotent (every entry attempted, missing sources
reported as done/conflict/broken instead of aborting) and `check_rename.sh`
guards the mapping. Shell execution is blocked in this environment (`bwrap:
setting up uid map: Permission denied`; unsandboxed run needs human approval,
which is disabled), so neither script was run here. To finish, run from the
repo root:

`bash new_literature/rename.sh && bash new_literature/check_rename.sh`

then re-check this index against the new paths. Paper identity below was
verified from file headers (no content copied or altered).
Prefer the `.md` version for LLM use; the single `.pdf` is a companion only.

## How Section 11 is built today (what this maps onto)

- `SECTION_11.md` → "Core Evidence-Based Foundations" table grounds everything
  (Seiler, Banister, Foster, Coggan, Skiba, Mujika/Bosquet, Gabbett/Impellizzeri,
  Rogers DFA a1).
- `examples/workout-library/WORKOUT_REFERENCE.md` → 26-template **cycling-only**
  library. Workouts must be selected from it.
- Running is explicitly deferred: threshold-run tests, pace curve, and running
  DFA a1 are flagged `validated: false`.

## Folder structure

```text
new_literature/
  INDEX.md                          <- this file
  rename.sh                         <- applies the renames below (re-runnable)
  check_rename.sh                   <- regression test for the mapping
  01_concurrent-interference/
  02_bike-run-transition/
  03_run-TID/
  04_run-prescription-CP-VDOT/
  05_run-intervals-HIIT/
  06_load-injury-economy/           <- complete: Foster, Nielsen, Barnes, Hreljac
```

## Naming convention

`AuthorYear_Journal_Short-Title.md` — no spaces, no MinerU hash suffix.
PDF companions share the MD stem with a `.pdf` extension.

## Tier 0 — load-bearing walls (fetch first)

| # | Paper (canonical) | File | Protocol mapping |
|---|-------------------|------|------------------|
| T0.1 | Hickson RC. Interference of strength development by simultaneously training for strength and endurance. Eur J Appl Physiol. 1980;45:255–263. | `01_concurrent-interference/Hickson1980_EJAP_Interference-Strength-Endurance.md` ✅ present | Hard-day spacing + sequencing rules; asymmetric interference (strength/power blunted, VO2max not). |
| T0.2 | Wilson JM et al. Concurrent training: a meta-analysis examining interference of aerobic and resistance exercise. J Strength Cond Res. 2012;26(8):2293–2307. | `01_concurrent-interference/Wilson2012_JSCR_Concurrent-Training-Meta-Analysis.md` ✅ present | Quantifies T0.1 on 21 studies / 422 ES: strength 1.76→1.44 concurrent, power hit hardest (0.91→0.55, all 3 groups differ), hypertrophy 1.23→0.85; running (not cycling) drives hypertrophy+strength decrements; frequency/duration dose the damage. |
| T0.3 | Millet GP, Vleck VE. Cycle-run transition review + practical recommendations. Br J Sports Med. 2000;34(5):384–390. | `02_bike-run-transition/Millet-Vleck2000_BJSM_Cycle-Run-Transition-Review.md` ✅ present (MD + PDF companion) | Justifies brick sessions as their own workout category; CR rise 1.6–11.6%, trunk-lean cue, transition skill. |
| T0.4 | Millet GP, Vleck VE, Bentley DJ. Physiological differences between cycling and running. Sports Med. 2009;39(3):179–206. | `02_bike-run-transition/Millet-Vleck-Bentley2009_SportsMed_Physiological-Differences-Cycling-Running.md` ✅ present | Mandatory per-sport thresholds; backs "running HR ~5–10 bpm higher" rule. |
| T0.5 | Etxebarria N et al. Cycling attributes that enhance running after the cycle section. IJSPP. 2013;8(5):502–509. | `02_bike-run-transition/Etxebarria2013_IJSPP_Cycling-Attributes-Running-Performance.md` ✅ present | Brick design + bike-pacing constraints: 1 h variable (40–140% MAP) vs constant @65% MAP → 9.3 km run 42±37 s slower, ~85% of loss in first half; high end-bike lactate/RPE predicts impairment. |
| T0.6 | Etxebarria N et al. High-intensity cycle intervals improve cycling and running in triathletes. Eur J Sport Sci. 2014;14(5):521–529. | `02_bike-run-transition/Etxebarria2014_EJSS_HIIT-Cycle-Improves-Cycling-Running.md` ✅ present | Both SHORT (10/20/40 s) and LONG (5 min) ×6 over 3 wk raise VO2peak ~7%; only LONG substantially improves post-bike 5 km (−64±59 s). |

## Tier 1 — running intensity distribution + prescription (mirrors Seiler/Coggan for the run leg)

| # | Paper (canonical) | File | Protocol mapping |
|---|-------------------|------|------------------|
| T1.1 | Esteve-Lanao J et al. Impact of training intensity distribution on performance in endurance athletes. J Strength Cond Res. 2007;21(3):943–949. | `03_run-TID/Esteve-Lanao2007_JSCR_Impact-Training-Intensity-Distribution.md` ✅ present | First RCT for polarized-in-runners: Z1-emphasis (80.5/11.8/8.3) beats Z2-emphasis (66.8/24.7/8.5) on 10.4 km XC (−157±13 s vs −121.5±7.1 s). Extends Seiler TID to running. |
| T1.2 | Muñoz I et al. Does polarized training improve performance in recreational runners? IJSPP. 2014;9(2):265–272. | `03_run-TID/Munoz2014_IJSPP_Polarized-Recreational-Runners-10K.md` ✅ present | Polarized (77/3/20) vs between-thresholds (46/35/19) at ~4 h/wk: 5.0% vs 3.6% 10K gain; strict-adherer subset d=1.29. Recreational-runner TID anchor. |
| T1.3 | Stöggl T, Sperlich B. Polarized training has greater impact on key endurance variables. Front Physiol. 2014;5:33. | `03_run-TID/Stoggl-Sperlich2014_FrontPhysiol_Polarized-vs-Threshold-HIIT-Volume.md` ✅ present | POL beats THR/HIIT/HVT on VO2peak (+11.7%), TTE (+17.4%), peak velocity/power (+5.1%) over 9 wk in runners/cyclists/triathletes/XC skiers. Intervention anchor bridging bike→mixed programming. |
| T1.4 | Casado A et al. Training periodization, methods, TID, volume in elite distance runners: systematic review. IJSPP. 2022. | `03_run-TID/Casado2022_IJSPP_Periodization-TID-Volume-Elite-Runners.md` ✅ present | Elites run pyramidal base → polarized competition; marathoners more pyramidal, 1500 m more polarized; hard-day/easy-day periodization. Calibrates run TID targets separately from cycling. |
| T1.5 | Kenneally M et al. Periodisation and TID in middle/long-distance running: systematic review. IJSPP. 2018 (accepted ms Nov 2017). | `03_run-TID/Kenneally2017_IJSPP_Periodisation-TID-Systematic-Review.md` ✅ present | Companion to T1.4 on periodisation×TID interaction for 1500 m–marathon. |
| T1.6 | SKIPPED — Kenneally M et al. TID of elite/highly-trained distance runners (IJSPP, 2018; ~135 km/wk, ~87/6/7). | — | Deliberately not fetched: Casado 2022 (T1.4) covers the same ground; marginal value is one split number. |
| T1.7 | Jones AM et al. Critical power: implications for VO2max and exercise tolerance. MSSE. 2010;42(10):1876–1890. | `04_run-prescription-CP-VDOT/Jones2010_MSSE_Critical-Power-VO2max-Tolerance.md` ✅ present | CP/CS = asymptote of hyperbolic P/V–t relation, W′/D′ curvature constant; heavy/severe boundary. Running's FTP-twin alongside Daniels VDOT. |
| T1.8 | Poole DC et al. Critical power: an important fatigue threshold. MSSE. 2016;48(11):2320–2334. | `04_run-prescription-CP-VDOT/Poole2016_MSSE_Critical-Power-Fatigue-Threshold.md` ✅ present | CP as the stabilizable/non-stabilizable fatigue threshold; Tlim = W′/(P−CP). Threshold-test section + pace-curve prescription. |
| T1.9 | SKIPPED as a fetch — Daniels J. Daniels' Running Formula. 4th ed. Human Kinetics, 2022. (book) | — | Reference only: VDOT derives all run paces from one performance anchor — conceptual twin of FTP-based prescription. Summarize tables, don't ingest the book. |

## Tier 2 — interval design + load monitoring for runners

| # | Paper (canonical) | File | Protocol mapping |
|---|-------------------|------|------------------|
| T2.1 | Buchheit M, Laursen PB. HIIT solutions to the programming puzzle. Part I: cardiopulmonary emphasis. Sports Med. 2013;43(5):313–338. | `05_run-intervals-HIIT/Buchheit-Laursen2013_SportsMed_HIIT-Part1-Cardiopulmonary.md` ✅ present | 9-variable HIIT prescription (work/relief intensity×duration, modality, reps, series, between-series recovery); time ≥90% VO2max as the cardo stimulus. Builds the run interval library the way Rønnestad/Billat built cycling. |
| T2.2 | Buchheit M, Laursen PB. Part II: anaerobic, neuromuscular load, practical applications. Sports Med. 2013;43(10):927–954. | `05_run-intervals-HIIT/Buchheit-Laursen2013_SportsMed_HIIT-Part2-Neuromuscular-Practical.md` ✅ present | Same-max-cardo formats differ in glycolytic/neuromuscular cost; ≥95% v/pVO2max volumes (6–8 km @vVO2max) strain musculoskeletal system — periodize accordingly. |
| T2.3 | Billat VL et al. Intermittent runs at vVO2max enable longer time at VO2max than intense submaximal runs. J Appl Physiol. 2000. | `05_run-intervals-HIIT/Billat2000_JAP_30-30-vVO2max-Time-at-VO2max.md` ✅ present | 30 s at 100% / 30 s at 50% vVO2max → 7:51 at VO2max vs 2:42 on the continuous vΔ50 run, lower lactate trend (n=8 track runners). Running counterpart to Rønnestad 30/15 in the repo. |
| T2.4 | Billat VL et al. Very short (15 s–15 s) interval-training around critical velocity allows maintaining VO2max for 14 minutes. Int J Sports Med. 2001;22:201–208. | `05_run-intervals-HIIT/Billat2001_IJSM_15-15-Critical-Velocity-14min.md` ✅ present | Small-amplitude 15/15 at mean critical velocity (90–80% and 100–70% vVO2max) → 14 min at VO2max vs 7 min for wide-amplitude (110–60%), lactate 9 vs 11 mmol/L. Very-short-interval anchor for the run library. |
| T2.5 | Foster C et al. A new approach to monitoring exercise training. J Strength Cond Res. 2001;15(1):109–115. | `06_load-injury-economy/Foster2001_JSCR_Session-RPE-Monitoring.md` ✅ present | Session RPE × duration validated against HR-based TRIMP across steady-state + interval cycling and basketball; mode- and intensity-independent load currency uniting bike+run alongside TRIMP/TSS. |
| T2.6 | Barnes KR, Kilding AE. Strategies to improve running economy. Sports Med. 2015;45(1):37–56. | `06_load-injury-economy/Barnes-Kilding2015_SportsMed_Running-Economy.md` ✅ present | RE = submaximal VO2 at a given velocity. Levers: training history/volume, uphill + level HIIT, short-term resistance/plyometrics (neuromuscular), altitude, optimal — not maximal — stiffness, nitrates/caffeine. Running-efficiency pillar (no cycling equivalent). |
| T2.7 | Hreljac A. Impact and overuse injuries in runners. Med Sci Sports Exerc. 2004;36(5):845–849. | `06_load-injury-economy/Hreljac2004_MSSE_Impact-Overuse-Injuries.md` ✅ present | Fatigue-curve framing: sub-tensile-limit stress + adequate rest → remodeling and a stronger structure; inadequate rest → overuse injury. Large/rapid impact forces flag at-risk runners; stress should be optimal, not minimal. Mechanistic base under the RUNSAFE sudden-onset finding. |
| T2.8 | Frandsen JSB et al. (Nielsen RO senior author). A paradigm shift in understanding overuse running-related injuries: findings from Garmin-RUNSAFE point to sudden not gradual onset. JOSPT Open. 2025;3(1):85-92. | `06_load-injury-economy/Nielsen2025_JOSPT_Garmin-RUNSAFE-Sudden-Onset.md` ✅ present | 1,666 injuries: 28% overload, 72% overuse — yet only 6.9% had a preceding problem 7 d prior (11.1% at 28 d): overuse onset is sudden-repetitive, not gradual. Backs run-specific spike rules instead of reusing cycling ACWR bands; pair with Impellizzeri ACWR critique already in protocol. |

## Already covered — don't re-fetch

Taper (Mujika & Padilla 2003; Bosquet et al. 2007: ~2% mean gain, cut volume ~50%,
keep intensity), block periodization (Issurin), TRIMP/monotony (Banister/Foster),
Seiler 80/20 itself.

## Open gap (do not paper over)

Running DFA a1 has no established 0.75/0.50 validation — protocol keeps it
`validated: false` for non-cycling. Don't fetch HRV-threshold papers expecting a
running equivalent yet.

## Rename map (old → new, applied by `rename.sh`)

See `rename.sh` in this folder for the exact mapping (one `move_one "src"
"dst"` line per file). Summary: strip the `MinerU_markdown_` prefix and
trailing `_<digits>` hash, expand to `AuthorYear_Journal_Short-Title`, and move
into the tier folder above. `384.full.pdf` moves alongside its MD twin as the
`.pdf` companion. Old basenames are listed verbatim in `rename.sh` so the
script is auditable, and `check_rename.sh` fails if any top-level MinerU file
lacks an entry or any entry maps to nothing.
Verification performed for this index: first-line/header read of all 21 present
MD files (incl. Wilson 2012, Foster 2001, Nielsen 2025, Billat 2000 + 2001,
Barnes-Kilding 2015, Hreljac 2004) to confirm paper identity before naming
(no content copied or altered).
