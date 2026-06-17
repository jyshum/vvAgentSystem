import os

from openai import OpenAI

from src.retry import with_retries


MODEL = "gpt-4o-mini"


@with_retries()
def query(prompt: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=30.0)
    response = client.responses.create(
        model=MODEL,
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    return response.output_text
