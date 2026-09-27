# Civil-works invoice audit: final architecture (CW-2025-0417-CIV)

**Status: final.** Every rule below has been checked against the scanned contract. Every numeric claim was produced by the Step 2 prototype `civilwork_verify.py` (33/33 tests passed) and now reproduces from the Step 3 implementation, which superseded and replaced the prototype. The three questions the contract and data could not settle (Q1–Q3) were decided by the project owner on 2026-09-27; see Part D.
**Scope:** the civil-works subcontract only. Directional drilling is out of scope.
**Supersedes:** `civilwork_audit_architecture_v2.md`. That file, the earlier review, the contract and the source data were not modified.
**Reproduce:** `python my_approach/civilwork/step_3/src/run_civilwork_audit.py` from the repository root (Python ≥ 3.10, standard library only). Outputs go to `my_approach/civilwork/step_3/output/`; tests and the field-by-field comparison with the prototype are described in `my_approach/civilwork/step_3/README.md`. The prototype `civilwork_verify.py` and its `civilwork_verification_output/` were removed after that comparison. Step 2 test evidence is in `civilwork_verification_report.md`.

This document separates four kinds of statement, and each section says which kind it holds:

- **Part A: contract rules.** Established by the contract text, with the page cited. Page = PDF page = printed footer.
- **Part B: data facts.** Established by computation over all 900 applications, 7,746 lines and 2,169 records.
- **Part C: implementation choices.** Decisions of this system, where the contract leaves the method open.
- **Part D: decisions and remaining uncertainty.** Each item states the choice taken and what changes under the alternative.

---

## 0. Output contract

- One row per application `PA-00001 … PA-00900` in the template format.
- `billed_total_cents = application_total × 100`.
- `expected_total_cents` = the **measured total the contract supports** for that application, in halalas (A5.1).
- `flagged = 1` in three cases: `expected ≠ billed`; a line or application breach exists even when the money is unchanged; or a required 31A/45A entry is wrong (A5.3–A5.4).
- `error_category` is the category with the largest money effect. Ties are broken by the fixed order in C6.
- `confidence` is assigned by evidence class (C7).

---

## Part A: Rules established by the contract text

### A1. Eligibility of an application and a line

| # | Rule | Source (page) | Consequence in the audit |
|---|---|---|---|
| A1.1 | Contract reference `CW-2025-0417-CIV`; Subcontractor Ridgeway Civil Engineering LLC | Agreement p1 | Any other reference is a breach and is flagged |
| A1.2 | Work executed on or before the extended Date for Completion (**30 Sep 2026**) is payable; work after it is not | A2 §2.1 p42 (A1 §1.1 p40); Schedule of Variations p38 | Line value 0 |
| A1.3 | The stated period is the first and last day of the items included | Cl 40 p8 | A mismatch is recorded; it has no money effect of its own |
| A1.4 | No application before the last day of its stated period | Cl 41 p8 | Breach, flagged |
| A1.5 | No item may be included whose date lies outside the stated period | Cl 41 p8 | Line value 0 |
| A1.6 | Submit within 21 days of the end of the stated period | Cl 41 p8 | Breach, flagged; no sanction stated (see D, Q3) |
| A1.7 | The Subcontract Sum is measurement of work **actually executed** | Agreement p1 | Basis for Q3: work executed after the submission date is not valued |

### A2. Pricing: the rate for a line

**Build-up**, Cl 27 (p6), "in the following order and no other":

`base → × zone (Sch 2) → × ground (Sch 3) → × night uplift → × rest-day uplift → × band per cent (Sch 4 Pt 3) → × (1 − discount) → round once, half-up, to the halala`

The discount comes from S2 §2.2 p41 and A2 §2.3 p42: "the final factor … before the rounding … and after any rebate". Rounding is Cl 28 p6: "once only … a half halala being rounded upward … not rounded at intermediate steps". A quantity split at a band edge is priced as parts, each at its own rounded rate (Cl 28; Sch 4 Pt 3).

