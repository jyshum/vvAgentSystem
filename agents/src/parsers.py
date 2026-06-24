import re
import json
from dataclasses import dataclass
from bs4 import BeautifulSoup


@dataclass
class ParsedPage:
    url: str
    title: str
    headings: list[dict]
    paragraphs: list[str]
    word_count: int
    external_links: list[str]
    schema_blocks: list[dict]
    raw_text: str
    modified_date: str | None
    last_modified_header: str | None
    status_code: int


def strip_boilerplate(soup: BeautifulSoup) -> BeautifulSoup:
    for tag in soup.find_all(["nav", "footer", "header", "aside"]):
        tag.decompose()
    for tag in soup.find_all(class_=re.compile(r"nav|footer|header|sidebar|menu", re.I)):
        tag.decompose()
    return soup


def parse_html(url: str, html: str, client_domain: str, status_code: int,
               last_modified_header: str | None = None) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    modified_date = None
    for meta_name in ["article:modified_time", "article:published_time", "date", "og:updated_time"]:
        tag = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
        if tag and tag.get("content"):
            modified_date = tag["content"]
            break
    if not modified_date:
        time_tag = soup.find("time", datetime=True)
        if time_tag:
            modified_date = time_tag["datetime"]

    schema_blocks = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            schema_blocks.append(data)
        except (json.JSONDecodeError, TypeError):
            schema_blocks.append({"_malformed": True})

    soup = strip_boilerplate(soup)

    headings = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        headings.append({"level": int(tag.name[1]), "text": tag.get_text(strip=True)})

    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]

    external_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and client_domain not in href:
            external_links.append(href)

    raw_text = soup.get_text(separator=" ", strip=True)
    word_count = len(raw_text.split())

    return ParsedPage(
        url=url,
        title=title,
        headings=headings,
        paragraphs=paragraphs,
        word_count=word_count,
        external_links=external_links,
        schema_blocks=schema_blocks,
        raw_text=raw_text,
        modified_date=modified_date,
        last_modified_header=last_modified_header,
        status_code=status_code,
    )
