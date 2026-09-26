# Step 2 — Validate the civil contract transcription

You are an independent proofreader. Compare the scanned source PDF against its Markdown transcription **page by page**. Your job is to find every transcription error you can, including a single wrong or missing character.

Source PDF:

`C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\contract\CW-2025-0417-CIV.pdf`

Transcription files:

`C:\Users\HP\Desktop\INS2\my_approach\output_step_1\civilwork\page_001.md` through `page_043.md`

Write your findings to this new report file:

`C:\Users\HP\Desktop\INS2\my_approach\output_step_1\civilwork\step_2_validation_report.md`

## Review method

1. Confirm the PDF page count and that exactly one Markdown file exists for each PDF page. Match `page_001.md` with PDF page 1, and continue in order through the last page.
2. Inspect the image of each page at a resolution that makes the smallest text readable. Zoom or crop dense tables, amendments, footnotes, headers, and footers. Do not rely on the existing `transcription_review.md` or Claude's earlier claims as evidence; compare the actual page image with the actual Markdown file.
3. Check every visible word and character as closely as possible: spelling, capitalization, punctuation, clause and item codes, dates, numbers, decimal points, currency, units, signs, percentages, and names. Check table cells against the correct row and column, and check that no line or section was omitted, duplicated, reordered, or moved to another page.
4. Count an actual transcription mismatch as an error even if it is only one letter, digit, punctuation mark, or space that changes the printed text. Do not count Markdown syntax or reasonable formatting differences as errors if the source text and table relationships remain faithful. Do not “correct” odd wording or contradictions in the source contract; report only differences between the image and transcription.
5. For each suspected error, inspect the source again at higher resolution before deciding. If the source remains unreadable, label that passage `unverifiable` instead of guessing or marking the Markdown correct.

## Report requirements

- Include a row for **every PDF page** with one of three statuses: `correct`, `has errors`, or `unverifiable`. A page is `correct` only after you have checked all of its visible content against the image.
- For each page with an error, list every discrepancy you found. Give the page number, a precise location (heading, clause, table row/column, or nearby text), the exact text in Markdown, the exact text visible in the PDF, and a short explanation. Quote only the small passage needed to locate the issue.
- Distinguish source-document oddities from transcription errors. For example, a cut-off description printed in the PDF is not a transcription error if Markdown copies it exactly.
- At the end, give the number of pages `correct`, `has errors`, and `unverifiable`, and verify that those three counts add up to the PDF page count. Also give the total number of individual discrepancies found. If any page could not be fully checked, explain why.
- State your review limits honestly. Do not claim a character-level check for a page you only skimmed.

Do not edit the PDF, any `page_*.md` file, or any other project file. Write only `step_2_validation_report.md`.