| # | Rule | Source |
|---|---|---|
| A2.1 | **Base rates:** Schedule 1 (60 items) | pp17–19 |
| A2.2 | **Instruments are read in the order issued**; each governs work executed on or after its effective date; later governs earlier for the same item | Schedule of Variations p38; closing words of pp39–43 |
| A2.3 | **Supplement No. 1** (effective 2025-05-01): B.23.010 4,385.00; B.21.020 431.50; A.16.010 1,524.00. D.41.020 monthly: May 214.50, Jun 219.80, Jul 226.40, Aug 223.10, Sep 220.50; after the last month "the rate last published applies until superseded" | p39 |
| A2.4 | **Amendment No. 1** (effective 2025-10-01 for rates): E.54.010 948.00; B.23.010 4,450.00 | p40 |
| A2.5 | **Supplement No. 2**: D.41.020 228.00 from 2025-12-01; **5 % discount** from 2025-12-01 on C.32.030, C.32.010, D.41.020, B.23.010 | p41 |
| A2.6 | **Amendment No. 2**: E.54.010 monthly Apr 976, May 991, Jun 1,013, Jul 1,038, Aug 1,038, Sep 1,052 (2026); **8 % discount** from 2026-04-01 on the same four items | p42 |
| A2.7 | **Amendment No. 3** (issued 2026-05-12, effective **2025-11-01**): C.32.010 1,984.00; A.14.010 56.80 | p43, p38 |
| A2.8 | **31A:** an application submitted **before** the issue date of a back-dated amendment "is not thereby incorrect: it was valued at the rate then in force". Submitted on or after the issue date → the new rate. | Cl 31A p32 |
| A2.9 | **Zone factors** Z1 1, Z2 1.06, Z3 1.145, Z4 1.28; apply to Series A–D only, never E | Sch 2 p20; Cl 29 p6 |
| A2.10 | **Ground factors** G1 0.94, G2 1, G3 1.12, G4 1.375, G5 1.63; apply only to the 15 listed items | Sch 3 p23; Cl 29 |
| A2.11 | **Ground freeze:** "for work executed after 27 September 2025, the ground classification is taken as G2 … whatever the Engineer recorded", i.e. from **28 Sep 2025** | Cl 27A p32 |
| A2.12 | **Night uplift:** 13 listed items (18/22/25 %); "not payable on an item priced at a zone factor exceeding 1.1", so none in Z3 or Z4 | Sch 4 Pt 1 p24; Cl 7 p3; Cl 27A p32 |
| A2.13 | **Rest-day uplift:** 35 % on B.21.020, B.21.030, D.41.030, B.21.040 on Friday or Saturday | Sch 4 Pt 2 p24; Cl 8 p3 |
| A2.14 | **No night and rest-day uplift together** without a written instruction; without one, rest-day alone applies | Cl 8 p3; P11 p13; Sch 4 p26 |
| A2.15 | **Bands:** 8 items; counted from zero at the start of each Contract Year; a measurement crossing a band is divided | Sch 4 Pt 3 pp24–25 (Clause 30 "substituted") |
| A2.16 | **Contract Years:** Year 1 2025-01-05 → 2026-01-04; Year 2 2026-01-05 → 2026-09-30. An extension does not begin a new year. | Cl 3A p32 |
| A2.17 | **Indexed items** C.31.010, D.41.030: base × Site Materials Index(month) / 100, rounded **half-even**, then treated as the rate for Cl 27 | Sch 2A p21; Cl 29A p32 |
| A2.18 | **USD items** B.23.020, B.25.010, C.32.040: USD × halalas-per-USD(month) / 100, rounded **half-even**, before any factor | Sch 2B p22; Cl 26A p32 |

### A3. Evidence and quantity

| # | Rule | Source | Consequence |
|---|---|---|---|
| A3.1 | 17 items are not payable until the named record is delivered; the absence of a record is a breach | Cl 46 p8; Sch 5 p27; Cl 13 p4 | No reference, a missing file, or a reference from the wrong series → line value 0 |
| A3.2 | The record identifies work area, date and quantity, and carries the foreman's signature **and** the Engineer's representative's countersignature | Cl 47 p8; P22 p14 | Either signature missing → line value 0 |
| A3.3 | The record is in the worker's own words and need not use Bill wording; its reference is quoted on the line | Cl 47A p33; Sch 5 p27 | The item is identified from the words in the body (C3), not from an item code |
| A3.4 | Weekly record: a week is measurable only if the record shows ≥ 5 days worked | Cl 47A p33; Sch 5 p27 | Otherwise 0 |
| A3.5 | Hourly items (E.51.010, E.51.030): the quantity is the hours attended **minus one** | Cl 6A p32; S20 p11 | Supported = min(billed, record − 1) |
| A3.6 | Surveyed items B.23.010, B.23.020, E.52.010: a quantity not exceeding the survey by more than 2 % is payable as measured; above that, the survey quantity only | Cl 33 p7; Cl 33A p32; Sch 4 Pt 6 p26 | A quantity below the survey is also "not exceeding" it, so it is payable as billed |
| A3.7 | Other record items: the payable quantity is at most the recorded quantity | Guideline check 5; Cl 46 | Supported = min(billed, record) |
| A3.8 | A quantity in a unit other than Schedule 1's is **rejected in its entirety**, not converted | Cl 26 p6; p19 | Line value 0 |
| A3.9 | Trench depth decides A.12.020 / .030 / .040 | P13 p13 | Used in the record classifier (C3) |

### A4. Limits across applications

| # | Rule | Source | Consequence |
|---|---|---|---|
| A4.1 | **Duplicate:** the same item, work area and date appearing more than once, in one application or across several → the later one is disallowed in full | Cl 44 p8 | Line value 0 |
| A4.2 | **Daily limits** per work area per day: A.11.010 4,500; A.12.010 1,200; B.21.020 140; C.32.010 6; D.41.030 3,200; E.51.020 1; A.13.030 800; C.32.030 3; E.53.010 2. The excess is not payable and is not carried forward. | Cl 31 p6; Sch 4 Pt 4 p26; Cl 19 p4; P6 p12 | Cut to the limit |
| A4.3 | **A.14.020 is excluded by A.14.010** on the same work area "within two days of the measurement". P19 is Part V and prevails over Parts I–III (P1), so the day of measurement itself is included: days 0, 1 and 2. | P19 p13; Cl 32 p6; Sch 4 Pt 5 p26; P1 p12 | Line value 0 |
| A4.4 | E.51.020 is not measurable on a day any of D.41.020/030/050, D.43.010/020 is measured for that work area | P21 p13 | Line value 0 |

