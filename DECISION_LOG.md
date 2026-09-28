# Decision log

Each entry gives the ambiguity, the reading used in `submission.csv`, the rows it affects, and what the alternative does. Money is in minor units, as in the submission. Every alternative can be run from `drilling_scenarios.csv`, `civilwork_scenarios.csv` or the config switches.

## Drilling services (DDS-2025-118)

| # | Ambiguity | Reading used | Rows | Alternative and its effect |
|---|---|---|---|---|
| D1 | Carrier of the Amendment No. 3 adjustment. Cl 36A says "first invoice submitted **on or after** the date of issue"; A3 says "**after** (Clause 36A)". | On or after → **MDS-01625**, the only invoice dated 2026-08-17. It is the only reading that yields a single "first" invoice, and A3 itself defers to 36A. | MDS-01625 | Strictly after gives a three-way tie on 2026-08-18 (MDS-01585, MDS-01631, MDS-01645) with no contractual tie-break. The flag and +30,996,552 move to the chosen invoice. The three are unflagged at confidence 0.75. |
| D2 | Is the adjustment part of the audited `invoice_total`, and does it bear VAT? Cl 40: total = net + VAT; Cl 36A: "shown as a single adjustment" on the invoice. | **Inside the total, no VAT** (owner's working choice). It is not a charge, so it is outside net (Cl 36) and outside VAT (Cl 39). It is payable only through the invoice (Cl 42); drilling has no civil-style Cl 45A that separates it. | MDS-01625: 53,626,610 (billed 22,630,058) | Separate entry → 22,630,058, still flagged. VAT on it → 58,276,092. Measured on billed instead of supported quantity → identical. |
| D3 | Unsigned Daily Drilling Report. Cl 15 requires both signatures; Cl 37 makes only the Schedule 5 codes conditional. | **No charge on that day** (Cl 15 and guideline checks 2 and 4). 33 lines. | MDS-00340 → 9,215,157; MDS-00842 → 4,942,549; MDS-00901 → 10,426,944 | Cl 37 codes only → 10,356,447 / 6,047,284 / 14,597,769. Flag only → billed totals (…/…/15,146,066). All three stay flagged either way. |
| D4 | PD-210 only "on the performance-drilled sections nominated in the call-off"; no call-offs are in the data. | **Proxy:** a 12-1/4" or 8-1/2" Operating day with a "performance engineer" (PD-201) on the rig. Fits all 2,206 billed days. | every PD-210 line | Every such day → no billed line changes (it only adds unbilled supply). "Bit and reamer" in the hole → 1,261 lines and 367 totals change; rejected. |
| D5 | Part IX (17A index, 17B factors, 21A, 25A, 31A, 36A) is absent from Cl 2's precedence list. | **Part IX governs** as special conditions. | all lines | Clause 18 literal (section factor on Standby) → 402 lines. Class factor on PD-210 → 940. No index → 15,635. Schedule 6 USD for lost in hole → 47. All rejected. |
| D6 | Instruments "read in the order issued": does A3's flat DD-120 rate beat S2's monthly rates from April 2026? | **Later issued governs**: A3 416.00. | DD-120 on post-issue invoices | Latest effective date governs → 778 lines, 213 totals; rejected. |
| D7 | Cl 21A: "the first hour of each period in the hole". | **Each report day.** The contractor deducts it on 4,601 days. | 3 flags: MDS-00856, MDS-01338, MDS-01877 | Once per BHA run → those 3 are no longer flagged, 7 totals change. Minimum 6 h before or after 21A: no case in the data; tested synthetically. |
| D8 | Evidence day: the line's stated date or its `report_ref` date (8 lines disagree). | **Stated date** (Cl 32 and 34); a `report_ref` mismatch is a warning. | MDS-00128, MDS-01352 unflagged (0.75); MDS-00164, MDS-00541, MDS-00895 flagged | `report_ref` date → those 5 swap and 8 totals change. |
| D9 | Wrong contract reference or submission outside Cl 33's window. | **Flag, keep the contract amount.** | 9 invoices | Reject the invoice → expected 0 on 3 to 9 rows. |
| D10 | Appendix B (worked invoice) contradicts Part IX: no index, no 21A. | **Illustrative only.** | — | Dropping the index as Appendix B does reprices 15,635 lines. Without 21A, the one-hour deduction the contractor makes on 4,601 days would be unexplained. |
| D11 | Never exercised by the data: the Cl 21 minimum × 21A; the 25A 1 % tolerance; Sch. 2 Pt 2 volume bands; discount rounding on Standby. | Implemented and configurable; synthetic tests pin them down. | none | The Standby rounding position is provably moot (base × 80 % is exact). Folding the discount into an Operating step reprices 214 lines; rejected. |
| D12 | Category vocabulary. | **Shared with civil works** where the kind is the same (13 labels). Wrong rates are labelled by the mechanism that reproduces the billed rate. The retroactive adjustment is named after each contract's own clause (`adjustment_31A_omitted` / `adjustment_36A_omitted`). | 179 flagged rows | — |

## Civil works (CW-2025-0417-CIV)

These are the owner's decisions of 2026-09-27; details are in the civil architecture, Part D.

| # | Ambiguity | Reading used | Alternative and its effect |
|---|---|---|---|
| C1 | Carrier of the 31A adjustment: "on or after" (Cl 31A) vs "after" (A3). Three applications fall on the issue date. | **PA-00443**, the only application strictly after. Kept outside `application_total` by Cl 45A, so the total is unchanged. | PA-00006, PA-00023 or PA-00380 → one flag swapped; all four at low confidence → 62 flags. |
| C2 | A repeated dewatering week with different dates (Cl 44 keys on the date). | **Not a duplicate.** | Within one application → 61 flags; all A.16.010 → 77; plus E.54.010 → 94. |
| C3 | Amount for procedural defects, and work after submission. | **Flag and value the supported lines.** Work after submission is 0 (PA-00125). | Zero every procedural total → 6 totals, −111,066,624. |

**Shared principle behind D1 and C1.** Both contracts pair "on or after" in the clause with "after" in the amendment. In both, the reading used is the one that yields a single first carrier. For drilling that is on or after (MDS-01625); for civil works it is after (PA-00443).
