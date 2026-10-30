
import datetime as dt
import hashlib
import html
import json
import os
import re
from google import genai
import sys
import urllib.request
import xml.etree.ElementTree as ET

from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

POSTS = Path(__file__).resolve().parents[1] / "_posts"
ATOM = "{http://www.w3.org/2005/Atom}"

FEEDS = [
    ("Google News India", "https://news.google.com/rss/search?q=India&hl=en-IN&gl=IN&ceid=IN:en", "India"),
    ("Google News Rajasthan", "https://news.google.com/rss/search?q=Rajasthan&hl=en-IN&gl=IN&ceid=IN:en", "Rajasthan"),
    ("Google News Technology", "https://news.google.com/rss/search?q=technology&hl=en-IN&gl=IN&ceid=IN:en", "Technology"),
    ("Google News Sports", "https://news.google.com/rss/search?q=sports&hl=en-IN&gl=IN&ceid=IN:en", "Sports"),
    ("BBC Hindi", "https://feeds.bbci.co.uk/hindi/rss.xml", "India"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "World"),
]


class Plain(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean(value):
    parser = Plain()
    try:
        parser.feed(value or "")
    except Exception:
        pass

    return re.sub(
        r"\s+", " ", html.unescape(" ".join(parser.parts))
    ).strip()


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def get_text(item, tag):
    node = item.find(tag)
    return node.text.strip() if node is not None and node.text else ""


def get_link(item):
    link = get_text(item, "link")

    if not link:
        node = item.find(f"{ATOM}link")
        if node is not None:
            link = node.attrib.get("href", "")

    return link.strip()

def get_image(item):
    # Check RSS media:content and media:thumbnail
    for tag in (
    "{http://search.yahoo.com/mrss/}content",
    "{http://search.yahoo.com/mrss/}thumbnail",
    ):
        node = item.find(tag)
        if node is not None:
            image_url = node.attrib.get("url", "")
            if image_url.startswith(("http://", "https://")):
                return image_url

    # Check image enclosure
    for node in item.findall("enclosure"):
        image_url = node.attrib.get("url", "")
        if image_url.startswith(("http://", "https://")):
            return image_url

    # Check image inside RSS description
    raw = (
        get_text(item, "description")
        or get_text(item, f"{ATOM}summary")
        or ""
    )

    match = re.search(
    r"""<img[^>]+src=["'](https?://[^"']+)["']""",
    raw,
    re.IGNORECASE
)

    if match:
        return html.unescape(match.group(1))

    return "/assets/images/news-default.svg"


def get_date(item, fallback):
    published = (
        get_text(item, "pubDate")
        or get_text(item, f"{ATOM}published")
        or get_text(item, f"{ATOM}updated")
    )

    if published:
        try:
            parsed = parsedate_to_datetime(published)

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)

            return parsed.astimezone(fallback.tzinfo)

        except Exception:
            try:
                parsed = dt.datetime.fromisoformat(
                    published.replace("Z", "+00:00")
                )

                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.timezone.utc)

                return parsed.astimezone(fallback.tzinfo)

            except Exception:
                pass

    return fallback

def generate_article(title, summary, source, link):
    api_key = os.environ.get("GEMINI")

    if not api_key or not summary:
        return None

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are a professional news editor for Today News.

Write an original, detailed news article using only the facts
available in the information below.

Rules:
- Do not copy the publisher's original article.
- Do not invent facts, statistics, quotes, or events.
- Explain the available information clearly.
- If details are missing, do not guess.
- Use simple, natural English.
- Write a headline followed by 5-7 useful paragraphs.
- Return Markdown only.

Headline: {title}
Available information: {summary}
Publisher: {source}
Original link: {link}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        article = (response.text or "").strip()
        return article if article else None

    except Exception as error:
        print(f"Gemini generation failed: {error}", file=sys.stderr)
        return None
    
    
def main():
    POSTS.mkdir(exist_ok=True)

    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    made = 0

    for source, url, category in FEEDS:
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "TodayNewsRSSBot/1.0"}
            )

            with urllib.request.urlopen(request, timeout=25) as response:
                root = ET.fromstring(response.read())

            items = (
                root.findall(".//item")
                or root.findall(f".//{ATOM}entry")
            )

            feed_made = 0

            for item in items[:12]:
                title = clean(
                    get_text(item, "title")
                    or get_text(item, f"{ATOM}title")
                )

                link = get_link(item)

                if (
                    not title
                    or not link
                    or urlparse(link).scheme not in ("http", "https")
                ):
                    continue
                CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"

                raw = (
                    get_text(item, CONTENT)
                or get_text(item, "description")
                or get_text(item, f"{ATOM}content")
                or get_text(item, f"{ATOM}summary")
                ) 

                summary = clean(raw)
                article = generate_article(
    title,
    summary,
    source,
    link
)

                date = get_date(
                    item,
                    dt.datetime.now(ist)
                )

                digest = hashlib.sha256(
                    link.encode("utf-8")
                ).hexdigest()[:10]

                slug = (
                    re.sub(r"[^a-z0-9]+", "-", title.lower())
                    .strip("-")[:60]
                    or "news"
                )

                path = POSTS / (
                    f"{date:%Y-%m-%d}-rss-{slug}-{digest}.md"
                )

                image_url = get_image(item)

                # Update image in an existing article
                if path.exists():
                    if image_url != "/assets/images/news-default.svg":
                        existing = path.read_text(encoding="utf-8")

                        existing = re.sub(
                            r'(?m)^image:.*$',
                            f"image: {quote(image_url)}",
                            existing,
                            count=1
                        )

                        path.write_text(existing, encoding="utf-8")
                        print(f"Updated image: {title}")

                    continue

                host = urlparse(link).netloc.removeprefix("www.")

                body = [
                    "---",
                    "layout: post",
                    f"title: {quote(title)}",
                    f"date: {date.strftime('%Y-%m-%d %H:%M:%S %z')}",
                    f"category: {quote(category)}",
                    'lang: "en"',
                    'author: "Today News Desk (RSS summary)"',
                    f"image: {quote(image_url)}",
                    f"source_name: {quote(source)}",
                    f"source_url: {quote(link)}",
                    "---",
                    "",
                    article or summary or "Open the original report for the full story.",
                    "",
                    f"**Original report:** [{host}]({link})",
                    "",
                    "> Short automatically generated RSS summary. "
                    "The original publisher owns the source reporting. "
                    "Visit the source for full context and updates.",
                    ""
                ]

                path.write_text(
                    "\n".join(body),
                    encoding="utf-8"
                )

                made += 1
                feed_made += 1


            print(f"{source}: {feed_made} new posts")

        except Exception as error:
            print(
                f"WARNING {source}: {error}",
                file=sys.stderr
            )

    print(f"RSS import complete. New posts: {made}")


if __name__ == "__main__":
    main()
