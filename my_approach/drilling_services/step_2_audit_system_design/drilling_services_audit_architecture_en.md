# Directional Drilling Services Invoice Audit Architecture — DDS-2025-118

**Scope:** Directional drilling contract DDS-2025-118 only. The civil works auditor is separate; no civil rate, rule, rounding choice, or interpretation was imported.

**Nature of this document:** A design based on actual checks. Every figure comes from the scripts in `verification/` and is documented in `verification_report.md`. Run `cd verification && python run_all.py` (Python 3.11.9, standard library only). The result was 12/12 passing tests and two runs with the same digest, `1674bc5d…640c`.

**Citation conventions:** `p.N` refers to page N of the scanned PDF; `[data]` means a CSV or daily report; `[interpretation]` is a choice not stated expressly in the contract; `[untested]` is a rule with no exercising case in the data.

---

## 0. One-page summary

- **The data is structurally consistent** (check 01): 1,906 invoices, 91,244 lines, and 8,151 daily reports, matching the README. Every nonblank `report_ref` resolves to exactly one file, and every `MDS-` ID in the template matches one invoice.
- **The proposed contract reading reprices 91,047 of 91,181 priced lines to the cent.** It covers Part IX (indexation 17A, exclusions 17B, billable hours 21A, riyal conversion 31A, and retroactive adjustment 36A), Amendment No. 3 (A3) taking precedence over Supplement No. 2 (S2) monthly rates, and the Appendix G site-word map.
- Every plausible alternative tested changes hundreds or thousands of currently matching lines; see §6.
- **Result: 120 defective invoices (6.30%).** Their totals change in 111 cases. Nine have timing or contract-reference defects with no amount change. Of the 120, 117 have only one defect. Every invoice whose total changes is flagged.
- **Two owner decisions materially affect amounts** (§7.4): whether A3 adjustment attracts VAT, and how to treat an unsigned report.

---

## 1. The claim under audit

### 1.1 Financial fields in `invoices.csv`

| Field | Contract meaning | Source | Observation |
|---|---|---|---|
| Line `amount` | Quantity × built rate, rounded | Clause 18, p.6 | Three lines have `amount != quantity × unit_rate` |
| `DS-900` | A single negative line for a 4% discount on services above 250,000.00 | Clause 38, p.8; P11, p.11 (per invoice) | All 63 present lines are correct; three invoices qualify but omit it |
| `net_amount` | Sum of line amounts including DS-900 | Clause 36, p.8 | Equals the sum of lines in every invoice |
| `vat_amount` | 15% of `net_amount`, half-even rounded | Clause 39, p.8; p.1 | Correct in every invoice |
| `adjustment` | The single A3 settlement in Clause 36A | pp.35, 42 | `0.00` in every invoice |
| `invoice_total` | `net_amount + vat_amount`, plus `adjustment` where applicable | Clause 40, p.8 | Three invoices do not equal `net + VAT` |

The judged number is **`invoice_total`** (README). Therefore an invoice may be wrong even if its ordinary service lines are correct, for example because DS-900, the final sum, or the adjustment is wrong.

### 1.2 Eventual submission fields, per MDS invoice

| Field | Proposed rule |
|---|---|
| `flagged` | 1 if the invoice has any contractual defect, whether or not it changes the amount |
| `error_category` | One principal category from §5.9; select the largest financial effect when there are several, and preserve the rest in the audit trail |
| `billed_total_cents` | `invoice_total × 100` as an integer, without binary floating point |
| `expected_total_cents` | Rebuilt total under §5.8 × 100; equals billed cents on an unflagged invoice |
| `confidence` | Proposed values in §5.10 |

Timing and contract-reference defects flag an invoice while leaving `expected = billed` [interpretation, §7.3]. Quantity, price, and arithmetic defects flag it and change `expected`. No invoice with a changed amount is unflagged in the current results.

---

## 2. Data map: invoice → line → daily report → contract item

```text
invoices.csv (1,906)                    invoice_no (unique)
   │ 1..N [13..93 lines per invoice]
   ▼
invoice_lines.csv (91,244)              line_ref = invoice_no-NNN (unique, no gaps)
   │ N..1 by (well_name, service_date)  ← chosen evidence key
   │      and report_ref = DDR-<well number>-<yyyymmdd> ← validation only
   ▼
records/DDR_<well>_<yyyymmdd>.txt (8,151) one report per (well, day)
   │ 1..N through Appendix G (site words → service codes)
   ▼
Schedule 1 / Schedule 2 / Schedule 2D item (39 used codes + DS-900)
```

### 2.1 Keys

- **`well_name`:** Consistent between invoice and its lines. Each well has one rig, field, and class across its invoices (214 wells); report rig always matches invoice rig. The well-name prefix does not identify the field: `NGP-WS`, for example, appears in all four fields. Take field and class from the invoice.
- **Report number:** Uses only three digits of the well name. These do not collide between prefixes in this dataset, but always key by full `(well_name, date)`.
- **Evidence key:** `(well_name, service_date)`, not `report_ref` [interpretation]. Clause 34 (p.8) makes date part of the line, and Clause 32 ties it to the invoice period. Eight lines have a date different from their `report_ref` date (§6.4). Keying by `report_ref` instead changes eight lines in eight invoices.

