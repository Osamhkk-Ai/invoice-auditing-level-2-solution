# Step 1 — Study, test, and design the directional-drilling audit system

You are designing an auditable invoice-checking system for **the directional-drilling services contract DDS-2025-118 only**. The civil-works auditor is a separate project: do not transfer its prices, record rules, rounding choices, error counts, or interpretations to this contract. First read the contract and **test your interpretations against the complete drilling data**; only then write the final architecture. This is a design and verification step, not the production auditor or the final combined `submission.csv`.

## Inputs to read

1. Complete, page-ordered drilling contract transcription:
   `C:\Users\HP\Desktop\INS2\my_approach\output_ocr\drilling_services\drilling_services_contract_combined.md`
2. Original scanned contract, for checking controlling wording, dates, rates, table columns, and amendments:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\contract\DDS-2025-118.pdf`
3. Transcription and independent validation reports (context, not substitutes for the PDF):
   `C:\Users\HP\Desktop\INS2\my_approach\output_ocr\drilling_services\transcription_review.md`
   `C:\Users\HP\Desktop\INS2\my_approach\drilling_services\step_1_ocr_extractor\step_2_validation_report.md`
4. Every drilling invoice and line:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\invoices\invoices.csv`
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\invoices\invoice_lines.csv`
5. **All** daily drilling reports, including unusual and incomplete files:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\records\`
6. Drilling guidelines, exercise README, and submission template:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\guidelines\INVOICE_AUDIT_GUIDELINES.md`
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\README.md`
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\submission_template.csv`

The README states that drilling has **1,906 invoices, 91,244 lines, and 8,151 daily reports**. Verify these counts from the files yourself. Drilling money is in USD; the eventual submission uses integer cents and judges `invoice_total`, not `net_amount` alone.

## Required work order — evidence and tests before the final design

### 1. Read the whole contract

Read all 42 pages, including Parts VIII and IX, Schedules 2C/2D and 7/8, Appendices D–G, the Schedule of Variations, and every supplement and amendment. The Contents page is incomplete. Build a dated rule inventory with the exact PDF page, clause or schedule, item/service codes, effective date, issue date, formula, and evidence requirement. Inspect the scanned page itself wherever one character or table cell changes a rule. Do not silently complete description cells truncated in the printed contract. Treat the retroactive Amendment No. 3 explicitly.

### 2. Profile all invoices, lines, and reports

Read **all rows**, not a sample, to establish actual counts, keys, date ranges, currencies, invoice-to-line joins, report references, missing/duplicate links, well and rig identities, field and well class, service codes, units, hole sections, day statuses, depth ranges, amounts, VAT, adjustments, and repeated charges. Inventory every report body format and signature/approval pattern. Inspect representative and atypical reports for every format. State which fields are machine-readable and which require interpretation. Do not assume a single report template or that `report_ref` alone proves a charge.

### 3. Run reproducible checks **before** writing the architecture

Write small, readable verification scripts and tests under `my_approach/drilling_services/step_2_audit_system_design/verification/`. They are analysis tools, not a production auditor. Run them and save a concise `verification_report.md` in the Step 2 folder. At minimum:

- Assert file counts, key uniqueness, invoice-to-line joins, report file coverage, data types, currency precision, and that every submission-template drilling ID can be matched to one invoice.
- Compare each proposed rate, factor, cap, discount, exception, VAT rule, and amendment date with the scanned contract; test the arithmetic with `Decimal` and the contract's actual rounding points. Include boundary cases on both sides of each effective date and contract-year/period boundary.
- Analyze report-to-line links by well and date or run. Check what a daily report actually supports: work status, tools, personnel, operating/standby time, measured depth, and any other fields the contract makes relevant. Test competing ways to map free-text report language to priced service codes; do not choose a code merely because its price matches the invoice.
- Test rules that need state across invoices or days: cumulative quantities, minimums, limits, once-only charges, overlapping services, duplicate billing, and adjustment timing **where the contract requires them**. Identify the ordering key and verify that it is supported by the contract or mark it as an interpretation.
- Reconstruct line amounts and invoice totals where the evidence and contract permit. Count exact matches, unexplained differences, and invoices affected. For each rule, test a plausible alternative or switch it off and measure which lines change. Keep a few negative controls: unusual lines that are contractually correct must remain unflagged.
- Cross-check the contract's worked examples and schedules, if present. Investigate mismatches rather than forcing the model to reproduce billed figures. A line matching the biller establishes what was billed, not that the biller followed the contract.
- Validate the scripts themselves with hand calculations from real line references and report values. Run the checks twice and confirm deterministic counts. Record the exact command, test results, and unresolved cases. If some lines cannot be priced, quantify and explain them; do not guess a figure.

Do not infer precision, recall, or accuracy from the README's 5–8% anomaly range: there are no labelled answers. Use it only as a final reasonableness check, not a target for selecting rules or flags.

### 4. Write the architecture only after reviewing the test results

Write **one clear Arabic design document**, keeping code identifiers, field names, clause references, and formulas in their original notation:

`C:\Users\HP\Desktop\INS2\my_approach\drilling_services\step_2_audit_system_design\drilling_services_audit_architecture.md`

Make it understandable to a developer or auditor new to this contract, from the high-level workflow down to precise calculations. Include:

1. The claim being audited: `invoice_total` versus `net_amount`, `vat_amount`, `adjustment`, and any other contract-defined amount. Define the eventual submission fields and distinguish an invoice flag from an amount change.
2. A data map from invoice → line → daily report → contract item, with join keys, cardinalities, and missing or conflicting evidence behavior.
3. A contract rulebook grouped by eligibility and dates, records and approvals, service identity and units, measured quantities or time/depth, pricing and amendments, limits or exclusions, adjustments, VAT and total arithmetic. For every important rule give its source, inputs, formula/decision, applicable codes and dates, and unresolved ambiguity.
4. A report-to-line verification matrix for **every actual report format and billed service family**, including what report words/fields support the item, quantity, status, date/run, signatures, and exceptions.
5. The complete processing architecture in a fixed order: input validation; contract-version resolution; evidence join and classification; supported quantity/time/depth; line pricing; cross-invoice rules; invoice-level arithmetic; flag, category, expected USD cents, confidence, and audit trail. State which state must persist across days or invoices.
6. The numerical findings from the verification scripts: tested rule alternatives, exact line/invoice counts, representative correct and wrong examples with real IDs, and failures the design still cannot determine. Cite `verification_report.md` and the reproducible code.
7. Risks and decisions: OCR/table ambiguity, conflicting or retroactive instruments, misleading report wording, day-status and depth interpretation, missing evidence, duplicates, money rounding, and any other risks the data reveals. Separate contract text, observed data, and your chosen interpretation. Ask the project owner only for a decision that materially changes results and cannot be settled from the contract and data.
8. A concrete implementation and review plan within the exercise's **16-hour total cap**, with the highest-risk rules tested first. State what the later production auditor must verify before generating drilling submission rows.

Use the guidelines to organize the audit, but let the contract govern where they differ. Cite the PDF page and clause/schedule beside contract claims, and cite CSV filenames, invoice/line IDs, and report names beside data claims. Never present an untested assumption as a fact. Keep the final architecture aligned with the checks you actually ran; if a proposed rule was not tested, say so plainly.

Do not alter the PDF, transcription, invoices, daily reports, civil-works files, or submission template. Write only the Step 2 design document and its verification scripts/report. Do **not** write production code or `submission.csv` in this step.
