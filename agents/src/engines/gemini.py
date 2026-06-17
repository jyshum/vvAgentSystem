import os

from google import genai
from google.genai import types

from src.retry import with_retries


MODEL = "gemini-2.5-flash"


@with_retries()
def query(prompt: str) -> str:
    client = genai.Client(api_key=os.environ["GOOGLE_GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return response.text