### 2.2 Cardinality

- An invoice covers one well and consecutive days (Clause 32). Actual lengths are 1–6 days except three periods extended into 2027 (81, 113, and 166 days).
- One daily report exists for each `(well, day)` (Schedule 5, p.24). Well days are continuous and fully covered by invoices without gaps or overlap, apart from the three extended invoices.
- A report supports several lines; normally a code occurs once per day. PD-210 may repeat by depth band (Clause 29). Three repeated groups occur, all within one invoice.
- An invoice has zero or one `DS-900` line.

### 2.3 Missing or conflicting evidence

| Condition | Treatment |
|---|---|
| No report for `(well, service_date)` | Line unsupported; payable amount 0 (guideline 2) |
| Report exists but neither party signed | All lines that day unsupported; payable amount 0 [interpretation; owner question] |
| Required Schedule 5 part B/C/D/E absent | The affected line is not payable (Clause 37, p.8) |
| Line section or status conflicts with report | Use the report (Clauses 19 and R7); no such conflict occurs |
| `report_ref` names another day but the correct day's report supports the line | Record a warning, without a flag or amount effect [interpretation, §7.3] |
| Billed quantity exceeds report | Pay the supported quantity (guideline 5), allowing the 1% metres tolerance (25A) |

---

## 3. Contract rulebook

Each rule records its source, inputs, decision or formula, codes and dates, ambiguity, and test status.

**Precedence where texts conflict:** Clause 2 (p.3) makes a Schedule prevail over a Part, and Part VI prevail over Parts I–V. It does not name Part IX because the contents page is incomplete. We treat Part IX as special conditions prevailing over earlier terms [interpretation supported by the data for 17A, 17B, and 21A]. Read changes in issue order: the later-issued instrument governs from its effective date (variations table p.37; guideline 7).

### 3.1 Eligibility and dates

| ID | Rule | Source | Decision | Test |
|---|---|---|---|---|
| E1 | DDS-2025-118 and contractor Meridian | p.1 | `contract_ref == "DDS-2025-118"` | Three wrong invoices: MDS-00672 and MDS-00988 (`DSS-…`), MDS-01799 (`…-181`) |
| E2 | Term 2025-01-01 through 2026-12-31 after two extensions | p.1; A1 1.1 p.39; A2 2.1 p.41 | `TERM_START ≤ service_date ≤ TERM_END`; work after 2026-12-31 not payable | Three 2027 lines in MDS-01619, MDS-01798, MDS-01860 |
| E3 | Work date, not invoice date, selects a rate | p.37 | Every rate lookup uses `service_date` | Intentional exception: 36A also uses `invoice_date` (§3.7) |
| E4 | One well, consecutive days, every line within period | Clause 32 p.8 | `period_start ≤ service_date ≤ period_end` | Three outside-period lines: MDS-00164-050, MDS-00541-018, MDS-00895-051 |
| E5 | Submission from period end through day 30 | Clause 33 p.8 | `0 ≤ invoice_date − period_end ≤ 30` | Three early (MDS-00645, MDS-00828, MDS-01258), three late (46, 51, 55 days); rest 2–30 days |
| E6 | Contract Year 1 is 2025; Year 2 begins 2026-01-01; extension does not start a new year | 3A p.35 | Used only for Schedule 2 Part 2 bands | See L4 |
| E7 | Rig-move days are not well days | P4 p.11 | No `rig move` status; well days continuous | No data effect |

### 3.2 Reports and signatures

| ID | Rule | Source | Decision | Test |
|---|---|---|---|---|
| R1 | Daily report for each well day, signed by company representative and lead directional driller | Clause 15 p.5 | Both signature fields nonblank (not `_____`) | Three unsigned reports: BD-149 on 2025-11-22, BD-218 on 2025-10-29, WS-055 on 2025-05-03; 33 lines in MDS-00901, MDS-00842, MDS-00340 |
| R2 | Runs, surveys, radioactive sources, and loss are in the daily report, not separate documents | Schedule 5 p.24, replacing Clause 16 | Part B for DD-111, LW-410/411/412/413, RM-510; C for DD-130; D for LW-420; E for LH-711..714 | Three lines lack required part: MDS-00876-062 and MDS-01393-036 (LW-420, no D); MDS-00954-021 (DD-130, no C) |
| R3 | Company representative's day status is final | R7 p.14 | Use report status | No line/report conflict |
| R4 | Quote the day's report number on each line | 19A p.35 | Check it, but do not use it as evidence key | Eight mismatched lines (§6.4) |

### 3.3 Service identity and units

| ID | Rule | Source | Decision | Test |
|---|---|---|---|---|
| S1 | State item in the unit specified by Schedule 1 | Clause 35 p.8 | `(service_code, description, unit)` match Schedule 1 | All 39 combinations match |
| S2 | Map site words to codes **exactly as printed** in Appendix G, including counterintuitive pairs | Appendix G p.36 | `gamma tool`→LW-410; `resistivity tool`→LW-411; `density-neutron`→LW-412; `float sub`→HC-640; `survey package`→MW-320, etc. | Literal-seeming alternative `resistivity tool`→LW-410 adds 2,963 unmatched day-codes. Independently, `Radioactive source carried: Yes` always accompanies `resistivity tool` in the 8,151 reports; LW-411 is the radioactive tool (T9 p.9) |
| S3 | One word can represent two codes: `mud motor`→DD-110 or LH-711, likewise `rotary steerable`, `MWD collar`, `gamma tool` | Appendix G | `In the hole` means rental; `Lost in hole tool` in Part E means LH | No residual ambiguity in the data |
| S4 | Do not choose a code because its price matches the invoice | Guideline 6 | Mapping comes from report only, never billed price | Enforced in `evidence.py` |

