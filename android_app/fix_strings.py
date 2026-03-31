import os
import re

base_dir = r"c:\Users\user\Downloads\UDX (2) 2\UDX (2)\android_app\app\src\main\res"

for root, dirs, files in os.walk(base_dir):
    for f in files:
        if f == "strings.xml":
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            
            # fix unescaped single quotes
            content = re.sub(r"(?<!\\)'", r"\'", content)
            
            # fix random starting double quotes right after >
            content = re.sub(r'>"(.*?)</string>', r'>\1</string>', content)
            
            # fix double backslashes
            content = content.replace(r"\\'", r"\'")
            
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
print("Done fixing strings")
