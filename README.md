# Invoice audit, Level 2: civil works (CW-2025-0417-CIV) and directional drilling (DDS-2025-118)

## Video walkthroughs

### Civil works audit

https://github.com/user-attachments/assets/071ac9ec-b397-4b6d-9af3-4ea7bc7f6710

[Download civil works MP4](videos/invoice_audit_brief_voiced.mp4)

### Drilling services audit

https://github.com/user-attachments/assets/315e50ab-caaf-4690-b1f0-71973270de58

[Download drilling services MP4](videos/drilling_invoice_audit_explainer_dark.mp4)

These videos are teaching aids; the CSV, report, code, and decision log are the submission artifacts.

This repository audits every invoice under both contracts. `output/submission.csv` has the template's 2,806 rows in template order, with money in integer minor units. A byte-identical copy is also kept at the repository root as `submission.csv`.

| | Invoices | Flagged | Share | Lines reconciled exactly |
|---|---:|---:|---:|---:|
| Civil works (SAR) | 900 | 59 | 6.56 % | 7,703 of 7,746 |
| Drilling (USD) | 1,906 | 120 | 6.30 % | 91,047 of 91,181 priced |
| **Total** | **2,806** | **179** | **6.38 %** | |

The README's 5–8 % band was used only as a final sanity check. It was never used to choose a rule.

- **[REPORT.md](REPORT.md)**: how the approach performs, and the error analysis grouped by failure type.
- **[DECISION_LOG.md](DECISION_LOG.md)**: the ambiguities, the readings chosen, and what the alternatives change.

## Reproduce all submission files from a fresh clone

Clone the complete repository, including the `invoice-auditing-level-2/` input folder. Requirements: Python >= 3.10 (tested on CPython 3.11.9) and the standard library only. `requirements.txt` declares no third-party packages. Run from the repository root:

```bash
python generate_output.py
```

This regenerates each contract's part and audit trail from the raw inputs, then writes three submission-format files:

| File | Scope | Rows |
|---|---|---:|
| [`output/civilwork_submission.csv`](output/civilwork_submission.csv) | Civil works (A), SAR in integer halalas | 900 |
| [`output/drilling_submission.csv`](output/drilling_submission.csv) | Drilling services (B), USD in integer cents | 1,906 |
| [`output/submission.csv`](output/submission.csv) | Both contracts, in template order | 2,806 |

The combined file is copied to root `submission.csv` for the challenge hand-in and existing tests. The merge refuses missing, extra, or duplicate template IDs. The two individual CSVs use the same submission schema and are for inspection; the combined CSV is the requested submission.

Tests:

```
python -m unittest discover -s my_approach/civilwork/step_3/tests          # 89 tests
python -m unittest discover -s my_approach/drilling_services/step_3/tests  # 96 tests, includes the merge guard and submission.csv checks
python my_approach/drilling_services/step_3/src/compare_with_step2.py      # drilling vs its Step 2 prototype, field by field
```

Both auditors are deterministic. Two runs produce byte-identical outputs, and the tests check this. The SHA-256 of the drilling part is `a717e076a8b824dc23692fcdce4ea6de9968d5924baee5532cf12c58d0cefb19`; that of the combined `submission.csv` is `aac86d9fc940728e30ce513f7f09fa8e343ffe7796eb3aa3b16ba855130a628c`.

## Layout

```
invoice-auditing-level-2/          the exercise inputs (unchanged)
my_approach/output_ocr/            contract transcriptions (page by page + combined) and their validation reviews
my_approach/civilwork/             step_1 transcription prompts · step_2 architecture, review, verification · step_3 auditor
my_approach/drilling_services/     step_1 transcription prompts · step_2 architecture + verification prototype · step_3 auditor
generate_output.py                one-command regeneration from the raw inputs
output/                           civil, drilling, and combined submission CSVs
submission.csv                     root copy of the merged submission (2,806 rows)
videos/                            optional visual walkthroughs
```

Each `step_3/README.md` has the code map, the test list, and the comparison with that contract's Step 2 baseline:

- [civil works](my_approach/civilwork/step_3/README.md)
- [drilling](my_approach/drilling_services/step_3/README.md)

The audit trails are in each `step_3/output/`. For each contract there is one row per line and one per invoice, giving the evidence, the rate build-up, the clause relied on and the reason. The full drilling line trail (24 MB) is regenerated rather than committed; its 134 exception lines are committed.

## Method in brief

1. **Contract.** The scanned contracts (no text layer) were transcribed page by page. Each transcription was validated independently against the scan. The drilling review found 0 errors on 42 pages. Every constant the code uses is re-read from the transcription by a test.
2. **Design against the data.** Every reading was tested on the whole dataset. The README's advice decided between readings: "if your reading of a clause reprices invoices that reconcile exactly as billed, your reading is probably wrong". Rejected readings are kept as runnable scenarios with their counts.
3. **Production auditor.** Each contract has its own auditor. The steps are:
   - load and validate the inputs
   - parse every record against an explicit grammar; unknown wording becomes a query and is never guessed
   - work out what each record supports
   - price each line from the rate in force on the work date, with money in `Decimal` and each contract's own rounding
   - apply once-only, duplicate and limit rules in a documented global order
   - rebuild each invoice total, then flag and categorise it
4. **Independent checks.** For each contract:
   - a field-by-field comparison with the Step 2 prototype: identical on every line and invoice for both contracts
   - hand calculations on real lines
   - a separate integer-cent re-pricer: it agrees on 30,000+ drilling lines and derives the drilling Clause 36A difference of +309,965.52 independently
   - synthetic boundary cases for rules the data never exercises

## AI assistance (disclosure)

The work was done with Claude (Anthropic) as a coding and analysis assistant. This covered:

- the contract transcriptions and their independent validation
- the architectures and their review
- the verification prototypes
- the production code, tests and documents

A human project owner directed each step and made the decisions recorded in the decision log. Every prompt is versioned in Git next to the step it drove, in the order used:

| Step | Civil works | Drilling |
|---|---|---|
| 1 Transcribe the scan | `civilwork/step_1_ocr_extractor/step_1_to_claude.md` | `drilling_services/step_1_ocr_extractor/step_1_to_claude.md` |
| 1b Validate the transcription | `…/step_2_validate_output_file.md` | `…/step_2_validate_output_file.md` |
| 2 Design and verify | `civilwork/step_2_audit_system_design/step_1_design_audit_system.md` | `drilling_services/step_2_audit_system_design/step_1_design_audit_system.md` |
| 2b Independent review | `…/step_2_independent_architecture_review.md` (drafts v1 → v2 → final kept) | — |
| 3 Implement | `civilwork/step_3/step_1_implement_civilwork_auditor.md` | `drilling_services/step_3/step_1_implement_drilling_and_complete_submission.md` |

The prompts were iterated. For example, the civil architecture went through a draft, an independent review prompt, a v2 and a final, and the drilling design prompt was rewritten after the civil experience. The commit history shows each change.

**Time.** The exercise caps work at 16 hours across all steps. Commit timestamps show four sessions, 26–28 Sep 2026. The time from each session's first commit to its last adds up to about 7½ hours. Work before each session's first commit (for example the civil transcription) is not timestamped, so the real total is higher. The project owner should confirm it against the cap. No step was cut short.

**Superseded note.** The last section of `my_approach/civilwork/step_3/README.md`, "What the full 2,806-row submission still needs", predates the drilling work. This README supersedes it; the civil files were left unchanged.
