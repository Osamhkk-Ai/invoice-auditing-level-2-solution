# Verification report — DDS-2025-118 audit design (Step 2)

Scope: directional-drilling contract DDS-2025-118 only. These are analysis checks written to test the design before the architecture was fixed. They are not the production auditor and they produce no `submission.csv`.

## How to reproduce

```
cd my_approach/drilling_services/step_2_audit_system_design/verification
python run_all.py            # Python 3.11.9, standard library only (csv, decimal, datetime, unittest)
python -m unittest test_hand_calcs -v
```

`run_all.py` runs the 12 hand-calculation tests, then checks 01–07 **twice**, and compares SHA-256 digests of the two result sets. Outputs:

- `verification/out/results.json`: every figure below
- `verification/out/flagged_invoices.csv`: the 120 invoices the tested reading flags, with billed and expected totals
- `verification/out/line_exceptions.csv`: the 134 lines whose amount or evidence differs

Final run (2026-09-28): tests **12/12 passed**. Both runs produced digest `1674bc5d827181138f3f82e02cc36b4c2ed30077e062b9b8865ea8366955640c` (**deterministic**). Runtime is about 2.5 minutes for both runs; almost all of it is the 13 alternative repricings in check 04.

| File | Purpose |
|---|---|
| `common.py` | loaders, report parser, contract tables with PDF page citations, half-even rounding |
| `pricing.py` | Clause 18 build-up with one switch per disputed reading (`Reading`) |
| `evidence.py` | what a Daily Drilling Report supports, per well-day and code (`EvidenceOptions`) |
| `check_01_integrity.py` | counts, keys, joins, types, precision, template coverage |
| `check_02_contract_rates.py` | 43 effective-date / boundary cases, Appendix B and F worked examples, rounding |
| `check_03_evidence.py` | report-supported quantity vs billed quantity for every well-day-code; evidence alternatives |
| `check_04_reprice.py` | line repricing, cross-invoice pools, invoice rebuild, Amendment No. 3 adjustment; pricing alternatives |
| `check_05_state.py` | Contract Year volume bands, once-per-well, per-run, duplicates, ordering key, invoice sequencing |
| `check_06_controls.py` | negative controls (unusual but contractual lines must stay unflagged) |
| `check_07_rate_diagnosis.py` | names the mis-application that reproduces each wrong billed rate |
| `test_hand_calcs.py` | 12 hand calculations on real lines and reports |

## 1. Data integrity (check 01)

- `invoices.csv` has **1,906** rows, `invoice_lines.csv` **91,244**, and `records/` **8,151** report files. These equal the README counts.
- `invoice_no` and `line_ref` are unique. `line_ref = invoice_no-NNN` holds throughout, with no gaps in `line_no`. Every invoice has 13–93 lines, and every line's `well_name` equals its invoice's well.
- All money fields have exactly 2 decimals and all quantities are integers. There is no currency column; USD applies (Clause P14, pp.11–12).
- `adjustment` is `0.00` on **all 1,906** invoices.
- `contract_ref` is `DDS-2025-118` on 1,903 invoices, `DSS-2025-118` on 2 (MDS-00672, MDS-00988) and `DDS-2025-181` on 1 (MDS-01799). One contractor name appears throughout.
- `report_ref`: 63 blanks, all on `DS-900` discount lines. Every other ref resolves to exactly one file `DDR_<well>_<yyyymmdd>.txt`, and every report is referenced at least once. Well numbers never collide across field prefixes. The report number inside each file matches its filename.
- 8 lines have a `report_ref` date different from `service_date`: MDS-00128-026, MDS-00164-050, MDS-00541-018, MDS-00895-051, MDS-01352-007, MDS-01619-045, MDS-01798-045, MDS-01860-039.
- There are 214 wells. Rig, field and class never conflict across a well's invoices, and the report rig always equals the invoice rig. Field does not follow the well-name prefix (e.g. NGP-WS wells appear in all four fields).
- Line dates run 2025-01-01..**2027-01-23**; report dates run 2025-01-01..2026-11-27.
- Template: 2,806 rows, of which 1,906 are `MDS-` ids. Each matches exactly one invoice, and no invoice is missing from the template.
- 3 lines have `quantity × unit_rate ≠ amount`: MDS-00332-013, MDS-00406-015, MDS-01044-025.

**Report formats.** One labelled template, `DAILY DRILLING REPORT`, is used by all 8,151 reports: UTF-8 with CRLF line endings, 850–1,280 bytes, and no unparsed tokens.

