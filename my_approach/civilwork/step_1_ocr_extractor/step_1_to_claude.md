# To Claude 1 — Transcribe the first contract PDF

You are transcribing a scanned, image-only contract. Read **every page** of this PDF, in page order:

`C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\civilwork\contract\CW-2025-0417-CIV.pdf`

Write the transcription as Markdown files in this output directory:

`C:\Users\HP\Desktop\INS2\my_approach\output_ocr\civilwork\`

Create one file per PDF page, named `page_001.md`, `page_002.md`, and so on through the final page. The filename number must match the PDF page number, starting at 1. Process the full PDF, including schedules, supplements, amendments, tables, signatures, headers, and footers. The existing `page_001.md` is a draft to verify against page 1; do not simply copy it without checking the image.

## Accuracy requirements

- Transcribe what is visible. Do not summarize, interpret, silently correct, or invent contract language.
- Preserve exact names, item codes, dates, quantities, units, rates, percentages, currency amounts, and amendment effective dates. Check each digit carefully.
- Preserve headings, paragraph order, numbered clauses, and table row and column relationships. Use Markdown tables where they remain readable. If a table is too complex, use a clearly structured list that preserves every cell and its row/column association.
- Keep each page separate, even when a paragraph or table continues onto the next page. Do not merge content across page files.
- Mark unreadable text as `[unclear]`. For a partly readable word or number, preserve the readable portion and mark only the uncertain part, such as `20[unclear]`.
- Do not infer missing words or numbers from another page. If you use a later page to resolve an unclear passage, make that explicit in a separate review note, not in the transcription itself.
- Do not translate the text. Keep the contract's original language and spelling.

After writing each page, visually compare the Markdown with that page's image and correct transcription errors. At the end, create `transcription_review.md` in the same output directory with: the page count processed, a list of pages containing `[unclear]`, and any tables or passages that need human verification. Do not claim a page was checked unless you actually compared it with the image.

Work only on the civilwork contract and this output directory. Do not edit the source PDF, the drilling contract, invoices, records, or other project files.
