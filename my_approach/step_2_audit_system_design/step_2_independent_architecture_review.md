# Step 2 — Independent review of the civil works audit architecture

You are a **second, independent reviewer** of an audit-system design. Do not assume the design is correct because its author reports many matching invoice lines. Your job is to find factual, contractual, arithmetic, and architectural mistakes **before implementation**. Work on the civil works contract only; do not review the directional drilling contract.

Design to review:

`C:\Users\HP\Desktop\INS2\my_approach\step_2_audit_system_design\civilwork_audit_architecture.md`

Primary evidence:

- Original scanned contract: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\contract\CW-2025-0417-CIV.pdf`
- Page-by-page transcription: `C:\Users\HP\Desktop\INS2\my_approach\output_step_1\civilwork\page_001.md` through `page_043.md`
- Combined transcription: `C:\Users\HP\Desktop\INS2\my_approach\output_step_1\civilwork\civilwork_contract_combined.md`
- Payment applications: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\invoices\applications.csv`
- Application lines: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\invoices\application_lines.csv`
- Site records: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\records\`
- Guidelines: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\guidelines\INVOICE_AUDIT_GUIDELINES.md`
- Exercise brief: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\README.md`

Write your review in clear Arabic, keeping code, field names, formulas, and clause numbers in their original notation, to:

`C:\Users\HP\Desktop\INS2\my_approach\step_2_audit_system_design\civilwork_audit_architecture_review.md`

## Required review process

1. Read the complete design and the complete contract, including Part VII, every schedule, supplement, amendment, issue date and effective date. Check the source PDF image directly wherever a critical table, clause, number, or ambiguous wording is involved. Treat the contract as controlling over the guidelines and the design.
2. Recompute the design's important data claims **from the CSVs and records**, using your own queries or scratch scripts. At minimum verify: row and record counts; record types and their counts; missing, shared and mismatched references; malformed or unsigned records; invoice-to-line totals; the claimed 7,703/7,746 billed-line reconciliations and 43 residual lines; the 76 and 59 candidate-application counts; the 89 lines in 72 applications affected by retroactive Amendment No. 3; and any reported ablation counts. If a figure cannot be reproduced because the pricing algorithm or constants are not provided, say **not independently verified** rather than accepting it.
3. Review each proposed rule and formula against the contract. Pay particular attention to precedence between instruments; `work_date` versus `application_date`; Clause 31A; indexed and USD rates; order and rounding of factors, uplifts, discounts and quantity bands; rest-day/night rules; supported quantities and signatures; shared records and duplicate billing; retention and adjustments; and the distinction between `application_total` and `net_payable`.
4. Test whether the processing order and stored state are sufficient for cross-application rules. Find cases where a rule might wrongly flag a valid invoice, miss an error, or give the wrong `expected_total_cents`. Check edge dates and invoice lines around amendments and contract-year boundaries.
5. Examine the design's open questions. Distinguish what the contract resolves, what remains genuinely ambiguous, and what could be settled by inspecting the actual data. Do not turn a guess into a contract rule merely because it matches the biller's past calculations or the README's estimated error rate.
6. Do a few independent, fully worked examples using actual `line_ref` and `record_ref` values. Show the contract clauses, input values, intermediate calculations, rounding, and conclusion. Include at least one ordinary line and examples around an amendment or record requirement.

## Report format

- Start with a short verdict: **ready to implement**, **ready with corrections**, or **not ready**. Explain the practical reason.
- Give a table of findings ordered by severity (`critical`, `major`, `minor`). For each finding include: the exact section/claim in the design, evidence from a contract page/clause or data row/file, your independent calculation or observation, the likely effect on flagged invoices or amounts, and a concrete correction.
- Add a separate table for key numerical claims with status `verified`, `contradicted`, or `not independently verified`, showing how you checked each one. A claim is not verified merely because the design says it was measured.
- List any contract interpretations that still require a human decision, with at least two plausible readings when appropriate.
- End with a prioritized correction list that a developer can apply before coding. State what you did **not** check so the verdict is calibrated.

Do not edit the design, transcriptions, source data, or contract. Write only the review report at the path above. Use temporary scratch work outside the project if needed, and include enough method or compact code in the report for another person to reproduce important numerical checks.