### A5. Application level

| # | Rule | Source |
|---|---|---|
| A5.1 | **Total = sum of the line amounts.** Clause 45A separates the "measured total" from the 31A adjustment and the 45A release in the amount payable, so neither of them is part of `application_total`. | Cl 43 p8; Cl 45A p32; Appendix B p36 |
| A5.2 | **Retention** = 5 % of the application total, rounded **down** to the halala | Cl 45 p8; Appendix B |
| A5.3 | **31A adjustment:** the rate difference on work already valued is shown as a **single** adjustment on one application and on no other. Clause 31A names the first application submitted "**on or after**" the issue date; Amendment No. 3 names the first submitted "**after**" it and requires re-measurement of work "already certified". The two texts conflict (see Q1). | Cl 31A p32; A3 p43 |
| A5.4 | **45A release:** on the first application submitted after 30 Sep 2026, half the retention held on all earlier applications is released, rounded down | Cl 45A p32 |
| A5.5 | **Net payable** = measured total + 31A adjustment − retention + 45A release | Cl 45A p32 |

### A6. Where the guidelines and the contract differ (reportable)

1. **Check 7** ("later instrument governs from its effective date") versus **Cl 31A**: pre-issue applications priced at the old A3 rates are correct (88 lines).
2. **Check 5** ("payable up to the record") is overridden in four cases. Cl 33A pays up to 2 % over the survey as billed. Cl 26 rejects a wrong unit in full. Cl 44 disallows a later duplicate in full. Cl 31 means a daily excess is not carried forward.
3. **Check 4** ("signed by whoever the contract says"): Cl 47 requires two signatures.
4. **Check 8**: the discount is the final factor after the band and before rounding (S2/A2), which moves halalas.
5. **Appendix B** prices C.31.010 at 91.37 = 86.20 × 1.06, omitting the 29A index (93.75 with it). 29A is the operative clause; the worked example is inconsistent with it.
6. **Cross-references** to Clauses 26.4, 14.2 and 26.6 (pp39, 40, 43) do not exist. Cl 21 and P25 point to Appendix A for content that is in Appendix C. None of these has a pricing effect.

---

## Part B: Facts established by the data

All figures came from the Step 2 prototype and reproduce from the Step 3 implementation; see `my_approach/civilwork/step_3/output/civilwork_run_summary.json`, `civilwork_ablation.csv` and `civilwork_scenarios.csv`.

### B1. Structure

- 900 applications and 7,746 lines. Keys are unique, there are no orphan lines, and 3–14 lines per application.
- Every line's site and zone equal its application's.
- 60 item codes, each with exactly one description, and that description equals Schedule 1.
- `ground_class` is filled exactly on the 15 Schedule 3 items. `record_ref` is filled exactly on Schedule 5 items, except 4 lines with no reference: PA-00111-12, PA-00111-13, PA-00631-10, PA-00766-12.
- `adjustment` = 0.00 and `retention_released` = 0.00 on 900/900. `retention` = floor(5 %) on 900/900. `net = total − retention` on 900/900.
- Σ lines = total on 899/900. The exception is **PA-00043**, billed 32.18 above its lines.
- Application numbers are not in date order.
- Submission lag runs from −14 to +49 days. **Late:** PA-00613 (26 days), PA-00699 (49), PA-00708 (44). **Early:** PA-00125, submitted 2025-04-15 with its period ending 2025-04-29 and **all six lines executed after submission**.
- PA-00154-03 and PA-00700-01 lie outside their stated periods and after submission.
- Work after 30 Sep 2026 appears on two lines only: PA-00375-07 and PA-00678-10. Those two applications are the only ones submitted after the completion date (2026-10-31 and 2026-10-28).
- Contract reference `CW-2024-0417-CIV` appears on PA-00560 and PA-00711; their lines are otherwise clean.

### B2. Records

- 2,169 files in 9 series: CT 381, CV 120, DW 114, DX 266, JS 368, MO 142, PR 365, PS 143, PT 270.
- Every file has a fixed header, one body line and two signature lines. Its title matches its series and its Ticket matches its file name.
- **26 body patterns** cover every file. The quantity is always the first number in the body.
- Every file has a foreman signature. **DX-00089 alone lacks the countersignature**; it evidences PA-00613-01.
- 2,193 lines cite a reference (2,172 distinct). Three files are missing: CT-00126, MO-00089, PS-00039. Every file is cited.
- PT-00189 evidences PA-00238-09, correctly, and is also cited by PA-00170-04. That line is a B.23.020 mesh item, which needs a JS record; PT-00189 is from another work area and date.
- **The words of every usable record match its line's item: 2,188 of 2,188.** All 51 CT records saying "placed and whacked … m3 of imported stone" evidence A.14.010 at the exact quantity.
- DW records: exactly one per work-area week. Every week begins on a Monday. Days on: 5 days (40 records), 6 (38), 7 (36).
- Quantity against record on usable records:

