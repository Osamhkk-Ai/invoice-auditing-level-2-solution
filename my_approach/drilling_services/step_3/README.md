# Step 3: drilling-services auditor (DDS-2025-118)

This step implements `../step_2_audit_system_design/drilling_services_audit_architecture.md` as a production auditor. It regenerates all **1,906 drilling rows** from the raw inputs, and the guarded merge combines them with the 900 civil-works rows into the repository-root `submission.csv`.

## Run

Python 3.10 or later, standard library only; tested on 3.11.9. There are no dependencies to install. Run from the repository root:

```
python my_approach/drilling_services/step_3/src/run_drilling_audit.py        # all outputs, about 75 s (about 10 s with --skip-sensitivity)
python my_approach/drilling_services/step_3/src/compare_with_step2.py        # field-by-field check against the Step 2 prototype
python -m unittest discover -s my_approach/drilling_services/step_3/tests    # 96 tests, about 55 s
```

The audit reads only these files:

- `invoice-auditing-level-2/drilling_services/` (invoices, lines, 8,151 reports)
- `submission_template.csv`

The contract tests also read the validated transcription `my_approach/output_ocr/drilling_services/drilling_services_contract_combined.md`.

| Output (`output/`) | Content |
|---|---|
| `drilling_submission_part.csv` | **The artifact.** The template's six columns and 1,906 `MDS-` rows in template order, with money in integer cents |
| `drilling_invoice_audit.csv` | Every invoice: every cause with its clause and money effect, billed vs rebuilt services, discount, net, VAT, adjustment and total, confidence, exception lines, notes, warnings |
| `drilling_line_exceptions.csv` | The 134 lines with a defect: report file, supported quantity and its basis, rate build-up step by step, billed vs expected amount (also in cents), reasons, clauses, the mis-application that reproduces the billed rate, and the policy applied |
| `drilling_line_audit.csv` | The same trail for all 91,181 priced lines. It is 24 MB, so it is regenerated rather than committed (`.gitignore`) |
| `drilling_scenarios.csv` | 15 material alternative readings and 11 rejected ones. For each: lines, invoices and flags that change, and the changed expected totals in cents |
| `drilling_run_summary.json` | Input SHA-256, counts, unsigned/unreadable reports, reasons, flagged ids, the Clause 36A plan, and the configuration |
| `drilling_step2_comparison.json` | Output of `compare_with_step2.py` |

The output is deterministic. Two full runs gave byte-identical files; the SHA-256 of `drilling_submission_part.csv` is `a717e076…cefb19`. A test repeats this check and confirms that the committed files are current.

## Code map (`src/drilling_audit/`)

| Module | Responsibility |
|---|---|
| `money.py` | Parses money from text into `Decimal`; half-even `r2`; `to_cents` refuses any fraction of a cent. Floats never touch money |
| `contract.py` | Every table with its PDF page: Schedules 1–6, Part IX, Appendix G, and the five instruments as data (issue date, effective date, rates, monthly rates, discounts, expiry) |
| `loader.py` | Loads and validates the CSVs; stops on any structural failure. Checks counts, keys, contiguous line numbers, 2-dp money, whole quantities, that `report_ref` names the line's well, and the discount-line shape |
| `reports.py` | Parses each report against an explicit grammar: header, Parts A–E, conditional-part fields, both signatures, Appendix G words. Unknown wording or structure is recorded in `Report.problems` and never guessed |
| `evidence.py` | What a report supports, with the basis in words. Covers Clauses 20–31, 21A, 23, 25, 26, 27, P10, P13, and the Sch.3 Pt3/Pt5 limits |
| `pricing.py` | Rate build-up (Cl 18, 17A, 17B, S2 2.2, A2 2.3). The instrument in force is chosen generically, including Clause 36A for any retroactive instrument. Also PD-210 depth bands and Schedule 2 Part 2 volume bands, lost-in-hole value (31/31A), the Cl 38 discount and Cl 39 VAT |
| `audit.py` | The fixed order (module docstring): pools per well-day-code (PD-210 per interval); lines consumed in `(invoice_date, invoice_no, line_no)` order; the 36A plan and carrier; invoice rebuild, billed-figure checks, flag, category, confidence |
| `categories.py` | Reason → category → clause, the tie-break order, and confidence |
| `diagnosis.py` | Names the mis-application that reproduces a wrong billed rate. It never sets an amount |
| `config.py` | `PRODUCTION` plus every alternative reading as a switch |
| `sensitivity.py` | Scenario runs |

