import os
import re

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    # Only rename ItemClick → ProductClick and item_store_link_id → product_store_link_id
    content = content.replace("ItemClick", "ProductClick")
    content = content.replace("item_store_link_id", "product_store_link_id")
    content = content.replace("item_store_link", "product_store_link")

    if original != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def process_directory(directory):
    count = 0
    for root, _, files in os.walk(directory):
        if "migrations" in root or ".gemini" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if replace_in_file(filepath):
                    print(f"Updated: {filepath}")
                    count += 1
    return count

if __name__ == "__main__":
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app"))
    c1 = process_directory(app_dir)
    print(f"Total files updated: {c1}")
