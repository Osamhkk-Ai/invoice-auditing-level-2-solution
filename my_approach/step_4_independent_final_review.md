# Independent final review — blind, adversarial, evidence-led

You are the final independent reviewer of a two-contract invoice-auditing submission. This is a hiring exercise. Accuracy matters more than reassurance, agreement, or finding a flaw for its own sake. Look actively for **real, consequential mistakes**, but do not invent speculative ones. Be direct and fair.

Workspace root: `C:\Users\HP\Desktop\INS2`

## Phase 1 — Form your own answer before seeing ours

Read the challenge requirements and template:

- `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\README.md`
- `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\submission_template.csv`

Independently examine **both** source contracts, their amendments, guidelines, complete invoice data, and records:

- Civil contract scan: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\contract\CW-2025-0417-CIV.pdf`
- Civil guidelines: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\guidelines\INVOICE_AUDIT_GUIDELINES.md`
- Civil invoices: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\invoices\`
- Civil site records: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\records\`
- Drilling contract scan: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\contract\DDS-2025-118.pdf`
- Drilling guidelines: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\guidelines\INVOICE_AUDIT_GUIDELINES.md`
- Drilling invoices: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\invoices\`
- Drilling daily reports: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\records\`

The page transcriptions under `C:\Users\HP\Desktop\INS2\my_approach\output_ocr\` may help you navigate the scans, but verify controlling words, figures and table relationships against the **PDF images**. The contract governs where a guideline differs.

Before opening any of our architecture documents, code, tests, generated audit trails, reports, or `submission.csv`, record your own interpretation of the important contract rules and create independent, runnable checks. Use your own constants, parsing, and calculations wherever practical. Test invoice-to-line and line-to-record links, evidence, signatures, dates, units, quantities, service identity, amended rates, factors, limits, duplication, adjustments, discounts, taxes, rounding, totals, and submission-format requirements. Check boundary cases and unusual but valid charges as well as suspected errors. Use exact decimal or integer-cent arithmetic. Do not use billed amounts as a substitute for contract authority.

Save your independent scripts and intermediate findings **only** under:

`C:\Users\HP\Desktop\INS2\my_approach\temp\independent_final_review\`

Record what you actually tested, your candidate flags and amounts, and unresolved contract interpretations **before** Phase 2. If complete independent repricing is impractical within the exercise's time cap, prioritize rules with the widest financial effect, report exact coverage, and do not imply that untested rows were verified.

## Phase 2 — Challenge our submission

Only after recording your Phase 1 findings, inspect:

- Final submission: `C:\Users\HP\Desktop\INS2\submission.csv`
- Reproduction instructions: `C:\Users\HP\Desktop\INS2\README.md`
- Report and decisions: `C:\Users\HP\Desktop\INS2\REPORT.md` and `DECISION_LOG.md`
- Civil implementation, tests and audit trails: `C:\Users\HP\Desktop\INS2\my_approach\civilwork\step_3\`
- Drilling implementation, tests and audit trails: `C:\Users\HP\Desktop\INS2\my_approach\drilling_services\step_3\`
- Earlier designs and verification work: the `step_2_audit_system_design` folders under each contract, **after** your independent view is fixed.

Run the repository's documented commands and tests yourself. Verify that a clean run reproduces `submission.csv` byte for byte and that every template ID appears exactly once, in order, with valid integer minor-unit amounts. Check whether the claimed tests can catch incorrect rules, rather than merely confirming the same assumptions as the implementation. Compare your independent results with ours at the line and invoice level. Investigate material disagreements using the original PDF page and raw record. Recalculate disputed amounts without importing our pricing or evidence functions.

For every confirmed error, give the exact affected invoice and line IDs, the relevant contract page/clause and record, our flag/category/amount, your corrected result, and the financial or scoring effect. Separate:

1. Confirmed errors that require a change to `submission.csv`;
2. Genuine contractual ambiguities with quantified alternative outcomes;
3. Documentation or test weaknesses that do not change a row;
4. Matters you could not verify.

Do not anchor on our expected counts, our confidence scores, or the README's anomaly percentage. Do not inflate the issue list with harmless quirks. If you find no material error, state the precise coverage and limits of your work instead of claiming perfect correctness.

## Verdict

Write your full independent findings to:

`C:\Users\HP\Desktop\INS2\my_approach\independent_final_review.md`

Lead with a plain answer: **Is this submission ready to send, yes or no, and why?** Rank findings by their effect on the actual submission. Give the smallest concrete corrections needed before sending, and an honest account of what remains uncertain. Tell us if our work is right; tell us just as clearly if it is wrong. We need accuracy for a hiring decision, not reassurance and not unnecessary overanalysis.

Do not modify `submission.csv`, source data, contracts, existing code, tests, or documents. Do not email, publish, or commit anything. Respect the exercise's **16-hour total work cap** across prior work and this review: track time you spend, and if the remaining budget is unknown, state that limitation rather than claiming compliance.