- Parts present: A+B 7,258; A+B+C 476; A+B+D 363; A+B+E 47; A+B+D+E 4; A+B+C+E 3.
- `In the hole` equals `Tools in run` on every report.
- Status: Operating 7,770; Standby 381.
- Signatures: 5 Company Representatives and 6 lead directional drillers. **3 reports have both signature lines blank** (`____________________`): DDR_NGP-BD-149_20251122, DDR_NGP-BD-218_20251029, DDR_NGP-WS-055_20250503.
- Free text is limited to the field words in `In the hole`, `Tools in run`, `Crew on tour` and `Lost in hole tool`. There are 15 tool words and 5 crew words, all listed in Appendix G (p.36).

## 2. Contract arithmetic (check 02)

- **43/43 boundary cases pass**, with each case taken on both sides of every effective date:
  - S1: 2025-07-01
  - A1: 2026-01-01
  - A3: effective 2026-02-01, and invoice dates 2026-08-16 / 2026-08-17
  - S2: 2026-04-01
  - A2: 2026-07-01
  - Commencement 2025-01-01 and extended Expiry 2026-12-31
  - Index month changes

  Examples: DD-101 on 2026-04-01 is 1,839.84 on a pre-issue invoice (A1 × 0.96) and 1,875.84 after issue (A3 × 0.96). DD-120 on 2026-07-01, 8-1/2", HPHT, after issue: 416.00 → 393.12 → 520.88 → 484.42.
- **Rounding.** Half-even is visible in the data. MW-320 standby 779.65 × 0.5 = 389.825 → **389.82** (half-up would give 389.83). DD-101 1,916.50 × 0.93 = 1,782.345 → 1,782.34 (e.g. MDS-01519-058). Switching every step to half-up changes 878 line amounts and 370 invoice totals (check 04), so the half-even figures are what was billed.
- **Appendix B (p.30)** reproduces only without Part IX. The printed MW-310 rate 2,975.75 = 2,245.85 × 1.325 has no Schedule 2C index; with the June-2025 index it is 3,082.88. The DD-120 quantity 18 is not reduced by Clause 21A. The billed data follows Part IX on both points (next sections). Appendix B's net, VAT and total arithmetic (25,662.26 / 3,849.34 / 29,511.60), its PD-210 split at 3,000 m, and its discount example (−2,496.00) all reproduce.
- **Appendix F (p.34):** 412 h → 16 %, reproduced. Via Schedule 2D, SAR 1,443,750 / 375.00 = 385,000.00 → 323,400.00. The 50 % cap is tested at 1,300 h.

## 3. Report evidence vs billed quantities (check 03)

Baseline reading: Appendix G word map, Clause 21A (one hour less per report day for the hourly items DD-120 and RM-530), PD-210 on Operating days whose crew includes a "performance engineer", and daily limits applied. Under it, **90,950 of 90,994** well-day-code pairs agree exactly and 44 do not. Joining on the `report_ref` date instead of `service_date` gives 90,952 / 42.

| Alternative (one switch) | Day-codes that now disagree | Verdict |
|---|---|---|
| Clause 21A off (charge the hours the report states) | 5,583 (+5,539) | rejected by data |
| LWD words read literally (e.g. "resistivity tool" → LW-410) | 3,007 (+2,963) | rejected; Appendix G governs |
| PD-210 on every 12-1/4"/8-1/2" Operating day | 2,016 (+1,972) | rejected |
| PD-210 only when "bit and reamer" in hole | 1,234 (+1,190) | rejected |
| Sch.8 wording: DD-120 also per back-reaming hour | 471 | rejected |
| Sch.8 wording: HC-630 once per BHA run (not Clause 30 count) | 956 | rejected |
| Daily limits off | +0 | not testable: no limit binds except MW-310 billed 3 (also above record) |

Other findings:

- The Clause 21 minimum of 6 h never engages: the lowest circulating hours on an Operating RSS day is 8. **The interaction of the minimum with Clause 21A is untested.**
- No billed metres fall inside the Clause 25A 1 % tolerance. All 7 metre over-billings exceed it (e.g. DDR_NGP-WS-106_20250126: LW-410 report 125 m, billed 171 m). **Clause 25A is untested by data.**
- "Radioactive source carried: Yes" coincides with "resistivity tool" on all 8,151 reports. This supports Appendix G's pairing of "resistivity tool" with LW-411 (density-neutron, the radioactive tool; Clause T9).
- Part E hours differ from the running sum of daily circulating hours on 27 of 54 losses. Clause 31 prices on hours "as stated on the Lost in Hole Report", and the billed values follow the stated figure.
- Crew counts are constant: DD-101 2, DD-102 1 and MW-301 2 on every report. The Schedule 8 conflict for DD-102 ("per coordinator" vs "tool in the hole") therefore changes nothing.

Baseline exceptions (44 day-codes):

