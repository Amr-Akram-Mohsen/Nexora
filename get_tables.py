import re
from pathlib import Path

# Change these if needed
ADMIN_TEMPLATES_DIR = Path("app/web/templates/admin")
OUTPUT_FILE = Path("extracted_tables.txt")

TABLE_PATTERN = re.compile(
    r"<table\b[^>]*>.*?</table>",
    re.IGNORECASE | re.DOTALL
)


def extract_tables():
    results = []

    for file_path in sorted(ADMIN_TEMPLATES_DIR.rglob("*")):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in {".html", ".jinja", ".jinja2"}:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Skipped {file_path}: {e}")
            continue

        tables = TABLE_PATTERN.findall(content)

        if not tables:
            continue

        for index, table in enumerate(tables, start=1):
            results.append(
                "\n"
                + "=" * 120
                + "\n"
                + f"FILE: {file_path}\n"
                + f"TABLE #{index}\n"
                + "=" * 120
                + "\n\n"
                + table
                + "\n"
            )

    OUTPUT_FILE.write_text(
        "\n".join(results),
        encoding="utf-8"
    )

    print(f"Extracted {len(results)} tables to {OUTPUT_FILE}")


if __name__ == "__main__":
    extract_tables()
