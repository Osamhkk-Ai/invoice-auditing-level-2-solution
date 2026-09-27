# Step 2 — Validation of the civil contract transcription

**Source PDF:** `invoice-auditing-level-2/civilwork/contract/CW-2025-0417-CIV.pdf`
**Transcription:** `my_approach/output_ocr/civilwork/page_001.md` to `page_043.md`
**Review date:** 2026-09-26
**Reviewer role:** independent proofreader, comparing the page images against the Markdown files directly. The existing `transcription_review.md` was not used as evidence.

## 1. Scope and method

- **Page count.** The PDF has 43 pages. The PDF has no text layer (each page is a single scanned image), so no automated text diff was possible. Exactly 43 Markdown files exist, `page_001.md` to `page_043.md`, with no gaps or duplicates. `page_NNN.md` was matched with PDF page NNN in order, and the printed footer "Page N" on every image agrees with its file number.
- **Rendering.** Every page was rendered with PyMuPDF at 200 dpi (1654 x 2338 px) and read in full. For the densest numeric tables (pages 17, 18, 21, 22, 25 and 36) the quantity, rate, index, exchange-rate, band, percentage and amount columns were re-rendered at 300 dpi as crops and re-read to rule out digit confusions (3/8, 6/8, 0/6, 1/7).
- **What was compared.** Headers, footers, headings, clause numbers and titles, body text, item codes, dates, numbers, decimal points, thousands separators, currency labels, units, percentages, names, addresses, and every table cell against its row and column. Line breaks inside a cell or paragraph, Markdown heading levels, bold markup, table alignment markers and the `---` rule used to separate header and footer were treated as formatting, not content.
- **Standard applied.** A discrepancy is any difference between the printed characters and the Markdown characters. Source-document oddities that the Markdown reproduces exactly are not discrepancies; they are noted separately in section 4.

## 2. Page-by-page results

| Page | Content | Status | Discrepancies |
|---|---|---|---|
| 1 | Title page, Agreement, key-terms table | correct | 0 |
| 2 | Contents | correct | 0 |
| 3 | Part I, Clauses 1–10 | correct | 0 |
| 4 | Part I, Clauses 11–22 (heading only for 22) | correct | 0 |
| 5 | Part I, Clauses 22 (body)–24 | correct | 0 |
| 6 | Part II, Clauses 25–32 | correct | 0 |
| 7 | Part II, Clauses 33–39 | correct | 0 |
| 8 | Part III, Clauses 40–50 | correct | 0 |
| 9 | Part III, Clauses 51–52 | correct | 0 |
| 10 | Part IV, S1–S11 | correct | 0 |
| 11 | Part IV, S12–S20 | correct | 0 |
| 12 | Part V, P1–P11 (heading only for P11) | correct | 0 |
| 13 | Part V, P11 (body)–P21 | correct | 0 |
| 14 | Part V, P22–P25 | correct | 0 |
| 15 | Part VI, H1–H12 (heading only for H12) | correct | 0 |
| 16 | Part VI, H12 (body)–H15 | correct | 0 |
| 17 | Schedule 1, Series A (18 rows) and Series B (8 rows) | correct | 0 |
| 18 | Schedule 1, Series B cont. (6 rows), Series C (11 rows), Series D (11 rows) | correct | 0 |
| 19 | Schedule 1, Series E (6 rows) and note | correct | 0 |
| 20 | Schedule 2, zone factors and work areas | correct | 0 |
| 21 | Schedule 2A, indexed rates and 24-month index table | correct | 0 |
| 22 | Schedule 2B, USD rates and 24-month exchange table | correct | 0 |
| 23 | Schedule 3, ground classification factors and item list | correct | 0 |
| 24 | Schedule 4, Parts 1–3 (Part 3 first 4 rows) | correct | 0 |
| 25 | Schedule 4, Part 3 cont. (20 rows), Part 4 heading | correct | 0 |
| 26 | Schedule 4, Part 4 table, Parts 5–6, note | correct | 0 |
| 27 | Schedule 5, records table (17 rows) and note | correct | 0 |
| 28 | Schedule 6, Parts 1–3 (Part 3 first 2 rows) | correct | 0 |
| 29 | Schedule 6, Part 3 cont. and note | correct | 0 |
| 30 | Schedule 7, provisional and prime cost sums | correct | 0 |
| 31 | Schedule 8, preliminaries (14 rows) and notes | correct | 0 |
| 32 | Part VII, 3A–45A | correct | 0 |
| 33 | Part VII, 47A | correct | 0 |
| 34 | Appendix A, definitions (15 rows) | correct | 0 |
| 35 | Execution | correct | 0 |
| 36 | Appendix B, form of payment application | correct | 0 |
| 37 | Appendix C, insurances and notices | correct | 0 |
| 38 | Schedule of Variations | correct | 0 |
| 39 | Supplement No. 1 | correct | 0 |
| 40 | Amendment No. 1 | correct | 0 |
| 41 | Supplement No. 2 | correct | 0 |
| 42 | Amendment No. 2 | correct | 0 |
| 43 | Amendment No. 3 | correct | 0 |

