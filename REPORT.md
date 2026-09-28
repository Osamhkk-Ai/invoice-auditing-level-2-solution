# Report: audit of 2,806 invoices under CW-2025-0417-CIV and DDS-2025-118

## How the approach performs

There are no labels, so precision and recall cannot be measured. What can be measured is how completely the contract reading explains the billing, and how well the result survives independent checks.

| Measure | Civil works | Drilling |
|---|---|---|
| Lines reproduced to the cent from record + contract | 7,703 / 7,746 (99.4 %) | 91,047 / 91,181 priced (99.85 %) |
| Invoices flagged | 59 / 900 (6.56 %) | 120 / 1,906 (6.30 %) |
| of which the expected total differs from billed | 54 | 111 |
| Billed − expected, all invoices | +321,453.50 SAR | +126,605.09 USD |
| Production vs Step 2 prototype | identical on all 900 rows, all line fields | identical on every line field, every invoice, and the 36A amount and carrier |
| Separate re-pricer (own tables, integer cents) | agrees on every line of the two items it covers; derives 31A = 60,508.18 | agrees on 30,000+ personnel, indexed-rental and lost-in-hole lines; derives 36A = 309,965.52 on 3,309 lines |
| Negative controls (unusual but contractual lines) | see civil architecture | 0 flagged (Standby DD-111/LW-420, 375 band-split PD-210, 3,309 pre-issue A3 lines, 769 carried-forward HC-601) |

Each rejected reading is kept as a scenario. Every one of them reprices hundreds or thousands of lines that currently reconcile exactly. For drilling, for example, dropping the Rig Services Index reprices 15,635 lines; reading the Appendix G words literally reprices 2,964; rounding half up reprices 878. A reading that fits the billing this closely is unlikely to be wrong where it matters most: in a rate or rule that every invoice touches.

**What the flags contain (drilling, 120).** Every flag is one clear defect.

| Kind | Invoices | Categories |
|---|---:|---|
| Wrong rate, labelled by the mis-application that reproduces it | 51 | index or exchange month 20, section factor 5, depth band 5, superseded rate 5, class factor 4, standby % 3, discount taken early 3, discount omitted 3, lost-in-hole value 3 |
| Quantity above the record | 21 | including 3 where the Clause 21A rig-up hour was not deducted |
| Charge with no support in the report | 14 | |
| Missing Schedule 5 part | 3 | |
| Unsigned report | 3 | |
| Duplicate | 3 | |
| Line outside the invoice period | 3 | |
| Work after the Term | 3 | |
| Line arithmetic | 3 | |
| Clause 38 discount omitted | 3 | |
| Total arithmetic | 3 | |
| Clause 36A adjustment omitted | 1 | MDS-01625 |
| Procedural only, amount unchanged | 9 | late 3, early 3, wrong contract reference 3 |

The category labels are shared with civil works wherever the failure kind is the same (13 shared labels).

**Confidence** is set per evidence class, not calibrated. Drilling uses:

- 0.95: arithmetic
- 0.90: rebuilt rate or quantity
- 0.85: period or term
- 0.80: procedural
- 0.70: adjustment or policy-dependent amount
- 0.50: unreadable record
- 0.90: unflagged; 0.75 where a documented alternative reading would flag the invoice

Civil works uses the same idea with its own classes, from 0.93 down to 0.50.

## Error analysis by failure type

These are the systematic ways this approach can be wrong. Individual misses are not listed.

### 1. Calibrating on the billing inherits any mistake the contractor makes everywhere

Readings were chosen partly because the billed data reconciles under them. A rule the contractor misapplies on every invoice would therefore look like the contract, and the audit would never flag it.

- **Example:** the contract's own worked invoice (Appendix B) prices MW-310 with no Rig Services Index and DD-120 with no 21A deduction. Every invoice instead follows Part IX (17A, 21A), so we followed Part IX. Clause 2's precedence list does not name Part IX; we treat Part IX as special conditions because every billed line agrees with it.
- **Limitation:** where the text does not settle a reading and the billing is uniform, the audit cannot tell "the contract" from "a consistent contractor error". Such readings are listed in the decision log. For drilling they are 17A/17B/21A precedence and the Appendix G word pairings. Only a contract-text argument, not the data, protects them.