## How the Step 2 design risks were resolved

| Risk | Production setting | Evidence and alternatives (all in `drilling_scenarios.csv`) |
|---|---|---|
| **1. A3 carrier** | `a3_carrier="on_or_after"` → **MDS-01625**, the only invoice dated 2026-08-17 | Clause 36A says "on or after"; A3 says "after (Clause 36A)", deferring to 36A. Only "on or after" yields a single *first* invoice. Strictly after, three invoices tie on 2026-08-18 (MDS-01585, MDS-01631, MDS-01645) and the contract gives no tie-break. Each tie candidate moves the flag and the 30,996,552-cent difference to that invoice; the three are left unflagged at confidence 0.75. The same principle, choosing the reading with a single first invoice, is also the one civil works took (PA-00443) |
| **2. Adjustment, VAT, total** | `adjustment_treatment="in_total"`, `vat_on_adjustment=False`. MDS-01625 expected **53,626,610** vs billed 22,630,058 | Clause 40 says total = net + VAT. Clause 36 defines net as the charges and the DS-900 discount, and Clause 39 puts VAT on net, so the adjustment (not a charge, and outside net by the owner's no-VAT choice) carries no VAT. Clause 36A requires the adjustment to be *shown on the invoice*, and Clause 42 pays invoices; drilling has no counterpart of civil Clause 45A that keeps an adjustment outside the audited total. Read that way, the adjustment is payable only through the invoice total. **Alternatives:** separate entry → flagged, expected 22,630,058 (= billed); VAT on it → 58,276,092 |
| **3. Unsigned reports** | `unsigned_policy="zero_day"`: 33 lines on 3 invoices valued 0 | **Clause 37 alone** reaches only the Schedule 5 codes; on these days that is one RM-510 line. Expected totals then rise to MDS-00340 10,356,447; MDS-00842 6,047,284; MDS-00901 14,597,769. **Flag only** gives the billed totals (10,356,447; 6,047,284; 15,146,066). All three remain flagged under every policy |
| **4. Evidence gaps** | PD-210 performance-engineer proxy; Clause 21A per report day; the minimum after 21A; the 25A tolerance on | Every-section PD-210 changes no billed line; "bit and reamer" reprices 1,261 lines (rejected). The 21A per-run reading makes 3 flags disappear (MDS-00856, MDS-01338, MDS-01877), but the contractor bills h − 1 on 4,601 non-first-run days. The minimum order, the 25A tolerance and the standby discount rounding have no case in the data; synthetic tests pin them down. The standby rounding position is **provably moot**: every discounted base in force from April 2026 × 80 % is exact to the cent |

New finding: folding the S2/A2 discount into the rounding of the preceding factor would change 214 billed lines that now reconcile exactly. The data therefore confirms the discount as its own rounded step.

## Comparison with the Step 2 baseline

`compare_with_step2.py` runs the prototype code and production on the same inputs. It found **no differences in any field**:

- all 91,181 priced lines: supported quantity paid, contract rate, expected amount, reason codes
- all 1,906 invoices: rebuilt total, flag, invoice-level defects
- the Clause 36A amount and carrier

| Measure | Step 2 | Production |
|---|---:|---:|
| Priced lines reconciled exactly / exceptions | 91,047 / 134 | 91,047 / 134 |
| Flagged invoices / total changed | 120 / 111 | 120 / 111 |
| 36A adjustment | +309,965.52 on MDS-01625 | same; also +309,965.52 on billed quantity |
| Invoice defect reasons | identical sets on all 1,906 invoices | identical |
| Rejected alternatives | e.g. 402 / 940 / 15,635 / 778 / 3,309 / 47 / 878 lines | identical line counts |

No rule was changed to match the baseline. The differences are in coverage and method:

1. Reports are parsed against a grammar. Unknown wording produces a `report_unreadable` query at confidence 0.50, and the amount stays as billed. No real report triggers it.
2. The invoice-level checks cover the issuer, net = Σ lines, VAT, and a non-zero adjustment on an invoice that is not the carrier.
3. Clause 36A is encoded generically.
4. Schedule 2 Part 2 volume bands are priced, not just counted.
5. The half-up scenario now also rounds VAT half up, so it changes 414 invoice totals where Step 2 reported 370. Line counts are identical.
6. **Category labels changed on purpose.** Step 2's 14 labels (e.g. `RATE_WRONG`) became the vocabulary shared with civil works, so one label means one kind across `submission.csv`:
   - `record_missing`, `line_outside_period`, `rate_superseded`, `index_or_fx_month_wrong`, `qty_above_record` and others are shared.
   - Like civil works, a wrong rate is labelled by the mechanism that reproduces it (`diagnosis.py`). All 51 have a named mechanism.
   - Flags, amounts and reasons are unchanged; only the labels differ.

**Retained deliberately:** the Step 2 `verification/` scripts and their `out/` files. They are the independent prototype that `compare_with_step2.py` and `tests/test_step2_baseline.py` execute. The architecture and verification report cite them. Removing them would lose that evidence.

## Tests (96)

| File | What it pins |
|---|---|
| `test_contract_transcription` (16) | Every constant re-read from the transcription tables: Sch.1–6, Appendix G, instrument dates and rates, monthly rates, discounts, term. Also the controlling words of 36A/A3, 40, 39, 17B, 21A, 25A, 31A, 15, 37 and 23. Mutating constants one at a time was confirmed to make these tests fail |
| `test_pricing` (21) | The 43 effective-date boundaries; hand calculations on real lines (MDS-00001-003, -00214-011, -01739-041, -01519-058, -00121-043, -00307-006, -00639-027); Appendix B/F; discount and VAT edges; PD-210 splits and volume bands; the discount-fold proof; the generic 36A rule |
| `test_reports_and_evidence` (24) | All 8,151 reports parse; parts, status and signatures; Part B equals the daily sums on all 1,369 runs; conditional parts. Synthetic reports cover unknown wording, one missing signature, the 21 minimum × 21A in both orders, per-run 21A, standby exclusions, limits, per-run and per-well charges, the PD-210 proxy. Synthetic end-to-end runs cover 25A, a query row, duplicates across invoices, the three unsigned policies, and status taken from the report |
| `test_independent_reprice` (3) | A separate integer-cent re-pricer with its own tables and report reader. It agrees on every personnel, MW-310/HC-620 and lost-in-hole line (30,000+). It derives the 36A difference (3,309 lines, 30,996,552 cents) and checks the billed arithmetic of all 1,906 invoices |
| `test_invoices` (23) | Named invoices; rate labels by mechanism; 36A under every reading; unsigned policies; negative controls (Standby DD-111/LW-420, 375 band-split PD-210 lines, 3,309 pre-issue lines, 769 HC-601 lines, mis-quoted report numbers); consistency (every changed total is flagged; category = largest cause; totals are the sum of the trail) |
| `test_step2_baseline` (2) | Field-by-field identity with the prototype and with its committed outputs |
| `test_submission_artifact` (7) | Two runs byte-identical; committed files current; schema and billed cents re-derived from the CSV text; the merge refuses missing, extra and duplicate ids; `submission.csv` equals the merge and every billed figure equals the raw total |

## Limits

- There is no labelled data, so confidence is a documented judgement, not a calibration.
- The PD-210 call-off is absent, so the proxy is an interpretation. It fits all 2,206 billed performance days.
- The civil merger's `--out` needs a path with a directory part (`./submission.csv`). A bare file name makes `os.makedirs("")` fail. The civil code was left unchanged.