## 3. Discrepancies found

None. No page contained a character, digit, punctuation mark, code, date, unit, name or table cell that differed from the printed image, and no line, row or section was omitted, duplicated, reordered or moved between pages.

## 4. Source-document oddities reproduced faithfully (not transcription errors)

These are features of the printed contract that a reader might mistake for transcription mistakes. In each case the Markdown copies the page exactly, which is the correct behaviour.

- **Page 2, Contents:** Part VI is listed before Part IV and Part V, and Part VII (which exists on page 32) and the Schedule of Variations are not listed. Transcribed as printed.
- **Page 17, Series A:** item codes are not in numeric order (A.11.030 appears after A.14.020). Row order transcribed as printed.
- **Page 18, Series C and D:** same non-sequential code ordering. Transcribed as printed.
- **Page 20, Schedule 2:** Z1 factor printed as "1" without decimals. Transcribed as "1".
- **Page 23, Schedule 3:** G2 factor printed as "1". Transcribed as "1".
- **Page 26, Part 6 note:** cites "(Clause 8)"; transcribed as printed.
- **Page 38, Amendment No. 3 row:** "Issued 2026-05-12, Effective 2025-11-01" (effective date before issue date). This is what the page shows and is consistent with page 43. Transcribed as printed.
- **Page 39, table row B.23.010:** description is cut off at "High-yield reinforcement bar, cut," in the PDF. Transcribed with the cut-off.
- **Page 40, table rows:** "Temporary haul road, maintained, p" and "High-yield reinforcement bar, cut," are cut off in the PDF. Transcribed with the cut-offs.
- **Page 41, table row D.41.020:** description reads "Dense bitumen macadam binder cours" (cut off) and the unit is printed as "m2" although the Supplement No. 1 rate for the same item is per tonne. Transcribed as printed.
- **Page 43, table rows:** "Precast manhole, 1200 mm diameter," and "Imported granular fill, placed and" are cut off in the PDF. Transcribed with the cut-offs.
- **Pages 39 and 43:** references to "Clause 26.4", "Clause 26.6" and (page 40) "Clause 14.2" do not correspond to any numbered sub-clause in the contract. Transcribed as printed.
- **Page 25 and page 39–43 tables:** where the PDF wraps a description over two lines inside one cell, the Markdown joins the two lines into one cell. This is a formatting difference, not a content difference.

## 5. Counts

| Status | Pages |
|---|---:|
| correct | 43 |
| has errors | 0 |
| unverifiable | 0 |
| **Total** | **43** |

The three counts sum to 43, which equals the PDF page count.

**Total individual discrepancies found: 0.**

## 6. Review limits

- Every page was read in full at 200 dpi, and every table row and column was checked cell by cell. The six densest numeric pages were additionally checked at 300 dpi. No page was skimmed and no page was left partially checked.
- The scans are clean and every character on every page was legible at 200 dpi, so no passage had to be marked unverifiable.
- The check is a visual comparison by a single reader against rendered images. No OCR text layer exists in the PDF, so no machine diff was available as a second, independent check.
- Signature lines on page 35 are blank in the PDF and are represented in the Markdown as underscores; the number of underscore characters was not counted against the printed line length, as the line is a blank rule rather than text.
- No file other than this report was created or modified.
