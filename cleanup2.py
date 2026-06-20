import os
import re

dirs = [
    r'c:\Users\ammar\Desktop\my_github\Nexora\app\web\templates\admin\control_panel\insights',
    r'c:\Users\ammar\Desktop\my_github\Nexora\app\web\templates\admin\components'
]

for d in dirs:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.html'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                original_content = content
                
                # Fix display_
                content = re.sub(r'\bdisplay_([,\)\s\n\>])', r'display_style="none"\1', content)
                
                # Fix header_, extra_, input_, body_, wrapper_
                content = re.sub(r'\b(header|extra|input|body|wrapper)_([,\)\s\n\>])', r'\1_class=""\2', content)
                
                if content != original_content:
                    print(f'Fixed {f}')
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(content)

print("All done!")
