import re
from collections import defaultdict

css_file = r'c:\Users\ammar\Desktop\my_github\Nexora\app\web\static\css\style.css'

with open(css_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Simple regex to find selectors. This won't be perfect but good enough for finding duplicates.
# It looks for things like .class { or #id { at the start of lines or after whitespace
selectors = re.findall(r'^([^{]+)\{', content, re.MULTILINE)

selector_counts = defaultdict(list)
for i, selector in enumerate(selectors):
    # Clean up selector (trim whitespace, remove newlines)
    clean_selector = selector.strip()
    if clean_selector:
        selector_counts[clean_selector].append(i)

# Find duplicates
duplicates = {s: lines for s, lines in selector_counts.items() if len(lines) > 1}

# Print top duplicates
print("Top Duplicated Selectors:")
for selector, occurrences in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:50]:
    print(f"{len(occurrences)} occurrences: {selector}")

# Check for large blocks that might be overrides
# We'll just look for specific sections that might be repeating
sections = re.findall(r'/\* (Start|End) .* Styles \*/', content)
print("\nSection Markers Found:")
for section in sections[:20]:
    print(section)
