# Step 3 — Implement the civil-works auditor and start the submission

You wrote the final civil-works architecture and verification package in the previous step. The project owner has accepted the three documented decisions (Q1–Q3) and authorized implementation. Start now; do not repeat the architecture exercise.

## Goal

Build a maintainable, runnable civil-works invoice auditor from `civilwork_audit_architecture_final.md`. Put **all production Python code under `my_approach/civilwork/step_3/src/`**. Use the existing `civilwork_verify.py` as a checked prototype, but refactor or port its rules into the Step 3 implementation rather than treating its existing output as the final deliverable.

Generate the civil-works portion of the submission from source data: **900 rows**, one per civil-works application, with the exact columns, IDs, integer-cent amounts, and conventions required by `submission_template.csv` and the repository README. Write this as a clearly named civil-works submission artifact in Step 3. The challenge's final `submission.csv` needs **2,806 rows across both contracts**; do not fill the 1,906 drilling rows with guesses or present the civil-works artifact as the complete challenge submission. Make it straightforward to merge the drilling results later.

## Implementation requirements

1. Read the final architecture, verification report, README, guidelines, source contract, invoice CSVs, records, and submission template. The contract controls where sources disagree. Preserve the accepted Q1–Q3 decisions exactly, and keep their alternatives configurable so sensitivity runs remain possible.
2. Split the implementation into understandable modules under `step_3/src/`: input loading and validation, contract constants and effective dates, record parsing and matching, eligibility and supported quantities, global ordering and quantity bands, rate building, application decisions, and submission writing. Use `Decimal` and the contract's stated rounding modes; do not use binary floating point for money.
3. Implement the full civil-works flow on all 900 applications and 7,746 lines. Keep a line-level and application-level audit trail showing the evidence, clause, calculation, and reason for each flag. A flagged application may have an expected total equal to its billed total when the breach concerns a required adjustment, release, or procedure.
4. Retain the documented decisions: PA-00443 carries the Clause 31A adjustment; a shared dewatering week with different work dates is not automatically a Clause 44 duplicate; and `expected_total_cents` values only work supported at the submission date, including PA-00043 = 23,142,526 cents and PA-00125 = 0.
5. Write meaningful automated tests using real boundary cases and independent arithmetic checks. Include the cases from the final architecture and report, but do not merely assert that one implementation path reproduces another path. Test generated file schema, all 900 IDs, cent units, unique rows, and deterministic output.
6. Compare the implementation against the verification baseline: 7,703 matching billed lines, 43 residual lines in 37 applications, 59 flagged civil-works applications under Q1–Q3, and the documented examples and totals. Investigate every difference; do not adjust rules just to force the counts to match. Record any justified deviation with its contract evidence.
7. Provide one documented command that regenerates the civil-works submission artifact from the repository's raw inputs. Run it twice and compare outputs. Keep dependencies pinned if any are introduced; prefer the standard library if it remains sufficient.

## Clean up experiments after replacement

Once the Step 3 code, tests, audit trail, and civil-works submission artifact reproduce the required results, remove **obsolete generated experiments and superseded prototype files** from Step 2, including `civilwork_verification_output/` and `civilwork_verify.py` if their useful behavior has been migrated. Update any documentation that points to removed files. Preserve the final architecture, the verification report if it still documents evidence, all versioned prompts, source PDFs, transcriptions, raw data, and unrelated user files. Inspect the exact files before deleting them; never delete the whole Step 2 folder or broad directory trees merely for tidiness.

## Completion criteria

Finish with the runnable civil-works implementation, tests, an auditable 900-row submission-format artifact, and concise run instructions. Report the actual test results, baseline comparison, files removed as obsolete experiments, and anything still needed for the full 2,806-row challenge submission. Respect the exercise's **16-hour total work cap**: if the cap is reached, stop and document remaining work rather than silently exceeding it.
