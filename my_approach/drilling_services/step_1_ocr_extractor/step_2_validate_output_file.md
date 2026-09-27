# Step 2 — Independently validate the drilling-services transcription

You are an independent proofreader. Compare the scanned source PDF against its Markdown transcription **page by page**. Find every transcription error you can, including a single wrong or missing character. Do not rely on the transcriber's claim that the pages are correct.

Source PDF:

`C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\contract\DDS-2025-118.pdf`

Transcription directory:

`C:\Users\HP\Desktop\INS2\my_approach\output_ocr\drilling_services\`

The expected files are `page_001.md` through `page_042.md`, plus `transcription_review.md`. Confirm the PDF's actual page count independently before trusting that expectation.

Write your findings to this report file:

`C:\Users\HP\Desktop\INS2\my_approach\drilling_services\step_1_ocr_extractor\step_2_validation_report.md`

## Review method

1. Confirm that exactly one Markdown file exists for every PDF page and that filename, page order and printed page number agree.
2. Render and inspect **every page** at a resolution that makes its smallest text readable. Zoom or crop dense tables, amendments, footnotes, headers and footers. Compare every visible passage and table cell with its page file. Do not treat `transcription_review.md` as proof.
3. Check spelling, capitalization, punctuation, clause and item codes, dates, rates, decimal points, currency, units, signs, percentages and names. Verify the row and column association of every table cell, and check for omissions, duplications and content moved between pages.
4. Give extra attention to the high-risk locations noted by the transcriber: the multi-column tables on pages 18–22, 26 and 30; the variation tables and effective dates on pages 37–42; the code/description boundary printed as `MW-30lMWD` on pages 39 and 41; and the partly marked wording of Clause 2 on page 3. Inspect the PDF image itself before deciding whether the existing Markdown reflects the visible glyphs. Do not silently repair a scanned oddity using Schedule 1.
5. Reinspect each suspected difference at higher resolution. If the source remains unreadable, mark that passage `unverifiable` rather than guessing or calling it correct. Distinguish a real transcription mismatch from odd wording or truncated text already present in the source.

## Report requirements

- Include one row for **every PDF page** with status `correct`, `has errors`, or `unverifiable`. A page is `correct` only after its full visible content has been compared with the image.
- For every discrepancy, give the page number, precise location, short Markdown excerpt, short PDF excerpt or description of visible glyphs, and the proposed correction. Count even a one-character error. Do not count harmless Markdown formatting changes when the source text and table relationships are preserved.
- Summarize the number of pages in each status and the total number of individual discrepancies. The page-status counts must add up to the PDF page count.
- State any review limits honestly. Do not claim a full character-level check for a page you only skimmed.

Do not edit the source PDF, page files, invoices, records or other project files. Write only `step_2_validation_report.md`.
