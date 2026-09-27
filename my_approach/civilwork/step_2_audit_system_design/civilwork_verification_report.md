# Verification results: civil-works audit architecture (CW-2025-0417-CIV)

Date: 2026-09-27. Scope: civil-works contract only.
Code: `civilwork_verify.py` (Step 2 prototype), standard library only, Python 3.11.9, run in about 7 s.
**Superseded:** the prototype and its `civilwork_verification_output/` were removed after the Step 3 implementation reproduced every output field by field (`my_approach/civilwork/step_3/README.md`). The figures below now regenerate with `python my_approach/civilwork/step_3/src/run_civilwork_audit.py` into `my_approach/civilwork/step_3/output/`.
Two consecutive runs gave byte-identical CSV outputs.

## 1. What was checked

| Area | Method | Result |
|---|---|---|
| Contract text | Rendered all 43 PDF pages. Compared 33 pages against the transcription by eye: pp1, 3, 4, 6–14, 17–27, 32–34, 36, 38–43, i.e. every page carrying a rate, factor, date, band, limit, record rule or payment rule. | No difference found. Controlling words confirmed on the scans: 31A "on or after" (p32); A3 "after the date of issue" and "already certified" (p43); 27A "after 27 September 2025" (p32); P19 "within two days of" (p13); Cl 43 "returned unpaid" (p8); Cl 45 "rounded down" (p8). |
| Data integrity | Full scan of 900 applications, 7,746 lines and 2,169 records | 900 / 7,746 / 2,169. Keys are unique, there are no orphans, and every file is referenced. 2,193 lines carry a reference (2,172 distinct). Three reference files are missing: CT-00126, MO-00089 and PS-00039. Twenty references are shared (19 DW, plus PT-00189). |
| Records | Parsed every file; 26 body patterns | Title matches the series in 2,169/2,169. Only DX-00089 lacks a countersignature; every file has a foreman signature. DW "Days on": 5 days (40 records), 6 (38), 7 (36). The words in the record body match the line's item code on all 2,188 lines with a usable record. |
| Pricing | Rebuilt every line with Decimal arithmetic under Clauses 26A, 27, 27A, 28, 29, 29A, Sch 4 Pt 3, 31A, S1, A1, S2, A2 and A3 | **7,703 / 7,746 lines reproduce the billed amount.** 43 residual lines in 37 applications. |
| Ablation | 23 single-rule changes against the same 7,703 baseline | See §2 |
| Quantities, limits, dates | Clauses 6A, 26, 31, 32/P19, 33/33A, 41, 44, 46, 47, 47A, P6, P21 across all applications | See §3 |
| Application level | Totals, retention, net, 31A adjustment, 45A release | See §3 |
| Named tests | 33 assertions covering the review's issues and the boundary cases | **33/33 pass** (prototype run log; checks carried into `my_approach/civilwork/step_3/tests/`) |

## 2. Ablation (one baseline: 7,703)

| Reading tested | Matched | Lost | Gained |
|---|---:|---:|---:|
| without 27A ground freeze | 6,868 | 837 | 2 (PA-00503-03, PA-00768-04) |
| without Sch 4 Pt 3 bands | 6,848 | 859 | 4 (PA-00312-05, -00374-02, -00496-02, -00871-04) |
| bands not reset at Contract Year 2 | 7,435 | 268 | 0 |
| without 26A USD conversion | 7,316 | 387 | 0 |
| without 29A indexation | 7,429 | 274 | 0 |
| without S2/A2 discount | 7,474 | 230 | 1 (PA-00268-03) |
| without rest-day uplift | 7,566 | 137 | 0 |
| night uplift also in Z3/Z4 | 7,620 | 84 | 1 (PA-00668-02) |
| without 31A (reprice pre-issue applications) | 7,615 | 88 | 0 |
| 31A boundary "on or before" the issue day | 7,701 | 2 | 0 |
| freeze from 27 Sep / from 29 Sep | 7,701 / 7,701 | 2 / 2 | 0 |
| band order by application date | 7,631 | 72 | 0 |
| reverse application-number tie-break | 7,695 | 8 | 0 |
| final rounding half-even | 7,587 | 116 | 0 |
| conversion rounding half-up | 7,685 | 18 | 0 |
| without S1 / A1 / S2 rates / A2 monthly | 7,423 / 7,591 / 7,647 / 7,680 | 281 / 112 / 56 / 23 | 1 / 0 / 0 / 0 |
| without zone / ground / night | 2,563 / 6,990 / 7,622 | 5,140 / 713 / 81 | 0 |