| Item group | Result |
|---|---|
| Ordinary record items | equal to the record in 1,401/1,401 |
| Hourly items | record − 1 in 284 lines; record in 1 (PA-00243-03) |
| Surveyed items | equal 202; below 140; above but ≤ 2 % in 25; above 2 % in 1 (PA-00312-04: 4 against a survey of 3) |
| Weekly items | 134 lines at 1 |

### B3. Pricing reproduction

- The Part A build-up reproduces **7,703 of 7,746** line amounts exactly. **43 lines in 37 applications** remain; they are decomposed in Appendix B.
- Ablation against that one baseline. Each line shows lines lost / lines gained when the rule is removed or changed:

| Rule removed or changed | Lost / gained |
|---|---|
| 27A freeze | 837 / 2 |
| bands | 859 / 4 |
| Contract Year reset | 268 / 0 |
| USD conversion | 387 / 0 |
| indexation | 274 / 0 |
| discount | 230 / 1 |
| rest-day uplift | 137 / 0 |
| 27A night cap | 84 / 1 |
| 31A | 88 / 0 |
| 31A boundary "on or before" | 2 / 0 |
| freeze from 27 Sep or 29 Sep | 2 / 0 each |
| band order by application date | 72 / 0 |
| reverse tie-break | 8 / 0 |
| half-even final rounding | 116 / 0 |
| half-up conversion rounding | 18 / 0 |
| S1 / A1 / S2 / A2-monthly | 281 / 112 / 56 / 23 lost |

- Each "gained" line is one of the 43 residual lines, billed with that rule applied the wrong way.
- **31A population:** 89 lines of C.32.010 / A.14.010 executed on or after 2025-11-01 in 72 applications submitted before 2026-05-12, billed 902,512.37 in total. 88 of them are at the old rate. PA-00350-02 took the new rate early and added an 18 % uplift it was not entitled to.
- Rate difference on the 89 lines = **60,508.18**: C.32.010 26,521.21 + A.14.010 33,986.97. Without PA-00350-02 it is 59,883.83.
- Applications submitted on 2026-05-12: PA-00006, PA-00023, PA-00380. First after it: PA-00443 (2026-05-14). First after 2026-09-30: PA-00678.
- **45A release** on PA-00678 = floor(8,069,143.47 / 2) = **4,034,571.73** on retention actually held. It would be 4,026,954.02 if retention were recomputed on corrected totals.

### B4. Cross-application facts

- Clause 44 key (item, work area, date): one duplicate, PA-00111-03 / PA-00111-12.
- Daily limits exceeded twice: PA-00845-03 (D.41.030, 3,440 against 3,200) and PA-00243-10 (E.51.020, 3 against 1).
- A.14.020 after A.14.010 on the same work area: one case at day 0 (PA-00801-05 after PA-00801-02), none at day 1 or 2, and nine at exactly day 3. The day-3 cases are the "odd but correct" boundary. P21 conflicts: none. E.53.010 above 2: none.
- Repeated weeks with different dates:

| Item | Repeated site-weeks | Extra lines | Within one application |
|---|---:|---:|---:|
| A.16.010 | 20 | 21 | 2 (DW-00045 on PA-00116; DW-00097 on PA-00395) |
| E.54.010 (no record required) | 17 | 18 | 4 |

  No repeated week shares a date.

---

## Part C: Implementation choices

### C1. Pipeline, one fixed order

```
[1] load CSVs as text, convert money to Decimal     [2] integrity checks (B1); stop on failure
[3] parse records (C3), then line evidence status    [4] line eligibility: term, period, submission date, unit
[5] cross-application pass in order (work_date, application_no, line_no):
    Cl 44 duplicates → Cl 31 daily limits → P19 exclusion → P21
[6] price every line in the same global order, with band counters per (item, Contract Year)
[7] expected line amount = supported quantity at the contract build-up
    (a reduced quantity keeps the band position of the billed quantity)
[8] application level: totals, procedural checks, 31A, 45A
[9] flag, category, confidence → submission rows, line audit trail, application audit trail
```

- **Why global:** bands, daily limits and duplicates depend on lines in *other* applications.
- The band order (work date, then application number, then line number) is the only order that reproduces the billing: application-date order loses 72 lines and the reverse tie-break loses 8.
- Applications cannot be streamed in submission order.

### C2. Band count

- Counted on **billed** quantity in the same global order.
- Counting on supported quantity instead changes no line in this data.

### C3. Record classifier

The item is identified from the **unit and words of the record body**, never from a keyword alone:

| Series | Rule |
|---|---|
| CT | `m3`/`cube` → A.14.010 (including "imported stone"); `capping` → D.41.040; `sub-base`/`Type 1` → D.41.010 |
| DX | "over four metres" or depth > 4 → A.12.040; "between two and four" or 2 ≤ depth ≤ 4 → A.12.030 |
| PR | wall → B.21.040; slab → B.21.030; foundation → B.21.020 |
| PT | 1800 chamber → C.32.030; 400 ductile → C.31.020 |
| JS | chainage → E.52.010; A393 mesh → B.23.020; bar/tonne → B.23.010 |
| CV, MO, PS, DW | one item each |

