import os
import re
import sys

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. Imports and specific long strings
    content = content.replace("app.domains.product", "app.domains.product")
    content = content.replace("app/domains/product", "app/domains/product")
    content = content.replace("ProductVariant", "ProductVariant")
    content = content.replace("ProductImage", "ProductImage")
    content = content.replace("ProductStoreLink", "ProductStoreLink")
    content = content.replace("ProductSpecification", "ProductSpecification")
    content = content.replace("Product Click", "Product Click")
    content = content.replace("Product View", "Product View")
    content = content.replace("product_id", "product_id")
    content = content.replace("product_type", "product_type")
    content = content.replace("product_links", "product_links")
    content = content.replace("product_images", "product_images")
    content = content.replace("product_variants", "product_variants")
    content = content.replace("product_store_links", "product_store_links")
    content = content.replace("product_specifications", "product_specifications")
    content = content.replace("content_products", "content_products")
    content = content.replace("product_library", "product_library")
    content = content.replace("product_row", "product_row")
    
    # 2. 'Product' (word boundary)
    content = re.sub(r'\bItem\b', 'Product', content)
    
    # 3. 'products' (word boundary, negative lookahead for parenthesis to avoid .items())
    # We replace 'products' with 'products' UNLESS it is followed by '('
    content = re.sub(r'\bitems\b(?!\s*\()', 'products', content)
    
    # 4. 'product' (word boundary)
    content = re.sub(r'\bitem\b', 'product', content)

    # 5. 'PRODUCTS' (word boundary)
    content = re.sub(r'\bITEMS\b', 'PRODUCTS', content)

    # 6. 'PRODUCT' (word boundary)
    content = re.sub(r'\bITEM\b', 'PRODUCT', content)

    if original != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def process_directory(directory):
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.py', '.html', '.js', '.css', '.json', '.md')):
                # Skip backup script and migration files since they may contain old schema refs
                if "backup_products.py" in file or "alembic" in root or "migrations" in root or ".gemini" in root:
                    continue
                filepath = os.path.join(root, file)
                if replace_in_file(filepath):
                    print(f"Updated: {filepath}")
                    count += 1
    return count

if __name__ == "__main__":
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app"))
    scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts"))
    
    c1 = process_directory(app_dir)
    c2 = process_directory(scripts_dir)
    print(f"Total files updated: {c1 + c2}")