- DD-120 above report: 5
- RM-530 above report: 2
- LW-401 above report: 4 (3 are duplicate lines)
- LW-410 above report: 3
- LW-411 above report: 2
- RM-510 above report: 2
- MW-301 above report: 2
- MW-310 above report: 1
- MW-330 above report: 2
- PD-201 above report: 1
- DD-121 on Operating days: 4
- HC-640 on Standby days: 4
- MB-701 on a day other than the first: 3
- RM-511 without "hole opener": 3
- report days whose line was re-dated elsewhere: 6

## 4. Line repricing and invoice rebuild (check 04)

Fixed order:

1. Term.
2. Invoice period.
3. Report exists and is signed.
4. Schedule 5 part present.
5. Supported quantity, pooled per well-day-code (PD-210 per band interval) and consumed in `(invoice_date, invoice_no, line_no)` order.
6. Rate build-up.
7. Amount.
8. Discount, VAT, total, and the Amendment No. 3 adjustment.

Results:

- 91,181 priced lines (all except `DS-900`). **91,047 match exactly** with no reason code; 134 lines differ.
- Lines that could not be priced although supported: **0**.

| Line reason | Lines |
|---|---|
| rate_differs | 51 |
| report_unsigned (whole day) | 33 |
| qty_above_report | 21 |
| not_supported_by_report | 14 |
| outside_invoice_period | 3 |
| outside_term (dated 2027) | 3 |
| already_billed (duplicate line) | 3 |
| amount ≠ qty × rate | 3 |
| part_D_absent (LW-420) | 2 |
| part_C_absent (DD-130) | 1 |

- **Invoices flagged: 120 (6.30 %)**. Total changed on 111. Flagged with the total unchanged on 9: 6 submission-window defects (MDS-00038, MDS-00199, MDS-00537 late; MDS-00645, MDS-00828, MDS-01258 early) and 3 contract references. **Every invoice whose total changes is flagged.**
- 117 flagged invoices carry exactly one defect. The other 3 (MDS-01619, MDS-01798, MDS-01860) carry `outside_term` and `period_outside_term`, which are one defect seen at line and invoice level.
- Invoice-level defects:
  - DS-900 missing: MDS-00072, MDS-00282, MDS-01049. For MDS-00072, services 1,307,552.40 → discount −42,302.10.
  - `invoice_total ≠ net + VAT`: MDS-00551, MDS-00916, MDS-01317.
  - VAT correct on all 1,906 invoices; net equals the sum of lines on all 1,906.
- **Amendment No. 3 (Clause 36A):** the difference on 3,309 DD-101/DD-120 lines performed on or after 2026-02-01 and invoiced before 2026-08-17 is **+309,965.52 USD**. The first invoice submitted on or after the issue date is **MDS-01625** (dated 2026-08-17). Its billed `adjustment` is 0.00. Expected total: 536,266.10 without VAT on the adjustment, 582,760.92 with it. **Owner decision needed.**
- Sanity check only, not a target: 6.30 % lies in the README's 5–8 % range.

| Pricing alternative (one switch) | Lines changed | Invoice totals changed | Invoices disagreeing with billed |
|---|---|---|---|
| Baseline | — | — | 111 |
| Clause 18 literal: section factor kept on Standby (vs 17B) | 402 | 240 | 330 |
| Class factor on PD-210 (Sch.2 note, vs 17B) | 940 | 248 | 343 |
| No Schedule 2C index (as Appendix B) | 15,635 | 1,836 | 1,838 |
| S2 monthly DD-120 beats A3 from Apr-2026 | 778 | 213 | 302 |
| A3 also applied to invoices submitted before its issue | 3,309 | 512 | 594 |
| Lost-in-hole at Schedule 6 USD, not Schedule 2D SAR | 47 | 47 | 148 |
| Evidence day from `report_ref` instead of `service_date` | 8 | 8 | 107 |
| Clause 21A off (at line level) | 7 | 7 | 108 |
| Round half up instead of half to even | 878 | 370 | 449 |
| Discount folded into standby rounding | 0 | 0 | 111 — no standby × discount tie in data; **untested** |
| No Clause 25A tolerance | 0 | 0 | 111 — no case in window; **untested** |
| PD-210 on every section day (line level) | 0 | 0 | 111 — only adds unbilled supply; see check 03 |

## 5. State across days and invoices (check 05)

- **Schedule 2 Part 2** (PD-210 by "metres already drilled on the well in the Contract Year", p.17). The largest single-well total in a Contract Year is **3,355 m**, so the 40,000 m band never engages. Cumulating across all wells, which is not the printed wording, would reprice 1,289 lines at 96 % and 473 at 92 %. All billed PD-210 rates are at 100 %.
- **Once per well:** 853 well-code pairs have one line each. The 3 exceptions are MB-701 billed again on a later day: MDS-00320-016, MDS-01438-039, MDS-01887-049. All 214 wells ran LWD, so LW-430 is due on every well.
- **Per run:** 654 motor runs → 654 DD-111 lines; 369 source runs → 369 LW-420 lines. Run first/last days agree with the report days on all 1,369 runs.
- **Duplicates:** 3 same-day, same-code groups, all within one invoice (MDS-00476, MDS-00580, MDS-01654). Changing the ordering key to `period_start` changes no keeper.
- **Invoice sequencing:** no gaps. The only overlaps are the 3 invoices whose period was stretched into 2027. Every well's invoices cover all its report days, and every well's report days are contiguous.