Checks applied to each line:
- The work area must match exactly.
- The date must match exactly, or for DW the work date must fall in [week beginning, +6].
- DX/PT `Ground` must match `ground_class`.
- Both signatures must be present; a blank or underscore line counts as missing.

Any file outside the 26 known patterns goes to manual review. There are currently none.

### C4. Line value rules, in precedence

1. **0** if the record is missing, from the wrong series or unsigned; if the unit is wrong; if the line is after the term, outside the stated period or after the submission date (Q3); if it is a later duplicate; or if it is excluded under P19.
2. Hourly: record − 1. Surveyed: as billed if within 2 %, otherwise the survey quantity. Other record items: min(billed, record).
3. Cut by the daily limit.
4. Priced by A2.

### C5. Application rules

- `expected_total` = Σ expected line amounts.
- Procedural breaches (A1.1, A1.4, A1.6, Cl 43) set a flag but never zero the total by themselves (Q3).
- **31A:** required adjustment on PA-00443 = 60,508.18 against 0.00 billed, so PA-00443 is flagged `adjustment_31A_omitted` with its total unchanged.
- **45A:** required release on PA-00678 = 4,034,571.73 against 0.00, so PA-00678 is flagged.

### C6. Category dictionary

27 categories are used in this data. The fixed tie-break order is:

`wrong_contract_ref, submitted_before_period_end, submitted_late, total_arithmetic, work_after_term, line_outside_period, duplicate_measurement, duplicate_week, record_missing, record_wrong_series, record_not_countersigned, unit_not_per_schedule, qty_above_survey_tolerance, chargeable_hour_not_deducted, daily_limit_exceeded, mutually_exclusive_item, work_after_submission, rate_superseded, retro_rate_taken_early, index_or_fx_month_wrong, zone_factor_wrong, ground_factor_wrong, ground_factor_after_freeze, night_uplift_zone_cap, uplift_not_eligible, rest_day_uplift_wrong_day, band_not_applied, discount_omitted, discount_early, intermediate_rounding, line_arithmetic, adjustment_31A_omitted, retention_release_45A_omitted`

- Pricing categories come from a **factor-by-factor decomposition** of the billed rate: a search over every stated base, month, zone, ground, uplift, band and discount, keeping the combination with the fewest differences from the contract. The ratio of billed to expected is never used on its own.
- A night uplift lost *because of* a wrong zone factor is reported as `zone_factor_wrong`.

### C7. Confidence (not calibrated; there are no labels)

| Evidence class | Confidence |
|---|---:|
| Explicit arithmetic, unit, term, period or submission-date breach | 0.93 |
| Price rebuilt and decomposed | 0.88 |
| Record-based breach | 0.85 |
| Cross-application limit, duplicate or P19 | 0.82 |
| Procedural breach with no money effect (late, wrong reference) | 0.75 |
| 31A / 45A entry | 0.60 |
| Not flagged | 0.90 |

The confidence of the strongest cause is used.

### C8. Audit trail

- `line_audit_baseline.csv` stores, for every line: base and its source instrument, zone, ground used, uplift, band parts, discount, evidence status, supported quantity, expected amount, notes and categories.
- `application_audit_baseline.csv` stores every cause and the 31A/45A amounts due.

---

## Part D: Decisions taken, and remaining uncertainty

### D1. Decisions by the project owner (2026-09-27)

| # | Clause and conflict | Decision | Alternatives computed |
|---|---|---|---|
| **Q1** | Carrier of the 31A adjustment. Cl 31A (p32) says "on or after" the issue date; A3 (p43) says "after". Three applications fall on the issue date with no contractual tie-break. | **PA-00443**: A3, the later and specific instrument | PA-00006, PA-00023 or PA-00380 instead → still 59 flagged, one application swapped. All four at low confidence → 62. No total changes under any choice (A5.1). |
| **Q2** | Repeated dewatering week. Cl 44 keys on item, work area and **date**; repeated A.16.010 weeks have different dates and share one DW record. | **Not a duplicate.** The literal key does not match; E.54.010 shows the same pattern with no record involved. | Within one application only → 61 (+PA-00116, PA-00395; −3,566.16). All A.16.010 → 77 (+18 applications; −33,902.20). A.16.010 and E.54.010 → 94 (+35; −50,163.20). |
| **Q3** | Expected total for procedural defects (Cl 41, Cl 43, contract reference) | **Value the lines the contract supports as at the submission date. Flag the breach; never zero a total for a procedural defect alone.** PA-00043 = 231,425.26 (arithmetic corrected despite Cl 43 "returned unpaid"). PA-00125 = 0.00 (all work after submission; Agreement p1 "work actually executed"). PA-00613, 699, 708, 560, 711 are flagged at their supported totals. | Keep after-submission lines → PA-00125 +25,068.53. Cl 43 → 0 → PA-00043 −231,425.26. Every procedural defect → 0 → 6 totals, −1,110,666.24. |

### D2. Readings resolved by text (no decision needed)

