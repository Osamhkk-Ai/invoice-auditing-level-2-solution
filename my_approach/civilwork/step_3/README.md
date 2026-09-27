# Step 3: civil-works auditor (CW-2025-0417-CIV)

This step implements `../step_2_audit_system_design/civilwork_audit_architecture_final.md`, using the owner's accepted decisions Q1–Q3.
It produces the **civil-works part** of the challenge submission: 900 of the 2,806 rows.
It is **not** the complete `submission.csv`. The 1,906 drilling rows still have to be produced (see the last section).

## Run

Python 3.10 or later, standard library only; tested on 3.11.9. There are no dependencies to install or pin.
Run from the repository root:

```
python my_approach/civilwork/step_3/src/run_civilwork_audit.py          # regenerate everything in my_approach/civilwork/step_3/output/
python -m unittest discover -s my_approach/civilwork/step_3/tests       # 89 tests, about 20 s
```

The audit reads only the raw inputs: `invoice-auditing-level-2/civilwork/` and `submission_template.csv`.
The contract-transcription tests also read `my_approach/output_step_1/civilwork/page_*.md`.
A full run takes about 9 s. Output is deterministic: two runs give byte-identical files, and a test checks this.

| Output (`output/`) | Content |
|---|---|
| `civilwork_submission_part.csv` | **The artifact.** Template columns, 900 rows `PA-00001…PA-00900` in template order, money in integer halalas |
| `civilwork_line_audit.csv` | All 7,746 lines: evidence status, record quantity and item, supported quantity, the rate build-up (base and its instrument, factors, band parts, discount), expected amount, delta, categories, the clauses relied on, and the reasons in words |
| `civilwork_application_audit.csv` | All 900 applications: every cause with its clause and money effect, billed / line sum / expected, 31A and 45A amounts due, notes |
| `civilwork_ablation.csv`, `civilwork_scenarios.csv` | Rule ablation, and the Q1–Q3 and reading alternatives, from one baseline |
| `civilwork_run_summary.json` | SHA-256 of the input files, counts, flagged ids, the 31A and 45A plans |

### Merging with the drilling part later

```
python my_approach/civilwork/step_3/src/merge_submission.py --part my_approach/civilwork/step_3/output/civilwork_submission_part.csv --part <drilling_part>.csv --out submission.csv
```

The merge refuses to write the file unless every template id appears exactly once across the parts, with the template's columns and valid values.
With the civil-works part alone it exits with `1906 template ids missing`.

## Code map (`src/civilwork_audit/`)

| Module | Responsibility |
|---|---|
| `loader.py` | Loads the CSVs as text, parses money to `Decimal` (exactly two decimals), runs structural validation, and stops on any failure |
| `contract.py` | Contract constants with page citations. The five instruments are data (issue date, effective date, rates, monthly rates, discounts). Contains the effective-dated rate lookup, including the generic Clause 31A rule |
| `records.py` | Record parser. An explicit table of the 26 body patterns identifies the item from the record's own words and unit; unknown wording is never guessed |
| `evidence.py` | Per-line rules: unit, required record (series, area, date, item, ground, both signatures, 5-day week), supported quantity (6A, 33A, record), term, period, submission date |
| `cross_checks.py` | Global order (work date, application, line; Cl 30): Cl 44 duplicates, record reuse, Cl 31 daily limits, P19 exclusion, P21, and the Q2 alternatives |
| `pricing.py` | Clause 27 build-up with global band counters per Contract Year. Rounded once, half-up; conversions half-even |
| `diagnosis.py` | Explains a billed rate that does not reproduce, as a factor-by-factor category. It never sets the amount |
| `decisions.py` | Application level: Cl 41 / 43 / 45 / reference checks, the 31A carrier and amount, the 45A release, flag, category and confidence |
| `submission.py` | Writes the submission rows and audit trails, and runs the schema validation shared with the merge |
| `config.py` | `AuditConfig`: Q1–Q3 as accepted, with every alternative selectable. `PricingOptions`: ablation switches |
| `sensitivity.py` | Ablation and scenario runs |

The accepted decisions are the defaults in `config.py`:

- **Q1:** `a31_carrier="after_issue"` puts the adjustment on PA-00443.
- **Q2:** `weekly_duplicate=None`, so a repeated dewatering week is not a duplicate.
- **Q3:** `zero_after_submission=True` and `procedural_zero="none"`.

To run an alternative, change the config. For example, `ACCEPTED.with_(weekly_duplicate="A16")` treats every repeated A.16.010 week as a duplicate.

## Tests (`tests/`, 89 tests)

- **`test_contract_transcription`**: parses the Step 1 transcription tables and compares them with every constant in `contract.py`: Schedules 1–5, the instruments, the monthly rates, discounts and completion dates, and the controlling words of the clauses. The constants were mutated in turn to confirm the tests catch a changed value.
- **`test_pricing`**: hand-written arithmetic on real lines:
  - PA-00001-01, the band split PA-00576-09, and PA-00003-06 at the pre-issue rate
  - PA-00115-05, rounded once rather than at each step
  - PA-00233-04, where 593.865 rounds half-up to 593.87
  - PA-00397-12, where the USD conversion 1,588.365 rounds half-even to 1,588.36
  - the Year 2 band reset, and the 27/28 Sep freeze lines

  Synthetic cases cover rules the data never exercises: rest-day uplift alone at night on a rest day, the night cap per zone, discount dates, instrument sequencing, band edges, and a reduced quantity keeping its band position.
