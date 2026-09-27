# Step 3 — Implement the drilling auditor and complete the submission

You produced the drilling Step 2 architecture and verification package. The project owner has authorized implementation. Build a runnable production auditor for **DDS-2025-118**, test it thoroughly, generate all **1,906 drilling rows**, and merge them with the existing **900 civil-works rows** into the challenge's complete **2,806-row `submission.csv`**. Do the work; do not stop after writing another design.

## Inputs and existing work

- Drilling architecture: `my_approach/drilling_services/step_2_audit_system_design/drilling_services_audit_architecture.md`
- Drilling verification report and scripts: `my_approach/drilling_services/step_2_audit_system_design/verification_report.md` and `verification/`
- Validated contract transcription: `my_approach/output_ocr/drilling_services/drilling_services_contract_combined.md`; inspect the original `invoice-auditing-level-2/drilling_services/contract/DDS-2025-118.pdf` whenever wording or a table cell controls a rule.
- Raw drilling data: `invoice-auditing-level-2/drilling_services/invoices/`, `records/`, and `guidelines/INVOICE_AUDIT_GUIDELINES.md`.
- Challenge requirements and row order: `invoice-auditing-level-2/README.md` and `submission_template.csv`.
- Existing tested civil-works implementation and part: `my_approach/civilwork/step_3/`, especially `output/civilwork_submission_part.csv` and `src/merge_submission.py`.

All production drilling code belongs under **`my_approach/drilling_services/step_3/src/`**. Put tests under `step_3/tests/`, generated drilling audit artifacts under `step_3/output/`, and run instructions in `step_3/README.md`. Keep the Step 2 verification scripts as independent evidence until production outputs have been compared field by field; then retain or clean them deliberately, with no lost reproducibility.

## Resolve design risks before locking the baseline

Re-read the controlling contract text and test the consequences of these issues. Do not silently treat an interpretation as a contract fact:

1. **Amendment No. 3 carrier:** Clause 36A says the first invoice submitted **on or after** 2026-08-17; A3 itself says **after** that date. The Step 2 baseline uses `MDS-01625` on 2026-08-17. Compute the strict-after scenario, document the same-date tie, and make the carrier policy configurable. Use the Step 2 baseline as the initial production setting unless a better contract-supported resolution is established and documented.
2. **Adjustment, VAT, and `invoice_total`:** Clause 39 calculates VAT on `net_amount`; Clause 40 defines the total as net plus VAT; Clause 36A requires a single adjustment. The owner's working choice is **no extra VAT on the adjustment**. Test whether the adjustment belongs inside the audited `invoice_total` or is a separate payable entry, show both outcomes for `MDS-01625`, and state exactly which reading the submission uses. Do not infer this solely from the CSV field layout.
3. **Unsigned Daily Drilling Reports:** Clause 15 requires both signatures and Clause 37 makes named records a condition of payment for Schedule 5 services. The working choice is to flag the three affected invoices and exclude charges supported only by an unsigned report. Test and report the alternative that flags the procedural defect without zeroing all charges; distinguish services expressly covered by Clause 37 from the broader evidence reading.
4. **Known evidence gaps:** the PD-210 call-off is absent; the performance-engineer proxy is an interpretation. The 6-hour minimum with Clause 21A, the 1% metres tolerance, and some Standby discount rounding cases are not exercised by the data. Keep these configurable or covered by synthetic boundary tests, and disclose the remaining uncertainty.

If a decision is genuinely necessary to produce a defensible submission and cannot be resolved from the contract and the accepted working choices, ask the project owner a concise question with the affected invoice IDs and amounts. Continue all independent implementation work while waiting. Do not delay the entire build for a question that can be represented as a documented scenario.

## Implement the auditor

1. Load and validate all 1,906 invoices, 91,244 lines, 8,151 daily reports, and all relevant contract tables. Use `Decimal` or integer cents, with the contract's half-even and other specified rounding at the correct steps. Never use binary floating point for money.
2. Parse every report, including its conditional Parts C/D/E, signatures, well, rig, date, status, hole section, depths, circulating hours, tools, crew, run numbers, and loss details. Match report wording to service codes using the contract and Appendix G; unknown wording must become a reviewable query, not a guessed code.
3. Resolve dated supplements and amendments, including the retroactive A3 rule. Compute each supported quantity and rate, depth-band splits, monthly index or exchange rate, discount, VAT, and invoice total. Apply across-day and across-invoice limits, once-per-well/run rules and duplicate checks in a documented deterministic order.
4. For each line and invoice, retain an audit trail with source report, clause, supported quantity, rate components, billed versus expected cents, reasons, and interpretation policy. Flag a procedural or adjustment error even when `expected_total_cents == billed_total_cents` if that is the documented reading.
5. Generate `my_approach/drilling_services/step_3/output/drilling_submission_part.csv` with exactly the 1,906 `MDS-` IDs in template order and the template's six columns. Do not copy the Step 2 flagged CSV as the production result; regenerate from raw inputs.

## Test and independently verify

- Write meaningful unit and integration tests for contract constants, report parsing and signature/part requirements, date boundaries, A3 pre-issue pricing and carrier, rate factors, index/exchange months, half-even rounding, PD-210 band splits, operating/standby logic, lost-in-hole depreciation, discounts, VAT, duplicate/once-only rules, invoice totals, and each output column.
- Use real documented invoice/line/report examples **and** synthetic boundary cases for rules that the dataset never exercises. Include negative controls for unusual but valid billing. Tests must independently calculate expected figures where practical; do not merely compare two paths through the same implementation.
- Compare the production run with the Step 2 verification baseline: 91,047 exact matches among 91,181 priced lines, 134 line exceptions, 120 flagged invoices, the +309,965.52 USD A3 adjustment, and the named examples. Investigate every deviation. Correct a rule only because the contract and evidence justify it, never to force the baseline count or the README's 5–8% band.
- Run the full auditor twice and compare SHA-256 hashes. Verify every drilling template ID appears once, money fields are integer cents, rows are deterministic, and the sum/flag/category claims are consistent with the audit trails.
- Test sensitivity for the carrier, adjustment/VAT treatment, unsigned reports, PD-210 proxy, and other material readings. State which invoices and expected totals change. Keep confidence honest; there is no labelled development set.

## Complete the challenge deliverables

1. Regenerate the civil-works part from its current code and run its tests; do not change its rules merely to accommodate the drilling results.
2. Use the existing guarded merger (or an equivalently strict merger) to write **`submission.csv` at the INS2 Git repository root**, containing exactly **2,806 unique IDs in template order**, with no blank or guessed drilling rows. Validate the combined file against the raw totals and template. Test that merging fails on a missing, extra, or duplicate ID.
3. Write a top-level `README.md` with commands to regenerate both parts and the complete submission from a fresh checkout. State Python version and pin any added dependencies. Prefer the standard library if sufficient.
4. Write the required short report with error analysis **grouped by failure type**, giving a real example and a limitation for each type; and a **one-page decision log** with contract ambiguities, chosen readings, affected rows, and alternative effects. Disclose AI assistance and keep this prompt and earlier prompts versioned in Git.
5. Do not email or publish the submission. Finish with a factual account of files produced, tests run, baseline differences, unresolved risks, and the exact command to reproduce `submission.csv`.

Respect the exercise's **16-hour cap across all steps**, not just this one. If the total cap is reached, stop and document remaining work rather than claiming completion. Do not alter source PDFs, raw CSVs, reports, validated transcriptions, or unrelated civil-works files.