| Question | Resolution |
|---|---|
| Is day 0 inside the P19 / Cl 32 exclusion? | Yes: P19 says "within two days **of**", and P1 gives Part V precedence. The data agrees: no cases at days 1–2 and nine at day 3. Alternatives: days 1–2 only → 58 flagged; days 0–3 → 67. |
| Does a missing 31A or 45A entry change `application_total`? | No: Cl 43 and Cl 45A make the total the measured total. The application is still flagged (A5.3, A5.4). |
| 27A freeze start | Work "after 27 September" means from 28 Sep. Confirmed by PA-00036-07 and PA-00684-06 (27 Sep, G1) and PA-00105-04 (28 Sep, G2). |
| Contract Year 2 | Starts 2026-01-05 under 3A. The sentence about extensions stops an *extension* from starting a year; it does not stop the anniversary. 268 lines depend on this. |
| Surveyed quantity below the survey | Payable as billed under 33A ("not exceeding"). |
| 45A carrier | PA-00678 is the first application submitted after 30 Sep 2026. The text is unambiguous even though the application is itself defective. |

### D3. Remaining uncertainty and its effect

| Item | Effect on the submission |
|---|---|
| **31A adjustment basis:** all 89 lines (60,508.18), or excluding the mis-valued PA-00350-02 (59,883.83); A3 speaks of work "already certified", and certification is not in the data | None on flag or total; reporting only |
| **45A basis:** retention held (4,034,571.73) or retention on corrected totals (4,026,954.02) | None on flag or total |
| **Part VII precedence:** 3A, 6A, 26A, 27A, 29A, 31A, 33A, 45A and 47A are not listed in Contents, in Cl 2 or in P1. Their precedence is inferred from specificity and confirmed by the data (hundreds of lines each). | If Part VII did not govern, most of B3 would fail. Treated as settled. |
| **Cl 47 vs 47A:** no record states an item code | Reading (c): identify the item from the series plus the words (C3). The strict Cl 47 reading would zero about 28 % of lines that reconcile, and is rejected. |
| **P3** (no standing time in Z4 "failure to programme deliveries") against PS records "waiting on access" | Not applied: it would reprice 25 lines in 24 applications that reconcile, and "waiting on access" does not state the P3 cause. |
| **S20:** standby alongside other work on the same day (126 of 143 E.51.010 lines) | Not applied; the text does not forbid it. |
| `night_work` flag taken as given; no clock times exist | Unverifiable |
| Grader's encoding of `expected_total_cents` for 31A, 45A and procedural rows | Unknown. Our values follow A5.1 and Q3. |
| Confidence values | Not calibrated |

---

## Verification summary

- **Contract text.** All 43 pages rendered; 33 rule-bearing pages compared by eye against the transcription with no difference. Not compared: pp2, 5, 15, 16, 28–31, 35 and 37 (contents, HSE, dayworks, PS/PC sums, preliminaries, execution, insurances). No rule the data exercises comes from those pages.
- **Data.** Every check in Parts A and B was run on all 900 applications, 7,746 lines and 2,169 records.
- **Tests.** 33/33 named prototype tests passed, and repeated runs were deterministic. Their checks are carried into the Step 3 test suite (`my_approach/civilwork/step_3/tests/`).
- **What is not proven.** Without labels, the match rates show which rules the billing applied; they are not a measured precision or recall.

### Corrections relative to v2

1. **PA-00801-05.** v2 left it as an interpretive question. P19 settles it: excluded, and flagged at confidence 0.82.
2. **31A carrier.** Decided as PA-00443. v2's application counts of 59 / 76 / 77 are replaced by one baseline: 59 flagged, with PA-00443 in place of PA-00006.
3. **`expected_total` for 31A/45A.** Now established by Cl 43 and 45A rather than left open. PA-00443 and PA-00678 are flagged regardless.
4. **Q3 amounts made explicit.** PA-00125 = 0 (v2 had its supported total); PA-00043 = Σ lines; late and wrong-reference applications keep their supported totals.
5. **PA-00375 and PA-00678 lateness.** v2 suggested measuring lateness after dropping the invalid lines. Under Cl 41 the stated period includes the after-term line, so these two are *not* late in text. They are flagged for work after the term (and PA-00678 for 45A).
6. **Surveyed lines below the survey (140).** Now explicitly payable as billed under 33A.
7. **Seven boundary ablations added** (B3): the 31A boundary, freeze 27/29 Sep, band ordering and both rounding modes. Each confirms v2's reading.
8. **Under-billed applications are flagged with a higher expected total:** PA-00248, 297, 610, 659, 803 and 889. PA-00297-07 alone is under-billed by 152,616.24 (D.41.020 billed at the Schedule 1 base rate of 63.50).
9. **Extra readings tested and rejected, with counts:** P3, S20, and bands on supported quantity (D3).

---

## Appendix A: Final baseline, 59 flagged applications

Amounts in SAR; Δ = expected − billed.