- **`test_independent_reprice`**: a separate re-pricer for C.32.010 and A.14.010 written from the contract text. It reads the raw CSV and counts bands unit by unit. It agrees with the engine on every line of both items and independently derives the 31A adjustment of 60,508.18 (26,521.21 + 33,986.97).
- **`test_records_and_evidence`**: all 2,169 records parse; DX-00089 lacks a countersignature; the imported-stone records; missing and wrong-series records; 6A; 33A; wrong units; term, period and submission date; Cl 44; daily limits; the P19 window at day 0 versus day 3; P21; and Q2.
- **`test_applications`**:
  - The flagged set, categories, totals and confidence are checked against Appendix A, parsed from the architecture document.
  - Q1, Q3, and 45A recomputed from the raw CSV.
  - Under-billed applications, and every flag having a cause.
- **`test_data_facts`**: the contract's own Appendix B worked example, including its 29A omission; line descriptions matching Schedule 1; and the application-level fields.
- **`test_submission_artifact`**:
  - Runs the documented command twice and compares the files byte for byte.
  - Checks that the committed output is current.
  - Checks the schema: 900 unique ids in template order, integer cents, and billed cents re-derived from the CSV text.
  - Exercises the merge guard, and checks the ablation and scenario counts.

## Comparison with the Step 2 verification baseline

Before deleting it, I re-ran the prototype and compared the two implementations field by field.

| Measure | Baseline | Step 3 |
|---|---:|---:|
| Billed line amounts reproduced | 7,703 | 7,703 |
| Residual lines / applications | 43 / 37 | 43 / 37 |
| Flagged applications (Q1–Q3) | 59 | 59 |
| Submission rows identical (all six columns, 900 rows) | — | 900 / 900 |
| Line supported quantity, contract amount, base, factors, categories | — | 7,746 / 7,746 identical |
| Application category sets; 31A (60,508.18 on PA-00443); 45A (4,034,571.73 on PA-00678) | — | identical |
| Ablation rows (23) and scenario rows (14) | — | identical counts and ids |

Documented examples reproduce exactly:

- PA-00043 = 23,142,526 cents and PA-00125 = 0.
- PA-00115 = 185,579.92, PA-00243 = 92,485.16, PA-00312 = 285,485.74.
- PA-00443 and PA-00678 are flagged with their totals unchanged.

**No output differs, so no rule was adjusted to match.** The differences below are in method and coverage. None of them changes a row in this data.

1. **Clause 30 (p6) states the global order in words.** It says "measurements executed on the same date are taken in order of application number and then line number". The architecture justified this order only by how well it fits the data. Schedule 4 Pt 3 says "Clause 30 is substituted" and states no order of its own, so this sentence is supporting textual evidence, not settled text.
2. **Records are parsed against an explicit table of the 26 patterns.** The quantity is captured by its position in the pattern, not taken as "the first number" in the body. A body in unknown wording, or a trench depth of exactly 2 m or 4 m (which fits two items; guideline check 6), becomes a `record_unrecognised` query at confidence 0.50 instead of being guessed. There are none in this data.
3. **Clause 31A is encoded generically.** Any instrument whose rates take effect before its issue date does not reprice an application submitted before that date. The prototype hard-coded A3.
4. **Checks added that do not fire in this data:**
   - work before commencement
   - a non-weekly record relied on by two lines (`record_reused`)
   - a missing foreman signature
   - a week of fewer than 5 days, as its own category (`week_under_five_days`)
   - P21 (`traffic_management_during_surfacing`)
   - retention and net arithmetic (Cl 45 / 45A)
5. **The Clause 40 period statement is recorded as a note, not a flag.** Three applications state a period other than the span of their items: PA-00154, PA-00678 and PA-00700. All three are already flagged.
6. **The 31A basis was investigated.** All 89 pre-issue lines are fully supported, so the adjustment is the same whether it is valued on billed or supported quantity.
7. **The audit trail now gives a reason for every line category.** The prototype left `line_arithmetic` lines (PA-00610-02, -00659-03, -00672-02) without one.

## What the full 2,806-row submission still needs

- **The drilling-services contract (1,906 invoices) has not been started.** Its contract `DDS-2025-118.pdf` still needs transcribing: `my_approach/output_step_1/drilling_services/` is empty. It then needs its own architecture and implementation, ending in a drilling part in the same format. After that, run `merge_submission.py`.
- **The challenge write-ups are still to do:** the short report with error analysis by failure type, the decision log, and a top-level README. The decision-log material for civil works is Part D of the architecture and the list above.
- **Confidence values are not calibrated**, because there are no labels. The way the grader encodes `expected_total_cents` for the 31A, 45A and procedural rows is unknown (architecture D3).
