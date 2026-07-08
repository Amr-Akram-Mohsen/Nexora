import os
import re

def process_dir(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Match {% extends "base.html" %} or {% extends 'base.html' %} or {% extends"base.html" %}
                new_content = re.sub(r'\{%\s*extends\s*[\'"]base\.html[\'"]\s*%\}', '{% extends "layout/base.html" %}', content)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {path}")

process_dir('app/web/templates/public')
process_dir('app/web/templates/auth')
process_dir('app/web/templates/components')
process_dir('app/web/templates/admin/layout')