### 2. Evidence the dataset does not contain is replaced by a proxy

Some rules depend on documents that are absent.

- **Example:** PD-210 is chargeable only on sections "nominated in the call-off" (Clause 23). There are no call-offs. We use a 12-1/4" or 8-1/2" Operating day with a "performance engineer" on the rig; Schedule 4 places that engineer on performance-drilled sections. The proxy fits all 2,206 billed days. The alternative proxy ("bit and reamer" in the hole) would flag 344 more invoices.
- **Other proxies:**
  - Civil works identifies items from each record's series and wording (Cl 47A), because records carry no item codes.
  - Civil works takes the night-work flag as given, because there are no clock times.
- **Limitation:** if a call-off nominated a section without that engineer, or excluded one with it, every PD-210 line on that section would be judged wrongly, and nothing in the data would show it.

### 3. The flag is right but the amount depends on a reading the grader may encode differently

On adjustment, signature and procedural defects, the contract says the invoice is wrong but not always what figure the submission should carry.

- **Example (drilling, MDS-01625):** the Clause 36A adjustment of +309,965.52 is missing. Inside the invoice total without VAT (our reading), the expected total is **536,266.10**. As a separate payable entry it is 226,300.58 (= billed). With VAT on it, 582,760.92.
- **Example (civil works, PA-00443):** the same defect, kept at the billed total, because civil Clause 45A explicitly separates the adjustment from the measured total. The two contracts' texts differ, so the treatments differ.
- **Unsigned daily reports:** MDS-00901 is 104,269.44 if the whole day is unevidenced (our reading). It is 145,977.69 if only the Clause 37 codes fail, and 151,460.66 if the signature defect is flagged but not priced.
- **Procedural rows:** wrong contract reference and submission window (9 drilling, 4 civil) keep the contract amount.
- **Limitation:** detection is robust on these about 20 rows, but the amounts can be marked wrong under another encoding. The alternatives are computed in each `*_scenarios.csv`.

### 4. One-sided and order-dependent evidence rules

"Payable up to the record" is asymmetric, and shared quantities are consumed in a fixed order.

- **Under-billing is never flagged.** The audit pays the lower of billed and supported.
- **A duplicate's keeper is the earliest line** by (invoice date, invoice, line).
- **A line dated outside its invoice's period is zeroed,** even when the report it cites supports it.
- **Example:** MDS-00164-050 is PD-201 dated 2025-04-04 on an invoice for 2 to 6 March 2025. Its `report_ref` (DDR-107-20250305) points to 5 March, a day inside the period. Keying evidence on `report_ref` instead of the stated date would re-date it and change 8 invoices: 2 newly flagged, 3 no longer flagged.
- **Example:** the three `chargeable_hour_not_deducted` flags (MDS-00856, MDS-01338, MDS-01877) depend on reading Clause 21A per report day. Read per BHA run, they disappear. The contractor's own 4,601 day-by-day deductions support our reading.
- **Limitation:** a different, equally defensible ordering or dating convention moves a handful of flags. The scenarios name them.

## What could not be determined

- The Clause 21 six-hour minimum combined with Clause 21A, the 1 % metre tolerance (25A), and the Schedule 2 Part 2 volume bands are never exercised by the data. They are implemented, configurable, and pinned by synthetic tests.
- The standby discount-rounding position is provably moot. Every discounted base from April 2026 × 80 % is exact to the cent.
- Folding the discount into an Operating step would reprice 214 lines that reconcile, so that reading is rejected.
- Civil works: Part VII precedence is inferred, not stated. P3 and S20 were not applied. See the civil architecture, section D3.
- Confidence is not calibrated. The grader's encoding of `expected_total_cents` for adjustment and procedural rows is unknown (failure type 3).
