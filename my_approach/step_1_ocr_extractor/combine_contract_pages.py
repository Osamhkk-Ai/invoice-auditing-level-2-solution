"""Combine the validated civil contract page transcriptions without rewriting them."""

from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output_step_1" / "civilwork"
COMBINED_FILE = OUTPUT_DIR / "civilwork_contract_combined.md"
EXPECTED_PAGES = 43


def main() -> None:
    pages = sorted(OUTPUT_DIR.glob("page_*.md"))
    expected_names = [f"page_{number:03d}.md" for number in range(1, EXPECTED_PAGES + 1)]
    actual_names = [page.name for page in pages]
    if actual_names != expected_names:
        raise ValueError(f"Expected {expected_names}, found {actual_names}")

    sections = []
    for number, page in enumerate(pages, start=1):
        sections.append(f"<!-- PDF page {number:03d}: {page.name} -->\n\n")
        sections.append(page.read_text(encoding="utf-8").rstrip() + "\n\n")
    COMBINED_FILE.write_text("".join(sections), encoding="utf-8")
    print(f"Combined {len(pages)} pages into {COMBINED_FILE}")


if __name__ == "__main__":
    main()