## 6. Negative controls (check 06)

Each control group stays unflagged except for lines that carry a separate, identified defect:

- DD-111 on Standby (9 lines, 0 flagged).
- LW-420 on Standby (9, 0).
- PD-210 band-split lines (375, 0).
- HC-601 in 2026 at the last published S1 rate 736.40 (769, 0).
- DD-101/DD-120 on pre-issue invoices at the pre-A3 rate (3,309, 0).
- The two in-period lines with a mis-quoted `report_ref`, MDS-00128-026 and MDS-01352-007 (2, 0).
- DD-121 on Standby (241): 1 flag, the stale rate on MDS-00840-023.
- Standby personnel (1,435): 7 flags, all on unsigned-report days or the stale rate on MDS-00622-014.
- DD-120 at report hours − 1 (4,601): 2 flags, one on an unsigned day and the stale rate on MDS-01739-041.
- Lost in hole (54): 8 flags, all wrong values (section 7).

All 63 billed `DS-900` lines are correct on their billed services.

## 7. What the wrong rates are (check 07)

All 51 `rate_differs` lines are reproduced by one named mis-application:

- Wrong index month: 6, e.g. MDS-00214-011 uses April 102.30 for a March day.
- MW-310 at the unindexed base with another section's or class's factor, or with the standby % omitted: 12.
- Section factor applied on a Standby day: 3.
- Standby % ignored: 3.
- PD-210 at the wrong band (98.70 for a 76.45 interval): 5.
- PD-210 or LW-41x with a class factor it should not carry: 4.
- Discount taken before 2026-04-01: 3 (MW-301 at 1,531.29 in 2025).
- Discount omitted: 3.
- Superseded instrument rate: 5.
- DD-110 at the wrong section factor: 2.
- Lost in hole at Schedule 6 USD with no depreciation: 3.
- Lost in hole converted at the **September 2025** rate (374.80) instead of the month of loss: 5.

The expected amount always comes from the contract build-up, not from these diagnoses.

## 8. Hand-calculation tests (`test_hand_calcs.py`, 12/12)

- MDS-00001-003 section factor.
- MW-320 half-even standby.
- MDS-00214-011 index.
- MDS-01739-041 discount step.
- A3 before and after issue.
- MDS-00639-027 and MDS-00307-006 lost-in-hole values.
- PD-210 split at 1,500 m.
- MDS-00072 discount.
- MDS-00001 VAT.
- Parsing of DDR_NGP-BD-011_20260225 (crew, tools, depths, first-day items).
- DDR_NGP-BD-011_20260308: 16 h recorded → DD-120 15.

## 9. Unresolved and untested

1. **VAT on the Amendment No. 3 adjustment** (MDS-01625: 536,266.10 vs 582,760.92). Clause 36A says "a single adjustment". Clause 39 puts VAT on the net amount, and the CSV keeps `adjustment` outside net. Needs an owner decision.
2. **Which invoice carries it.** Clause 36A says "on or after the date of issue", which gives MDS-01625. A3's own text says "after", which gives three invoices dated 2026-08-18 (MDS-01585, MDS-01631, MDS-01645) and no single "first". Chosen: 36A. A per-well reading would leave most wells' differences with no later invoice.
3. **Unsigned reports** (3 invoices, 33 lines, e.g. MDS-00901 −47,191.22 incl. VAT). Chosen: the day's charges are unevidenced (Clause 15, guideline 2). Alternative: flag the invoice but keep the amount.
4. **Contract-reference typos** (3 invoices). Chosen: flag and keep the contract amount. Alternative: reject the whole invoice.
5. **PD-210 "nominated in the call-off"**: the call-off is not in the data. The performance-engineer proxy fits 2,206/2,206 billed days, but it is an interpretation.
6. **Untested by the data:** Clause 21 minimum × 21A; Clause 25A tolerance; discount rounding position on Standby days. The precedence of Part IX over a Schedule (Clause 2 names only Part VI) is supported by the data on 17B, 17A and 21A but is not stated by the contract.
7. **Mis-quoted report numbers** (MDS-00128-026, MDS-01352-007) are left unflagged because the same-day report supports them and nothing is billed twice. A stricter reading of Clause 19A would query them.
