import os

from openai import OpenAI

from src.retry import with_retries


MODEL = "sonar"


@with_retries()
def query(prompt: str) -> str:
    client = OpenAI(
        api_key=os.environ["PERPLEXITY_API_KEY"],
        base_url="https://api.perplexity.ai",
        timeout=30.0,
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
