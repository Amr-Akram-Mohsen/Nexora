import os
import re
import glob

def remove_image_alt_text(md_text):
    """
    Finds Markdown images ![Alt Text](URL) and removes the Alt Text,
    resulting in ![](URL)
    """
    # Regex explanation:
    # \!\[        - Matches literal "!["
    # (.*?)       - Matches the alt text (non-greedy)
    # \]          - Matches literal "]"
    # \((.*?)\)   - Matches the URL inside parentheses
    return re.sub(r'\!\[.*?\]\((.*?)\)', r'![](\1)', md_text)

def remove_wikipedia_citations(md_text):
    """
    Finds Wikipedia citations like [\[448\]](URL) or [448] and removes them.
    """
    # Matches the specific format Firecrawl outputs for Wiki links: [\[123\]](url)
    md_text = re.sub(r'\[\\?\[\d+\\?\]\]\([^\)]+\)', '', md_text)
    
    # Matches standard [123] citations just in case
    md_text = re.sub(r'\[\d+\]', '', md_text)
    
    return md_text

def clean_excessive_newlines(md_text):
    """
    Replaces 3 or more consecutive newlines with just 2 newlines.
    """
    return re.sub(r'\n{3,}', '\n\n', md_text)

def clean_markdown_file(filepath):
    print(f"Cleaning {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Apply cleaning steps
    content = remove_image_alt_text(content)
    content = remove_wikipedia_citations(content)
    content = clean_excessive_newlines(content)
    
    # Write the cleaned content to a new file
    clean_filepath = filepath.replace('.md', '_cleaned.md')
    with open(clean_filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved cleaned file to {clean_filepath}")

def run_cleaner():
    # Find all generated markdown files in scraper_tests
    # that haven't been cleaned yet
    test_files = glob.glob('scraper_tests/*.md')
    for filepath in test_files:
        if not filepath.endswith('_cleaned.md'):
            clean_markdown_file(filepath)

if __name__ == "__main__":
    run_cleaner()
