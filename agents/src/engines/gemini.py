import os

from google import genai
from google.genai import types

from src.retry import with_retries


MODEL = "gemini-2.5-flash"


@with_retries()
def query(prompt: str) -> str:
    # Timeout in milliseconds. Without it a stalled Gemini request (its Google
    # Search grounding occasionally hangs) blocks forever and freezes the whole
    # tracker run; the other engines all cap at 30s, so match them.
    client = genai.Client(
        api_key=os.environ["GOOGLE_GEMINI_API_KEY"],
        http_options=types.HttpOptions(timeout=30_000),
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return response.text