| Application | Category | Billed | Expected | Δ | Conf. |
|---|---|---:|---:|---:|---:|
| PA-00043 | total_arithmetic | 231,457.44 | 231,425.26 | −32.18 | 0.93 |
| PA-00052 | unit_not_per_schedule | 102,099.03 | 97,859.99 | −4,239.04 | 0.93 |
| PA-00090 | index_or_fx_month_wrong | 119,591.35 | 119,430.70 | −160.65 | 0.88 |
| PA-00101 | index_or_fx_month_wrong | 385,551.53 | 385,195.37 | −356.16 | 0.88 |
| PA-00111 | record_missing (+duplicate) | 375,442.26 | 368,252.12 | −7,190.14 | 0.85 |
| PA-00115 | intermediate_rounding | 185,582.92 | 185,579.92 | −3.00 | 0.88 |
| PA-00120 | zone_factor_wrong | 140,818.01 | 140,159.85 | −658.16 | 0.88 |
| PA-00125 | work_after_submission (+early) | 25,068.53 | 0.00 | −25,068.53 | 0.93 |
| PA-00138 | rest_day_uplift_wrong_day | 103,408.58 | 94,477.52 | −8,931.06 | 0.88 |
| PA-00154 | line_outside_period | 90,678.40 | 89,374.24 | −1,304.16 | 0.93 |
| PA-00170 | record_wrong_series | 317,208.79 | 254,986.63 | −62,222.16 | 0.85 |
| PA-00243 | daily_limit_exceeded (+chargeable hour) | 94,099.16 | 92,485.16 | −1,614.00 | 0.85 |
| PA-00248 | rate_superseded | 30,917.93 | 31,121.67 | +203.74 | 0.88 |
| PA-00268 | discount_omitted | 81,404.75 | 79,170.59 | −2,234.16 | 0.88 |
| PA-00291 | ground_factor_wrong | 126,599.91 | 119,496.21 | −7,103.70 | 0.88 |
| PA-00297 | rate_superseded (+zone) | 208,403.01 | 359,886.87 | +151,483.86 | 0.88 |
| PA-00312 | band_not_applied (+survey tolerance) | 287,499.89 | 285,485.74 | −2,014.15 | 0.88 |
| PA-00320 | zone_factor_wrong (+ground) | 54,800.86 | 53,696.16 | −1,104.70 | 0.88 |
| PA-00350 | retro_rate_taken_early (+uplift) | 28,983.13 | 26,560.68 | −2,422.45 | 0.88 |
| PA-00374 | band_not_applied | 173,295.39 | 172,531.43 | −763.96 | 0.88 |
| PA-00375 | work_after_term | 337,523.03 | 336,580.69 | −942.34 | 0.93 |
| PA-00406 | unit_not_per_schedule (+discount early) | 144,671.39 | 136,889.63 | −7,781.76 | 0.93 |
| PA-00443 | adjustment_31A_omitted | 280,688.88 | 280,688.88 | 0.00 | 0.60 |
| PA-00468 | zone_factor_wrong | 32,093.20 | 28,736.71 | −3,356.49 | 0.88 |
| PA-00489 | rate_superseded (+discount) | 129,105.08 | 128,586.56 | −518.52 | 0.88 |
| PA-00496 | band_not_applied | 244,989.11 | 244,407.66 | −581.45 | 0.88 |
| PA-00503 | ground_factor_after_freeze | 143,997.69 | 133,496.62 | −10,501.07 | 0.88 |
| PA-00509 | ground_factor_wrong | 92,426.41 | 86,591.90 | −5,834.51 | 0.88 |
| PA-00560 | wrong_contract_ref | 351,571.74 | 351,571.74 | 0.00 | 0.75 |
| PA-00609 | record_missing | 118,237.40 | 105,031.16 | −13,206.24 | 0.85 |
| PA-00610 | line_arithmetic | 47,873.44 | 47,904.44 | +31.00 | 0.93 |
| PA-00613 | record_not_countersigned (+late) | 88,779.08 | 60,849.08 | −27,930.00 | 0.85 |
| PA-00631 | record_missing | 219,994.52 | 188,446.52 | −31,548.00 | 0.85 |
| PA-00636 | ground_factor_wrong (+zone) | 149,066.61 | 145,232.01 | −3,834.60 | 0.88 |
| PA-00659 | line_arithmetic | 300,595.57 | 300,600.57 | +5.00 | 0.93 |
| PA-00668 | night_uplift_zone_cap | 88,993.72 | 88,064.68 | −929.04 | 0.88 |
| PA-00672 | record_missing (+line arithmetic) | 96,171.04 | 95,243.04 | −928.00 | 0.93 |
| PA-00678 | work_after_term (+record missing, 45A) | 526,097.77 | 510,294.90 | −15,802.87 | 0.93 |
| PA-00699 | submitted_late | 42,823.05 | 42,823.05 | 0.00 | 0.75 |
| PA-00700 | line_outside_period | 49,814.70 | 16,211.98 | −33,602.72 | 0.93 |
| PA-00707 | zone_factor_wrong | 35,989.42 | 33,676.34 | −2,313.08 | 0.88 |
| PA-00708 | submitted_late | 213,031.90 | 213,031.90 | 0.00 | 0.75 |
| PA-00711 | wrong_contract_ref | 210,965.21 | 210,965.21 | 0.00 | 0.75 |
| PA-00732 | uplift_not_eligible | 184,907.74 | 184,307.98 | −599.76 | 0.88 |
| PA-00738 | rate_superseded (+discount) | 230,452.21 | 225,709.81 | −4,742.40 | 0.88 |
| PA-00761 | ground_factor_wrong (+zone) | 84,513.96 | 75,852.04 | −8,661.92 | 0.88 |
| PA-00766 | record_missing | 313,278.66 | 197,454.66 | −115,824.00 | 0.85 |
| PA-00768 | ground_factor_after_freeze (+uplift) | 81,520.26 | 72,451.67 | −9,068.59 | 0.88 |
| PA-00787 | zone_factor_wrong | 180,257.83 | 178,486.18 | −1,771.65 | 0.88 |
| PA-00801 | mutually_exclusive_item | 112,149.23 | 106,594.03 | −5,555.20 | 0.82 |
| PA-00803 | discount_early | 403,350.62 | 409,254.48 | +5,903.86 | 0.88 |
| PA-00817 | rate_superseded (+zone, discount) | 174,812.18 | 164,982.82 | −9,829.36 | 0.88 |
| PA-00822 | uplift_not_eligible | 84,484.32 | 81,732.78 | −2,751.54 | 0.88 |
| PA-00833 | unit_not_per_schedule | 52,758.67 | 47,860.97 | −4,897.70 | 0.93 |
| PA-00845 | daily_limit_exceeded | 392,233.85 | 368,284.25 | −23,949.60 | 0.82 |
| PA-00871 | band_not_applied | 85,224.47 | 84,941.43 | −283.04 | 0.88 |
| PA-00889 | rate_superseded | 311,490.48 | 311,578.68 | +88.20 | 0.88 |
| PA-00892 | unit_not_per_schedule | 75,201.33 | 73,223.10 | −1,978.23 | 0.93 |
| PA-00898 | ground_factor_wrong | 62,756.66 | 60,533.54 | −2,223.12 | 0.88 |

