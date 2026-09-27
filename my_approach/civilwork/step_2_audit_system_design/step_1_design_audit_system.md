# Step 1 — Design the civil works audit system

You are designing an auditable invoice-checking system for **the civil works contract only**. Do not work on the directional drilling contract. First study the actual contract and data; then write a clear architecture from the high-level workflow down to the detailed checks. This step is **design and analysis only**: do not implement the auditor or produce `submission.csv` yet.

## Inputs to read

1. Complete contract transcription, in page order:
   `C:\Users\HP\Desktop\INS2\my_approach\output_ocr\civilwork\civilwork_contract_combined.md`
2. Source scanned contract, to inspect whenever wording, a rate, a date, or a table relationship matters:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\contract\CW-2025-0417-CIV.pdf`
3. Transcription review and validation reports (use as context, not as substitutes for the contract):
   `C:\Users\HP\Desktop\INS2\my_approach\output_ocr\civilwork\transcription_review.md`
   `C:\Users\HP\Desktop\INS2\my_approach\civilwork\step_1_ocr_extractor\step_2_validation_report.md`
4. Civil works invoice data:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\invoices\applications.csv`
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\invoices\application_lines.csv`
5. All civil works site records:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\records\`
6. The civil works audit guidelines and exercise README:
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\guidelines\INVOICE_AUDIT_GUIDELINES.md`
   `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\README.md`

Write **one design document in clear Arabic**, keeping field names, item codes, clause numbers, and formulas in their original notation:

`C:\Users\HP\Desktop\INS2\my_approach\civilwork\step_2_audit_system_design\civilwork_audit_architecture.md`

## Study the evidence before designing

- Read the **entire** contract transcription, including the schedules, supplements, amendments, effective dates, and Part VII. Check the source PDF for any clause or table that affects a proposed rule. Do not assume the Contents page lists every instrument.
- Read both CSV schemas and profile **all rows**, not just the headers or first few examples. Report actual counts, date ranges, unique item codes, missing values, repeated references, joins between applications and lines, and any patterns that affect the design. Verify these findings with reproducible counts or queries.
- Inventory **all** record files by reference series and actual content type. Determine how many types exist and how many files of each type exist. Inspect representative files from every type and investigate atypical or malformed examples. Describe the fields and signatures that can actually be extracted. Do not assume every record has the same template.
- Compare the guidelines' twelve checks with the contract. Use the guidelines to organize the workflow; where they differ, the contract governs. Call out any difference that changes an audit decision.
- Use concrete examples from actual civil works invoice lines and their referenced records to test your understanding. Do not invent examples or claim that a rule has been validated by labelled answers; none are provided.

## Design document structure

1. **Purpose and scope.** In plain language, explain what one civil works application claims, what counts as a wrong application, which billed total is being judged, and what the eventual submission row must contain. Distinguish `application_total`, `retention`, `adjustment`, `retention_released`, and `net_payable` precisely.
2. **Data map.** Show the path from application to lines to records to contract rules. Name the join keys, cardinalities, and the checks needed for missing or duplicate links. Include a compact diagram or table if it helps.
3. **Contract rulebook.** Divide the rules into understandable groups, such as: contract and submission eligibility; work dates and instrument precedence; evidence and signatures; item identity and units; measurable quantity; base rates and zone/ground factors; uplifts, discounts, caps and exceptions; adjustments and retention; duplicates; and final arithmetic/rounding. For each important rule, state the source page/clause or schedule, required inputs, precise decision or formula, affected item codes/dates, and what to do when evidence is missing or the rule is ambiguous. Separate calculation rules from evidence/eligibility rules.
4. **Record-to-line verification.** Provide a matrix mapping every record type to relevant item codes, expected reference prefix, fields to compare, signature requirements, quantity interpretation, and any special conditions (for example, weekly records and surveys). Discuss the apparent tension between Clause 47's item-code requirement and Clause 47A's free-text site records without silently choosing a resolution.
5. **Processing architecture, high level to detail.** Explain the stages and their order: ingest and validate inputs; normalize dates, money and references; resolve the applicable contract version; join and assess evidence; measure supported quantity; compute the contract price; apply invoice-level adjustments and retention; detect duplicates across applications; reconcile totals; assign flag, error category, expected amount and confidence; and save an audit trail. Identify what state must be maintained across applications and why ordering matters. Use exact decimal/integer money arithmetic and state rounding points from the contract.
6. **Data-driven design choices.** Explain how findings from the actual CSVs and records change the proposed parser, rule engine, and review queue. Identify the few recurring patterns that can be deterministic and the cases that need human review. Do not suggest an AI classifier where a direct join or contract rule is sufficient.
7. **Verification without labelled answers.** Propose meaningful checks against the contract's worked example, internal arithmetic, repeated patterns that reconcile as billed, edge cases around amendment dates, and a small manual sample. Explain what each check can and cannot establish. Do not describe unmeasured precision, recall, or accuracy as facts.
8. **Risks and open decisions.** List likely failure modes: OCR/transcription, conflicting or retroactive amendments, wrong item mapping, record ambiguity, missing signatures, double billing, rounding, and any others found in the data. For each, give a detection or containment method. Record genuine contract ambiguities separately with a proposed interpretation and supporting evidence; do not present interpretations as settled facts.
9. **Implementation plan.** Give a short, ordered build plan for the civil works auditor, prioritized for the exercise's 16-hour cap. Say what can be automated now and what deserves human review first. Keep it concrete enough that a developer could implement it next.

Write for a reader who is new to this contract. Define technical terms once and use short examples. Put evidence citations next to claims using PDF page numbers and clause/schedule references, and cite data filenames or record references for data findings. Clearly separate **observed facts**, **contract interpretations**, and **proposed system behavior**. If you cannot verify a statement, label it as an open question. Do not change the input files or write any output other than the design document above.