The v2 table reproduces exactly. The 7 boundary rows are new: the 31A boundary, freeze 27/29 Sep, the two band orders, and the two rounding modes.

## 3. Findings on the specific issues

| Issue | Result |
|---|---|
| CT "imported stone" | All 51 lines are A.14.010 at the recorded quantity. Classifying by the unit in the record body gives zero mismatches. |
| Amendment No. 3 vs Clause 31A | Conflict confirmed on the scans. Adjustment = **60,508.18** (C.32.010 26,521.21 + A.14.010 33,986.97), or 59,883.83 without PA-00350-02. Decision Q1: carrier **PA-00443**. |
| Missing adjustments | `adjustment` and `retention_released` are 0.00 in 900/900. The 45A release of **4,034,571.73** is due on PA-00678; it would be 4,026,954.02 on a corrected-retention basis. Neither changes `application_total` (Cl 43, 45A). |
| PA-00115-05 | Intermediate rounding: 121.79 vs billed 121.80, −3.00. Expected 185,579.92. |
| Shared DW records | 19 records, none sharing a date; 2 are within one application (PA-00116, PA-00395). E.54.010 has no record and shows the same pattern (17 repeated site-weeks, 4 within one application). Decision Q2: not a duplicate. |
| Work after submission | PA-00125 (all 6 lines), PA-00154-03 and PA-00700-01. Decision Q3: only work executed by submission is valued, so PA-00125 expected = 0. |
| Boundary cases | 27/28 Sep freeze lines match. PA-00006-14 and PA-00380-02 match at 56.80. Daily limits: PA-00845-03 and PA-00243-10. P19: day 0 excluded (PA-00801-05); the nine day-3 cases are allowed. 25 surveyed lines within 2%; PA-00312-04 is above it. 284 hourly lines at record−1; PA-00243-03 is not. |
| Additional readings tested and rejected | P3 (no standing time in Z4 "waiting on access") would reprice 25 lines in 24 applications that reconcile as billed. Reading S20 as barring other work on a standby day would reprice 126 of 143 E.51.010 lines. Counting bands on supported rather than billed quantity changes nothing. |

## 4. Final baseline outcome

**59 of 900 applications flagged (6.6%)** across 27 categories; the full list is in the architecture, Appendix A. Scenario effects (now `my_approach/civilwork/step_3/output/civilwork_scenarios.csv`):

| Alternative | Flagged | Change |
|---|---:|---|
| Q1: carrier PA-00006 / PA-00023 / PA-00380 | 59 | swaps PA-00443 for that application |
| Q1: flag all four candidates | 62 | +3 |
| Q2: repeated week within one application | 61 | +PA-00116, PA-00395 (−3,566.16) |
| Q2: all repeated A.16.010 weeks | 77 | +18 applications (−33,902.20) |
| Q2: A.16.010 and E.54.010 | 94 | +35 applications (−50,163.20) |
| Q3: keep lines executed after submission | 59 | PA-00125 +25,068.53 |
| Q3: Cl 43 → 0 | 59 | PA-00043 −231,425.26 |
| Q3: every procedural defect → 0 | 59 | 6 totals, −1,110,666.24 |
| P19 window days 1–2 / days 0–3 | 58 / 67 | −PA-00801 / +8 applications |

## 5. Limits

- There are no labels. Match rates show which rules the billing applied, not whether any given flag is right. The confidence values are assigned by evidence class and have not been calibrated.
- Ten PDF pages were not compared by eye: pp2, 5, 15, 16, 28–31, 35 and 37 (contents, HSE, dayworks, provisional sums, preliminaries, execution, insurances). None of them feeds a rule the data exercises.
- Rates for items or months that no line uses are verified only by visual comparison, not by data.
- The meaning of `night_work` is taken as given; the files carry no clock times.
- `expected_total_cents` for the 31A, 45A and procedural cases follows the contract text and your Q1–Q3 decisions. How the grader encodes those cases is unknown.