### 3.4 Quantities: time, depth, and counts

| ID | Rule | Source | Formula or decision | Test |
|---|---|---|---|---|
| Q1 | Personnel charged per person-day from report count | Clause 22; Schedule 4; P13 | `qty = N` from `Crew on tour` | Matches all days. DD-101=2, DD-102=1, MW-301=2 in every report |
| Q2 | Daily rental only if report records tool in hole | Clause 28; P6 | `qty = 1` if tool word is in `In the hole` | Three RM-511 lines without `hole opener`; four HC-640 lines on Standby; MW-310/MW-330 duplicates |
| Q3 | DD-120 uses circulating hours on Operating days, minimum six; **first hour of each period in hole is not billed** | Clause 21 p.6; 21A p.35; P10 | `qty = max(circ − 1, 6)` [interaction of 21A with minimum untested] | Removing 21A changes another 5,539 day-codes. `Each period` is read as each report day [interpretation supported by 4,601 cases]. Lowest Operating hours are eight, so the minimum never binds |
| Q4 | DD-121 on Standby day in place of DD-120 | Clause 21; Schedule 3 Part 4 | `qty = 1` if `rotary steerable` present and status Standby | Four DD-121 lines on Operating days |
| Q5 | Count from report on Operating days only | Clause 30 | DD-130=gyro surveys; LW-413=pressure points; HC-610=wiper trips; HC-630=clean-out runs; RM-530=back-reaming hours − 1 (21A) | Two RM-530 lines claim full hours. Schedule 8's `HC-630 per run` wording makes 956 days fail, so rejected |
| Q6 | Metres=`Depth end − Depth start` on Operating day with tool in hole | Clauses 24, 25; R3 | LW-41x per Appendix G; RM-510 needs `hole opener` | Seven excesses, all above 1% (WS-106 on 2025-01-26: report 125 m, billed 171 m) |
| Q7 | PD-210 metres only in sections `nominated for performance drilling in the call-off`, split at 1,500, 3,000, 4,500 m; boundary belongs to shallower band | Clause 23 p.6; Appendix A p.29; Schedule 2 p.17 | Call-off absent. **Chosen proxy [interpretation]:** Operating day in 12-1/4" or 8-1/2" section with a `performance engineer` (PD-201, placed in Schedule 4's performance sections) | Fits 2,206/2,206 billed days. `Every 12-1/4"/8-1/2" day` conflicts on 1,972 days; `bit and reamer` conflicts on 1,190 |
| Q8 | 1% metres tolerance | 25A p.35 | If `billed ≤ supported × 1.01`, pay billed; otherwise pay report-supported amount | [untested]: no case in window |
| Q9 | Daily limits | Clause 22; Schedule 3 Part 5 | `qty ≤ limit` | No binding limit except MW-310 billed 3 (HA-118 on 2026-04-26), also above the report |

### 3.5 Pricing and amendments

Clause 18 (p.6) sets build-up order; each step is rounded to a cent using half-even (Clause 17). Add 17A/17B (p.35), the Supplement No. 2 (S2) discount, and Amendment No. 2 (A2) (pp.40–41):

```text
r0 = base rate effective on service_date                         (Table 3.5-A)
r1 = round(r0 × RSI[service month] / 100.00)                     if code in Schedule 2C (MW-310, HC-620)
r2 = round(r1 × SECTION_FACTOR[report section])                  if section-rated and Operating (17B)
r3 = round(r2 × CLASS_FACTOR[well class])                        if class-rated and not PD-210 (17B)
r4 = round(r3 × STANDBY_PCT[code])                               if Standby
r5 = round(r4 × (1 − d))                                         if code in {DD-101, MW-301, LW-401, DD-120, MB-701}
     d = 0.04 from 2026-04-01, then 0.07 from 2026-07-01 (replaces 0.04; does not add to it)
amount = round(qty × r5)
```

- **Section-rated:** DD-110, DD-120, PD-220, MW-310, RM-510, RM-511 (p.20).
- **Class-rated:** DD-120, MW-310, MW-320, LW-410..413 (p.20). PD-210 is excluded by 17B despite its appearance in the Schedule.
- **Section factors:** 26"=1.315; 17-1/2"=1.145; 12-1/4"=1.00; 8-1/2"=0.945; 6"=0.885.
- **Class factors:** Standard=1.00; Extended Reach=1.175; HPHT=1.325.
- **Standby:** Four engineers DD-101, PD-201, MW-301, LW-401 at 80%; DD-102, DD-111, MW-330, LW-420 at 100%; other rentals at 50%. DD-120, DD-130, PD-210, LW-410..413, RM-510, RM-530, HC-610, HC-630, HC-640 are not payable. Once-per-well and lost-in-hole charges remain at 100% (pp.20–21).

**Table 3.5-A — dated rates** (all 43 boundary cases passed):

| Code | Service-date period or condition | Base rate | Source |
|---|---|---|---|
| DD-101 | Through 2025-12-31 | 1,847.35 | Schedule 1 p.15 |
| | 2026-01-01 to 2026-01-31 | 1,916.50 | A1 p.39 |
| | From 2026-02-01, invoice submitted **before** 2026-08-17 | 1,916.50 | 36A p.35 |
| | From 2026-02-01, invoice submitted **on or after** 2026-08-17 | 1,954.00 | A3 p.42 |
| DD-120 | Through 2025-06-30 | 384.15 | Schedule 1 |
| | 2025-07-01 to 2026-01-31 | 398.50 | S1 p.38 |
| | From 2026-02-01, invoice before A3 issue: Feb–Mar 398.50, then S2 monthly April–Dec (406.00, 411.50, 411.50, 423.00, 429.50, 434.00, 434.00, 441.00, 447.50) | — | 36A; S2 2.1 p.40 |
| | From 2026-02-01, invoice on/after A3 issue | 416.00 all months | A3 (later issue prevails) |
| DD-121 | Through 2025-06-30, then from 2025-07-01 | 2,893.65, then 2,984.00 | Schedule 1; S1 |
| HC-601 | Through June 2025; monthly July–Dec 2025; last published rate continues | 689.35 → 701.50/714.00/722.60/719.80/731.00/736.40 → 736.40 | S1 1.2 p.38 |
| MW-301 | Through 2025; from 2026-01; from 2026-07 | 1,646.55 → 1,708.00 → 1,763.00 | A1; A2 p.41 |
| LW-401 | Through 2025; from 2026-01 | 1,898.45 → 1,969.00 | A1 |
| MB-701 | Before 2026-07; from 2026-07 | 18,497.50 → 19,237.00 | A2 |
| MW-310, HC-620 | Each month | base × RSI(month)/100 | 17A; Schedule 2C p.18 |
| PD-210 | Depth band | 42.35 / 58.15 / 76.45 / 98.70; no class factor | Schedule 2; 17B |
| LH-711..714 | Loss month | `round(SAR × 100 / halalas[month])`, then rounded `× (100 − min(⌊h/25⌋, 50))/100` | 31; 31A; Schedule 2D p.19; Part E hours |

**Hand-calculated real lines** (`test_hand_calcs.py`):

- **MDS-00001-003** (DD-110, 26"): 1,417.75 × 1.315 = 1,864.34125 → **1,864.34**, correct.
- **MDS-01739-041** (DD-120, 8-1/2", 2026-09-15, post-issue invoice): 416.00 × 0.945 = 393.12, then × 0.93 = 365.6016 → **365.60**. Billed 376.58, the S1 rate without discount: wrong.
- **MW-320 on Standby:** 779.65 × 0.5 = 389.825 → **389.82** half-even; half-up gives 389.83.
- **MDS-00639-027** (LH-713, 2025-08-20, 189 hours): 1,443,750 ÷ 3.7500 = 385,000.00; 7% depreciation → **358,050.00**. Billed 385,000.00: wrong.

### 3.6 Limits and exceptions

| ID | Rule | Source | Decision | Test |
|---|---|---|---|---|
| L1 | Once per well: MB-701 and DD-140 first day; MB-702 and LW-430 last day (LW-430 only with LWD) | Clause 27; Schedule 3 Part 6 | First/last day from the well reports | Three MB-701 repeats on a later day: MDS-00320-016, MDS-01438-039, MDS-01887-049. All 214 wells ran LWD |
| L2 | Once per run: DD-111 on last day of run with `mud motor`; LW-420 on first day of a run carrying radioactive source | Clause 26 p.7 | Part B fields | 654=654 and 369=369 |
| L3 | No duplicate for same well, day, code, except PD-210 bands | Clause 29 | Consumed inventory per `(well, day, code[, band])` | Three repeats within same invoice: MDS-00476, MDS-00580, MDS-01654 |
| L4 | PD-210 volume rebate based on metres drilled **on the well** in the Contract Year | Schedule 2 Part 2 p.17 | Per `(well, Contract Year)` | Highest cumulative metres 3,355; 40,000 band never activates. Pooling all wells, contrary to printed text, reprices 1,762 lines; all bills use 100%. Scan p.17 checked |
| L5 | Daily limit | Schedule 3 Part 5 | See Q9 | — |

### 3.7 Retroactive settlement

**Chosen rule.** A3 was issued 2026-08-17 with effect from 2026-02-01 (pp.37, 42). Clause 36A (p.35) says an invoice submitted before issue was correct at its then-current rate. The **difference on previously invoiced services** is one adjustment on the **first invoice submitted on or after issue**, nowhere else.

**Inputs:** DD-101 and DD-120 lines with service date from 2026-02-01 whose invoices were submitted before 2026-08-17: 3,309 lines across 68 wells.

```text
adjustment = Σ [round(qty × post-issue rate) − round(qty × pre-issue rate)]
```

**Result:** `+309,965.52 USD`, on **MDS-01625** dated 2026-08-17 (the only invoice that day). Billed `adjustment` is `0.00`, an omitted adjustment. Some DD-120 differences in July and August are negative because monthly S2 rates 423.00 and 429.50 exceed A3's 416.00.

**Ambiguities and choices:**

1. **VAT on adjustment:** Expected total is 536,266.10 without adjustment VAT or 582,760.92 if adjustment enters `net`. The data puts `adjustment` outside `net`. **Owner question.**
2. **`After` versus `on or after`:** A3 says `after the date of issue`, yielding three invoices dated 2026-08-18 with no unique first. Clause 36A says `on or after`; chosen because A3 refers to 36A.
3. **One contract adjustment or one per well:** Per-well leaves most wells' differences without a later invoice; rejected.
4. **DS-900 on repricing:** Did not recalculate DS-900 on old invoices; text refers to the `difference on services` [interpretation].

Applying A3 to pre-issue invoices would change 3,309 lines and 512 invoices that now match; rejected. Giving S2 monthly rates priority over A3 from April would change 778 lines and 213 invoices; rejected.

### 3.8 VAT and invoice arithmetic

```text
S        = Σ amounts(lines other than DS-900)                    (Clause 36)
DS-900   = −round((S − 250,000.00) × 0.04) if S > 250,000.00      (Clause 38; P11)
net      = S + DS-900
VAT      = round(net × 0.15)                                     (Clause 39)
total    = net + VAT + adjustment                                (Clauses 40, 36A)
```

Appendix B's example (p.30) reproduces 25,662.26 / 3,849.34 / 29,511.60, and a 312,400.00 service amount yields −2,496.00 discount. **MDS-00072:** S=1,307,552.40, required discount −42,302.10, but no DS-900 line; expected total is 48,647.42 lower, including discount VAT.

**Appendix B caveat:** Its illustrative MW-310 rate (2,975.75) has no index, and its DD-120 quantity 18 does not deduct the 21A hour. Treat the example as illustrative and predating Part IX, not controlling. Actual bills follow Part IX for 15,635 MW-310/HC-620 lines and 4,601 DD-120 lines.

---

## 4. Evidence matrix: report → item

### 4.1 Actual report grammar

All 8,151 reports share one `DAILY DRILLING REPORT` template with named fields, UTF-8, CRLF line endings, and size 850–1,280 bytes.

| Part | Occurrences | Fields |
|---|---:|---|
| Header | 8,151 | `Report`, `Contract`, `Well`, `Rig`, `Date` |
| A — Operations summary | 8,151 | `Hole section`, `Status`, `Depth start/end (m MD)`, `Circulating hours`, `BHA run`, `In the hole`, `Crew on tour`, `Gyro surveys`, `Pressure points`, `Wiper trips`, `Back-reaming hours`, `Clean-out runs` |
| B — Run log | 8,151 | `Run`, `Run first day`, `Run last day`, `Tools in run`, `Run circulating hours`, `Metres logged`, `Metres reamed`, `Radioactive source carried` |
| C — Gyro survey | 479 | `Gyro surveys taken`, `Surveyed section` |
| D — Radioactive source | 367 | `Source run`, `Sources handled`, `Source handling certified` |
| E — Lost in hole | 54 | `Lost in hole run`, `Lost in hole tool`, `Circulating hours accumulated on the well` |
| Signatures | 8,151 (three blank) | `Signed (Company Representative)`, `Signed (lead directional driller)` |

Numbers, dates, status, and section can be parsed directly. Interpretation is needed for tool and crew words (Appendix G), PD-210 nomination (performance-engineer proxy), and the link between Part C and Part A survey count. Those match except WS-009 on 2025-12-11: Part A says one survey and Part C is missing. Part E hours differ from the sum of daily circulating hours in 27/54 cases; use the stated report value because Clause 31 says `as stated`.

### 4.2 Service-family matrix

| Family | Codes | Report evidence | Quantity | Status | Day/run | Required signatures/part | Observed exceptions |
|---|---|---|---|---|---|---|---|
| Personnel | DD-101 `directional hands`; DD-102 `night man`; MW-301 `MWD engineers`; LW-401 `logging engineers`; PD-201 `performance engineer` | `Crew on tour: N <word>` | N, subject to Part 5 limits | Operating 100%; Standby 80%, DD-102 100% | Same day | A and both signatures | Duplicates MDS-00476-051, MDS-00580-046, MDS-01654-078; above crew count MDS-01265-028 (PD-201=2), MDS-01751-010 (MW-301=3), LW-401=2 in MDS-01373 and MDS-01646 |
| Daily rental | DD-110 `mud motor`; MW-310 `MWD collar`; MW-320 `survey package`; MW-330 `real-time link`; HC-601 `circulating sub`; HC-620 `drilling jars`; HC-640 `float sub`; PD-220 `bit and reamer`; PD-230 `hydraulics package`; RM-511 `hole opener`; RM-520 `stabiliser string` | `In the hole` | 1 | Standby 50% or 100%; HC-640 not payable | Day | A | RM-511 without `hole opener` (3); HC-640 on Standby (4); MW-310 billed 3 |
| Rotary steerable | DD-120/DD-121 `rotary steerable` | `Circulating hours` | `max(h−1, 6)`; DD-121=1 | DD-120 Operating only; DD-121 Standby only | Day | A | Five days above report; four DD-121 lines on Operating days |
| Counts | DD-130, LW-413, HC-610, HC-630, RM-530 | `Gyro surveys`, `Pressure points`, `Wiper trips`, `Clean-out runs`, `Back-reaming hours` | Count, except RM-530 hours − 1 | Operating only | Day | DD-130 needs C; LW-413 needs B | One DD-130 without C; two RM-530 without hour deduction |
| Metres | LW-410 `gamma tool`; LW-411 `resistivity tool`; LW-412 `density-neutron`; RM-510 with `hole opener` | `Depth end − Depth start` | Metres with 1% tolerance | Operating only | Day | B | Seven excesses |
| Performance drilling | PD-210 | Depths, `performance engineer`, section | Metres by depth band | Operating only | One line per band per day | A | Five wrongly use 98.70 band; two use class factor |
| Run | DD-111 (`mud motor` in `Tools in run`); LW-420 (`Radioactive source carried: Yes`) | `Run first/last day` | 1 | 100% any status | DD-111 last day; LW-420 first day | B; LW-420 also D | Two LW-420 lines without D |
| Well | MB-701/DD-140 first day; MB-702/LW-430 last day | First/last report for well | 1 | Full | — | A | Three repeated MB-701 lines |
| Lost tool | LH-711 `mud motor`; LH-712 `rotary steerable`; LH-713 `MWD collar`; LH-714 `gamma tool` | Part E | 1 | Full | Loss day | E | Eight wrong values: three Schedule 6 amounts without depreciation; five use September 2025 exchange rate |

---

## 5. Fixed-order processing architecture

```text
[0] Ingest → [1] Validate inputs → [2] Resolve contract version → [3] Link/classify evidence
   → [4] Supported quantity → [5] Price line → [6] Cross-invoice rules
   → [7] Calculate invoice → [8] Flag, category, expected amount, confidence, audit trail
```

### 5.1 [1] Validate inputs (fail on violation)

- Counts: 1,906 / 91,244 / 8,151; unique `invoice_no` and `line_ref`; every line belongs to an invoice.
- Read two-decimal money text into `Decimal`; never use `float`. Quantities are integers.
- Every nonblank `report_ref` resolves. Blank is allowed only for `DS-900`.
- Parse every report without an unknown word; stop rather than guess words outside Appendix G.
- Submission template has 1,906 MDS IDs, one per invoice.

### 5.2 [2] Resolve contract version

Code tables, each constant with a page citation (`common.py`): Schedules 1, 2, 2C (index), 2D (riyal/exchange rate), Schedule 3 Parts 1–7, and five modifying instruments with issue and effective dates. `resolve_rate(code, service_date, invoice_date)` applies later issue order from effective date, the 36A A3 exception for invoices before 2026-08-17, and monthly rates with the last published rate continuing.

### 5.3 [3] Link and classify evidence

For each line, **in this priority order, first applicable result wins**: `outside_term`, `outside_invoice_period`, `no_report_for_day`, `report_unsigned`, `part_X_absent`. Otherwise it is supported and goes to [4]. Record `report_ref_mismatch` as a warning with no amount effect.

### 5.4 [4] Supported quantity

`supported(report) → {code: qty}` per §4.2; calculate PD-210 band intervals `(from, to)`. Store supported inventory by `(well, date, code[, from, to])`.

### 5.5 [5] Price line

- Process in `(invoice_date, invoice_no, line_no)` order.
- Consume inventory: `qty_pay = min(billed_qty, remaining)`, subject to 25A metre tolerance. Exhausted inventory means `already_billed`; none in the first place means `not_supported_by_report`.
- `rate = build_rate(...)` under §3.5 using **report section and status** and invoice well class.
- `expected_amount = round(qty_pay × rate)`.
- Independently test billed `amount == round(qty × unit_rate)`.

### 5.6 [6] Cross-invoice state

| State | Key | Purpose |
|---|---|---|
| Supported-quantity inventory | `(well, date, code[, interval])` | Clause 29 and guideline 10 prevent double billing within/across invoices. Earlier `(invoice_date, invoice_no, line_no)` keeps the claim [interpretation; changing key to `period_start` changes no case] |
| Well first/last day and wells that ran LWD | `well` | Clause 27; all reports for a well must be read before judging MB-702/LW-430 |
| Runs ledger | `(well, run)` | Clause 26 |
| A3 difference ledger | Contract-wide | Clause 36A; accumulate from pre-issue invoices and place on first invoice on/after issue |
| PD-210 metres per well and Contract Year | `(well, contract_year)` | Schedule 2 Part 2; tracked though no threshold binds in these data |

### 5.7 [7] Invoice calculation

Rebuild from expected line amounts under §3.8. Independently check billed DS-900 against billed services, billed `net` against summed lines, VAT, and `total = net + VAT + adjustment`. Check submission timing, contract reference, and service beyond term.

### 5.8 [8] Outputs

For each invoice: `flagged`, `error_category`, integer `expected_total_cents`, `billed_total_cents`, `confidence`. An audit trail for each bad line records `line_ref`, billed/expected quantity, rate, amount, reason, rate-build trace, and contract clause/page. `verification/out/line_exceptions.csv` is an example.

### 5.9 Proposed error-category vocabulary

Last column counts invoices in the verification results. Categories can overlap at invoice level.

| Category | Included reasons | Invoices |
|---|---|---:|
| `RATE_WRONG` | `rate_differs`: index, section, class, standby, discount, old instrument, PD-210 band, lost-tool value | 51 |
| `QTY_ABOVE_RECORD` | `qty_above_report` | 21 |
| `CHARGE_NOT_IN_RECORD` | `not_supported_by_report` | 14 |
| `DUPLICATE_CHARGE` | `already_billed` | 3 |
| `RECORD_UNSIGNED` | `report_unsigned` | 3 |
| `RECORD_PART_MISSING` | `part_C_absent`, `part_D_absent` | 3 |
| `OUTSIDE_PERIOD` | `outside_invoice_period` | 3 |
| `OUTSIDE_TERM` | `outside_term`, `period_outside_term` | 3 |
| `LINE_ARITHMETIC` | `amount_ne_qty_x_rate` | 3 |
| `DISCOUNT_MISSING` | `discount_DS900_wrong` | 3 |
| `TOTAL_ARITHMETIC` | `total_ne_net_plus_vat` | 3 |
| `RETRO_ADJUSTMENT_MISSING` | `a3_adjustment_missing` | 1 |
| `SUBMISSION_WINDOW` | `submitted_before_period_end`, `submitted_over_30_days` | 6 |
| `CONTRACT_REFERENCE` | `contract_ref_wrong` | 3 |

### 5.10 Proposed confidence

These are proposed, uncalibrated values; there are no labelled answers for calibration.

| Condition | Confidence |
|---|---:|
| Deterministic arithmetic (`LINE_ARITHMETIC`, `DISCOUNT_MISSING`, `TOTAL_ARITHMETIC`) | 0.95 |
| Wrong rate reproduced by a named mistake (check 07), excess quantity, no evidence, duplicate, or required part absent | 0.90 |
| Outside period/term; lost tool converted at another month's rate | 0.85 |
| Submission window or contract reference | 0.80 for flag; amount remains billed |
| Unsigned report or A3 settlement | 0.70 because amount depends on owner choice |
| Ordinary unflagged | 0.90 |
| Unflagged with an untested rule or `report_ref_mismatch` (MDS-00128, MDS-01352) | 0.75 |

---

## 6. Numerical results from verification scripts

Source: `verification_report.md` and `verification/out/results.json`.

### 6.1 Baseline

- **91,047/91,181 priced lines** match to the cent without a defect; 134 bad lines; zero unpriceable lines that have evidence.
- **120 invoices flagged (6.30%)**; totals change for 111.
- Net difference between billed and expected: +126,605.09 USD after including the negative A3 settlement difference of −309,965.52.
- The README's 5–8% range was used only as a final plausibility check, never to select a rule.

### 6.2 Tested alternatives

| Alternative | Changed lines/day-codes | Invoices with changed totals | Assessment |
|---|---:|---:|---|
| Keep section factor on Standby (literal Clause 18) | 402 | 240 | Rejected; 17B governs |
| Class factor on PD-210 | 940 | 248 | Rejected; 17B governs |
| No 2C index (as in Appendix B) | 15,635 | 1,836 | Rejected |
| S2 monthly DD-120 rates precede A3 | 778 | 213 | Rejected |
| Apply A3 to pre-issue invoices | 3,309 | 512 | Rejected; 36A governs |
| Lost-tool value as USD directly from Schedule 6 | 47 | 47 | Rejected; 31A and 2D govern |
| Remove day-level 21A | 5,539 day-codes | — | Rejected |
| Read LWD words literally | 2,964 | 881 | Rejected; Appendix G governs |
| PD-210 every 12-1/4" or 8-1/2" day / only with `bit and reamer` | 1,972 / 1,190 day-codes | — | Both rejected |
| Schedule 8: DD-120 includes back-reaming / HC-630 per run | 471 / 956 day-codes | — | Both rejected |
| Key by `report_ref` date | 8 | 8 | Lower-impact alternative (§7.3) |
| Half-up instead of half-even | 878 | 370 | Rejected; Clause 17 governs |
| Combine discount with standby step; remove 25A tolerance; remove daily limits | 0 | 0 | **Untested**: no affected case |

### 6.3 Real examples

**Correct:** MDS-00001-003; all 3,309 pre-A3-issue DD-101/DD-120 lines; 375 PD-210 lines split at band boundaries; nine DD-111 and nine LW-420 lines on Standby days.

| Incorrect line | Billed | Expected | Reason |
|---|---:|---:|---|
| MDS-00214-011 (MW-310) | 2,171.14 | 2,154.17 | April index used for March work |
| MDS-00062-021 (LW-410) | 171 m | 125 m | Exceeds report |
| MDS-00320-016 (MB-701) | — | — | Repeated on later day; invoice excess 21,272.12 |
| MDS-00121-043 (MW-301) | 1,531.29 | 1,646.55 | 7% discount applied in 2025 before effective date |
| MDS-00307-006 (LH-712) | 1,225,653.68 | 1,225,326.75 | September 2025 exchange rate instead of April 2025 |

**Invoice examples:** MDS-00072 omits DS-900; MDS-00551 total differs from `net + VAT`; MDS-01625 omits A3 adjustment; MDS-00038 submitted 55 days late; MDS-01799 quotes `DDS-2025-181`.

### 6.4 Unresolved

- MDS-00128-026 and MDS-01352-007 quote the previous day's report, but the correct day's report supports them and they were not billed twice; left unflagged.
- Ordering of 21A and the six-hour minimum; 25A tolerance; rounding position of the discount on Standby days; VAT on A3; PD-210 call-off absent from data.

---

## 7. Risks and decisions

### 7.1 Transcription and table risks

- Independent validation found zero errors across 42 pages.
- Scan pages 6, 17, 35, 37, and 42 were also read directly because they contain numbers or words not testable from the data: six-hour minimum; 40,000/120,000 m bands; 36A's `on or after`; instrument dates; A3's `after`.
- Truncated descriptions on pp.38, 39, 42 (`circula`, `24-hour cov`, etc.) were not completed; codes and prices are used.
- The crowded `MW-30lMWD` cell on pp.39 and 41 was read as MW-301; 8,146 matching lines support it.

### 7.2 Conflicting or retroactive instruments

| Topic | Contract text | Data | Choice |
|---|---|---|---|
| DD-120 from April 2026: S2 monthly or A3 | `in the order issued… the later governs from its effective date` (p.37 and instruments) | All post-issue invoices use 416.00 | A3 governs |
| A3 before issue | 36A | 3,309 lines at old rate | Old rate plus settlement on MDS-01625 |
| Class factor on PD-210 | Schedules 2 and 3 Part 2 say yes; 17B says no | Follows 17B | 17B, although Clause 2 does not name Part IX |
| Section factor on Standby | Clause 18 applies it; 17B excludes it | Follows 17B | 17B |
| Appendix B | No index or 21A | Data follows 17A and 21A | Illustrative only |
| Schedule 8 versus Clauses 21/30 (DD-120 with back-reaming; HC-630 per run; DD-102 `tool in hole`) | Schedule 8 internally conflicts | Principal clauses govern | Clauses 21, 30, 22 |

### 7.3 Misleading wording, status, depth, and evidence

- **Appendix G pairs words contrary to their apparent meaning:** `resistivity tool` maps to LW-411 (density-neutron). Use printed map, supported by the radioactive-source field accompanying the word in all reports.
- **`Each period in the hole` in 21A** is interpreted as each report day; 4,601 matching cases support it.
- **Depth:** No metres on Standby days. On 943 Operating days with no metres, no metre line is charged; these are exactly the 943 days with wiper trips.
- **Lines dated outside period or after term:** Price and judge the stated line date (Clauses 32, 34). Trusting `report_ref` instead leaves six lines payable.
- **Wrong contract reference and submission window:** Flag as procedural defects but retain contractual amount. Rejecting the whole invoice instead would zero three invoice totals.

### 7.4 Owner questions

Only these two materially change amounts and are not settled by text or data:

1. **Does A3 adjustment carry VAT?** Default no, since `adjustment` is outside `net` in the data. Expected MDS-01625 total 536,266.10; alternative 582,760.92.
2. **Does an unsigned report disallow all charges for that day, or only flag the invoice with amount unchanged?** Default disallow under Clause 15 and guideline 2. Affects MDS-00901, MDS-00842, MDS-00340; MDS-00901 falls by 47,191.22.

### 7.5 Rounding and money

- Use `Decimal` only and half-even rounding at each step.
- Half-up throughout would alter 878 lines and 370 invoice totals; billed values follow half-even. Example: MDS-01519-058, 1,916.50 × 0.93 = 1,782.345 → 1,782.34.
- Cents are `int(Decimal × 100)` after rounding.

---

## 8. Implementation and review plan within the 16-hour cap

The original drilling implementation plan allowed about four hours after transcription and design, prioritizing highest risks. Allocation of the cap between drilling and civil work was an owner decision. This section records the plan as written; it is not a new estimate of time remaining.

| Hour | Work | Completion criterion |
|---|---|---|
| 0–0.5 | Move `common.py`, `pricing.py`, `evidence.py` into a production module without changing logic; pin tables with page references | Twelve tests pass |
| 0.5–1.5 | Boundary-test highest-risk rules: A3/36A before/after issue, carrier and VAT per owner; 17B; 17A index month; Appendix G; 21A; 31A exchange month | Rejected alternatives still yield §6.2 figures |
| 1.5–2.5 | Build §5 pipeline, all 1,906 MDS rows, and line audit trail | Exactly reproduce 120 / 111 / 91,047 |
| 2.5–3 | Negative and deterministic controls (two identical runs), decision log | Zero control flags |
| 3–4 | Manually inspect two from each category and nine no-amount-change invoices; apply owner decisions | Documented |

**Production gates before writing drilling rows:**

1. Counts, unique keys, every report reference resolves, and every report word appears in Appendix G.
2. Exactly 91,047 lines reprice to the same cent, and every §6.2 alternative gives the same count; deviations indicate changed logic.
3. `expected_total_cents == billed_total_cents` on each unflagged invoice, and every amount-changing invoice is flagged.
4. Every flagged row has one §5.9 category, a recorded reason, and a contract-clause reference.
5. A3 settlement appears only on MDS-01625, with documented VAT decision.
6. Two runs yield one digest; cents are integers without `float`.
7. Full submission has 2,806 rows; 1,906 drilling rows do not alter civil rows.