## Appendix B: The 43 residual lines, decomposed

| Type | Lines |
|---|---|
| Wrong zone factor (9) | PA-00120-04, -00297-02, -00320-02, -00468-01, -00636-06, -00707-04, -00787-05, -00817-04, -00761-02 (billed as Z3, so a valid night uplift was lost: under-billed) |
| Wrong ground factor before the freeze (6) | PA-00291-05, -00320-04, -00509-02, -00636-02, -00761-06, -00898-01 |
| Ground factor after the freeze (2) | PA-00503-03, -00768-04 |
| 18 % on an ineligible item (4) | PA-00732-05, -00768-03, -00822-06, -00350-02 (also the A3 rate before issue) |
| Rest-day uplift on a Tuesday (1) | PA-00138-09 |
| Night uplift in Z4 (1) | PA-00668-02 |
| Band not applied (4) | PA-00312-05, -00374-02, -00496-02, -00871-04 |
| Discount early (2) / omitted (1) | PA-00406-02, -00803-12 / PA-00268-03 |
| Superseded rate (6) | PA-00297-07 (D.41.020 at 63.50), -00738-03 (July 2025 D.41.020 rate), -00248-05 and -00889-08 (A.14.010 at 53.20 in post-issue applications), -00489-02 and -00817-02 (B.23.010 at 4,385 without discount) |
| Wrong index/FX month (3) | PA-00090-01 (Feb 2026 index), -00101-07 (FX 377.00), -00375-07 (Feb 2026 FX; also after the term) |
| Amount ≠ quantity × rate (3) | PA-00610-02, -00659-03, -00672-02 |
| Intermediate rounding (1) | PA-00115-05 |

Where a stale rate also shows a different band per cent (PA-00248-05, -00489-02, -00817-02, -00889-08), the expected amount always comes from the engine's band counter, never from "correcting" the billed ratio.

## Appendix C: Worked checks

**PA-00001-01**, correct as billed. D.43.010, Z2, night: 14.80 × 1.06 × 1.25 = 19.61; × 299 = **5,863.39**.

**PA-00576-09 / CT-00124**, correct as billed. A.14.010, Year 1, cumulative 7,935 before this line, so 65 m3 at 95 % and 66 m3 at 91 %:
- 53.20 × 0.95 = 50.54; 53.20 × 0.91 = 48.41
- 65 × 50.54 + 66 × 48.41 = **6,480.16**. The record says "131 m3 of imported stone": A.14.010, matching.

**PA-00003-06**, correct as billed (31A pre-issue). C.32.010 at the old rate, freeze to G2, 5 % discount: 1,860 × 1.06 × 0.95 = 1,873.02; × 5 = 9,365.10. At the new rate it would be 9,989.45, and the difference of 624.35 goes into the 60,508.18 adjustment on PA-00443.

**PA-00243**, flagged:

| Line | Item | Billed | Contract | Δ |
|---|---|---|---|---:|
| -03 | E.51.010 | 10 h | 9 h under 6A | −246.00 |
| -10 | E.51.020 | 3 days | 1 day under Cl 31 | −1,368.00 |

Expected total **92,485.16**.

**PA-00115-05**, flagged. 69.20 × 1.28 × 1.375 = 121.792 → 121.79. The billed 121.80 rounds after the zone step. Δ −3.00.
