import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
print(f"DATABASE_URL: {db_url}")
print(f"Length: {len(db_url)}")
for i, char in enumerate(db_url):
    print(f"{i}: {char} ({ord(char)})")
