import os
import re

dirs = [
    r'c:\Users\ammar\Desktop\my_github\Nexora\app\web\templates\admin\control_panel\insights',
    r'c:\Users\ammar\Desktop\my_github\Nexora\app\web\templates\admin\components'
]

unsemantic_pattern = re.compile(r'\b(badge-(?!type)[a-zA-Z0-9-]+|text-[a-zA-Z0-9-]+|bg-[a-zA-Z0-9-]+|border-[a-zA-Z0-9-]+)\b')

for d in dirs:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.html'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Replace classes inside class="..."
                def class_replacer(match):
                    classes = match.group(1)
                    new_classes = unsemantic_pattern.sub('', classes)
                    new_classes = re.sub(r'\s+', ' ', new_classes).strip()
                    return f'class="{new_classes}"' if new_classes else ''
                
                content = re.sub(r'class="([^"]+)"', class_replacer, content)
                
                # Remove inline styles entirely, except for width
                # Use a regex that matches style="..." but check if it's width
                def style_replacer(match):
                    style_content = match.group(1)
                    if 'width:' in style_content and ('color:' not in style_content and 'background:' not in style_content):
                        return f'style="{style_content}"'
                    return ''
                
                content = re.sub(r'style="([^"]+)"', style_replacer, content)
                
                # Clean empty class=""
                content = content.replace('class=""', '')
                
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
print('Done cleanup!')
