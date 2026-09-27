# Step 2 — Validation report: DDS-2025-118 transcription

Source PDF: `C:\Users\HP\Desktop\INS2\invoice-auditing-level-2\drilling_services\contract\DDS-2025-118.pdf`
Transcription: `C:\Users\HP\Desktop\INS2\my_approach\output_ocr\drilling_services\`
Review date: 2026-09-27

## Result

| Status | Pages |
|---|---|
| correct | 42 |
| has errors | 0 |
| unverifiable | 0 |
| **Total** | **42** (equals the PDF page count) |

**Individual discrepancies found: 0.**

No transcription error was found on any page, including single-character checks of every figure, code, date, rate and table cell. Every suspected difference was re-inspected at higher resolution (600–900 dpi, or the native scan pixels) and in each case the Markdown reflected the visible glyphs. The suspects are listed below.

## Structural checks

- **Page count:** PyMuPDF reports 42 pages. Each page is a single greyscale JPEG (1654 × 2338 px, i.e. 200 dpi native) with no text layer.
- **Files:** Exactly `page_001.md` to `page_042.md` exist, plus `transcription_review.md`. There are no missing, extra or duplicate page files.
- **Order and numbering:** Every file's first line is `DDS-2025-118 | Directional Drilling Services` and its last non-blank line is `Page N`, where N equals the filename number. A montage of all 42 scanned headers and footers confirmed that each scan prints the same header and `Page 1` to `Page 42` in order.
- **Content placement:** Continuation tables (pages 15/16, 20/21/22, 27/28) and split clauses (pages 3/4 Clause 13, 9/10 T14, 11/12 P14) begin and end at the same rows and words as the scan. No content was moved between pages, duplicated or omitted.
- **Mechanical scan of the page files:** no `[unclear]` markers, no non-ASCII characters other than the em dash used in the scan's headings, and no double or trailing spaces.

## Method

1. Pages 1–5: full-page render at 150 dpi, plus overlapping top/middle/bottom crops at 260 dpi.
2. Pages 6–42: the text area was split into 1–4 overlapping horizontal strips rendered at 250 dpi, so body text is about 2× the size of the full-page view. Each strip was read line by line against the page file, and table cells were checked row by row with their column association.
3. Suspect glyphs were re-rendered at 600–900 dpi, or cropped from the native embedded image.
4. `transcription_review.md` was not relied on. Each of its claims was checked independently against the image.

## Suspected differences re-inspected (all resolved as "Markdown correct")

| Page | Location | Markdown | What the scan shows at high zoom | Conclusion |
|---|---|---|---|---|
| 3 | Clause 2, "Schedules 1 to 6" | `Schedules 1 to 6` | At 600 dpi the text reads "Schedules 1 to 6". The mark nearby is an isolated scan speck, like the hundreds of specks across every page. No other glyph is present. | Correct |
| 18 | Index table, 2025-09 and 2026-10 values | `104.90`, `114.70` | Specks sit near the digits. The digit shapes are unambiguous. | Correct |
| 30 | Footnote, discount figure | `-2,496.00` | At native resolution a faint grey speck sits above the decimal point, making it look like a colon at low zoom. The dark lower dot is the full-weight decimal point. | Correct (scan speck) |
| 33 | End of the intro sentence | `(Clauses 16 and R9).` | At 600 dpi: a full-weight dot with a faint grey speck below it. A true comma on the same page ("DD-120,") has a solid dark tail, which this mark lacks. | Correct (full stop) |
| 38 | Table, DD-120 effective date | `2025-07-01` | A speck touches the hyphen. The digits read 2025-07-01. | Correct |
| 39 | Rate table, row 2 code and description | `MW-301` / `MWD engineer` | At native resolution the scan prints `MW-30` + a vertical stroke + `MWD`, with no space. The stroke is cap/digit height (the same height as the `0`, lower than a Times lowercase `l` ascender). Its foot serif is merged into the left serif of `M`. The same row layout squeezes other codes against their descriptions with almost no gap (`LW-401 LWD`, `DD-101 Directional`). The glyph is the digit `1` of a code that overflows the narrow Code column. This is read from the image itself, not taken from Schedule 1. | Correct. It is a layout overlap in the source, not a character error. |
| 41 | Rate table, MW-301 row | `MW-301` / `MWD engineer` | Same overlap as page 39, with the same stroke height and merged serif (`MB-701 Mobilisation` in the next row is similarly tight). | Correct (same reasoning) |
| 41 | Rate table, MB-701 rate chargeable | `19,237.00` | At native resolution a light grey speck sits above the decimal point. The decimal point itself is the darker lower dot. | Correct (scan speck) |

## Source oddities reproduced correctly (not transcription errors)

These are features of the printed document. The page files reproduce them faithfully and should not be "fixed":

- **Truncated description cells:** page 38 (`circula`, `on stand`), page 39 (`24-hour cov`) and page 42 (`circula`, `24-hour cov`). The scan cuts these words off at the column edge, and the transcription matches.
- **Page 2:** the Contents page lists only Parts I–VII, Schedules 1–6 and Appendices A–C.
- **Page 27:** DD-102 "Directional coordinator, office based" is charged for "each day the Daily Drilling Report records the tool in the hole", as printed. This conflicts with the page 27 intro sentence, but it is the source wording.
- **Page 27:** DD-120 "each circulating or back-reaming hour" and PD-210 "each metre drilled, logged or reamed as Clauses 23 to 25 describe" are printed as shown.
- **Page 28:** HC-630 "each BHA run, as Clause 26 describes" is printed as shown.
- **Page 36:** the field-term pairings (e.g. HC-640 → "float sub", LW-410 → "gamma tool", LW-411 → "resistivity tool", LW-412 → "density-neutron", MW-320 → "survey package", PD-220 → "bit and reamer") are printed exactly so.
- **Page 37 / 42:** Amendment No. 3 is issued 2026-08-17 and effective 2026-02-01, as printed.
- **Cross-references to clauses that do not exist** (e.g. "Clause 19.3" on page 38, "Clause 19.1" on page 39, "Clause 16.4" on page 42), and page 17's reference to "Clause 3A" for Contract Years, are printed as shown.

## Page-by-page status

| Page | Content | Status | Notes |
|---|---|---|---|
| 1 | Title, parties, key terms table | correct | |
| 2 | Contents | correct | 16 rows, 3 columns checked |
| 3 | Part I, Clauses 1–13 heading | correct | Clause 2 "Schedules 1 to 6" confirmed at 600 dpi |
| 4 | Clause 13 continued, Clause 14 | correct | |
| 5 | Part II, Clauses 15–16 | correct | |
| 6 | Part III, Clauses 17–25 | correct | |
| 7 | Clauses 26–31 | correct | |
| 8 | Part IV, Clauses 32–42 | correct | |
| 9 | Part V, T1–T14 heading | correct | |
| 10 | T14 continued, T15–T16 | correct | |
| 11 | Part VI, P1–P14 heading | correct | |
| 12 | P14 continued | correct | |
| 13 | Part VII, H1–H12 | correct | |
| 14 | Part VIII, R1–R12 | correct | |
| 15 | Schedule 1, Series 100–400 | correct | 22 rows; all rates checked digit by digit |
| 16 | Schedule 1, LW-430 and Series 500–700 | correct | 16 rows |
| 17 | Schedule 2 depth bands, Part 2 volume bands | correct | |
| 18 | Schedule 2C, index table | correct | 2 + 24 values; row/column pairing checked |
| 19 | Schedule 2D, SAR values and exchange table | correct | 4 + 24 values |
| 20 | Schedule 3 Parts 1–3 (start) | correct | Factors and 15 standby rows |
| 21 | Schedule 3 Part 3 cont., Parts 4–5 | correct | 14 + 15 rows |
| 22 | Schedule 3 Part 5 cont., Parts 6–7 | correct | |
| 23 | Schedule 4 | correct | |
| 24 | Schedule 5 | correct | 5 + 12 rows |
| 25 | Schedule 6 | correct | |
| 26 | Schedule 7 tool specifications | correct | 20 rows × 5 columns; wrapped names re-joined correctly |
| 27 | Schedule 8 (DD-101 to LW-410) | correct | 18 rows |
| 28 | Schedule 8 (LW-411 to LH-714) | correct | 20 rows |
| 29 | Appendix A | correct | |
| 30 | Appendix B form of invoice | correct | 5 rows × 8 columns and totals; footnote `-2,496.00` confirmed |
| 31 | Appendix C, Execution | correct | |
| 32 | Appendix D | correct | |
| 33 | Appendix E | correct | Final full stop confirmed |
| 34 | Appendix F | correct | |
| 35 | Part IX, 3A–36A | correct | |
| 36 | Appendix G | correct | 24 rows |
| 37 | Schedule of Variations | correct | 5 instruments; all issued and effective dates checked |
| 38 | Supplement No. 1 | correct | Truncated descriptions reproduced as printed |
| 39 | Amendment No. 1 | correct | `MW-30lMWD` glyph read as code `MW-301`; see above |
| 40 | Supplement No. 2 | correct | 9 monthly rates, 5 discount rows |
| 41 | Amendment No. 2 | correct | `MW-30lMWD` as page 39; `19,237.00` confirmed |
| 42 | Amendment No. 3 | correct | |

## Review limits

- Pages 1–5 were compared at 150 dpi (full page) and 260 dpi (crops). Pages 6–42 were compared at 250 dpi strips. The native scan is 200 dpi, so higher renders add magnification but no new detail. Every page's full visible content was read against its file. No page was only skimmed.
- The review was a visual comparison by one reviewer. It was not an independent OCR diff. A visual read can in principle miss a transposition that forms a plausible word or number. To limit this, every number, code and date was compared character by character, not just read for sense.
- For the `MW-30lMWD` cells on pages 39 and 41, the reading of the fused stroke as the digit `1` rests on its height and on the column-overflow pattern of neighbouring rows. If the exact printed glyphs matter legally, a human should confirm against the original paper document.
- `transcription_review.md` was not validated as a page file. Its factual claims about the source were checked and found accurate. The "stray mark" in its item 6 (page 3) is ordinary scan noise.
