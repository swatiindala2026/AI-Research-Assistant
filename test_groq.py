
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load .env from the project folder
env_path = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=env_path, override=True)

api_key = os.getenv("GROQ_API_KEY")

print("ENV file exists:", env_path.exists())
print("API key loaded:", bool(api_key))
print("API key length:", len(api_key) if api_key else 0)
print("API key starts correctly:", api_key.startswith("gsk_") if api_key else False)

if not api_key:
    print("Please check your .env file.")
else:
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        messages=[{"role": "user", "content": "Say Hello"}]
    )

    print("Groq Response:", response.choices[0].message.content)
