"""A polite web scraper for books.toscrape.com.

Practices:
- Checks robots.txt before scraping
- Identifies itself with a custom User-Agent
- Rate-limits requests (1 second delay between pages)
- Handles network errors and broken pages gracefully
- Validates every record against a Pydantic schema
- Cleans raw strings (e.g. "£51.77" → 51.77) during parsing
"""

import json
import time
import urllib.robotparser
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from schemas import Book

BASE_URL = "https://books.toscrape.com"
USER_AGENT = "Mozilla/5.0 (compatible; ArtificiallBot/1.0; +https://github.com/PawelPikulik/Artificiall)"
REQUEST_DELAY = 1.0  # seconds between requests
TIMEOUT = 10  # seconds per request
MAX_RETRIES = 3


def can_fetch(url: str) -> bool:
    """Check robots.txt before hitting a URL."""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{BASE_URL}/robots.txt")
    try:
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        # If robots.txt is missing (404) we treat it as permissive
        # but still log the caution.
        return True


def fetch_page(url: str) -> Optional[str]:
    """Fetch a single page with retries, custom headers, and timeouts."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            print(f"  Attempt {attempt}/{MAX_RETRIES} failed for {url}: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * attempt)
    return None


def parse_star_rating(css_class: str) -> int:
    """Map CSS class like 'star-rating Three' to integer 3."""
    word = css_class.replace("star-rating", "").strip()
    mapping = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5,
    }
    return mapping.get(word, 0)


def parse_book(article) -> Optional[Book]:
    """Extract a single book from an <article> tag and validate it."""
    try:
        title_tag = article.find("h3").find("a")
        title = title_tag.get("title", "").strip()
        href = title_tag.get("href", "")

        # Fix relative URLs
        if href.startswith("../../"):
            href = f"{BASE_URL}/catalogue/{href.replace('../../', '')}"
        elif href.startswith("../"):
            href = f"{BASE_URL}/catalogue/{href.replace('../', '')}"
        elif not href.startswith("http"):
            href = f"{BASE_URL}/{href}"

        price_text = article.find("p", class_="price_color").text.strip()
        availability = article.find("p", class_="instock availability").text.strip()
        rating_class = article.find("p", class_="star-rating")["class"]
        rating = parse_star_rating(" ".join(rating_class))

        image_tag = article.find("img")
        image_url = None
        if image_tag:
            raw_src = image_tag.get("src", "")
            if raw_src.startswith("../../"):
                image_url = f"{BASE_URL}/{raw_src.replace('../../', '')}"
            elif not raw_src.startswith("http"):
                image_url = f"{BASE_URL}/{raw_src}"
            else:
                image_url = raw_src

        return Book(
            title=title,
            price=price_text,
            availability=availability,
            rating=rating,
            url=href,
            image_url=image_url,
        )
    except Exception as exc:
        print(f"  Failed to parse a book card: {exc}")
        return None


def scrape_page(page_url: str) -> List[Book]:
    """Scrape one listing page and return validated Book objects."""
    print(f"Fetching {page_url} ...")
    if not can_fetch(page_url):
        print(f"  robots.txt disallows {page_url}")
        return []

    html = fetch_page(page_url)
    if html is None:
        print(f"  Giving up on {page_url}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="product_pod")

    books: List[Book] = []
    for article in articles:
        book = parse_book(article)
        if book:
            books.append(book)

    print(f"  → {len(books)} books parsed")
    return books


def scrape_all(max_pages: int = 3) -> List[Book]:
    """Scrape up to *max_pages* listing pages politely."""
    all_books: List[Book] = []
    page = 1

    while page <= max_pages:
        if page == 1:
            url = f"{BASE_URL}/index.html"
        else:
            url = f"{BASE_URL}/catalogue/page-{page}.html"

        books = scrape_page(url)
        if not books:
            # A broken / empty page means we reached the end.
            break

        all_books.extend(books)
        page += 1

        if page <= max_pages:
            time.sleep(REQUEST_DELAY)

    return all_books


def save_json(books: List[Book], path: str = "books.json") -> None:
    """Dump validated books to a pretty-printed JSON file."""
    data = [book.model_dump() for book in books]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} books to {path}")


if __name__ == "__main__":
    print("Starting polite scraper ...")
    print(f"User-Agent: {USER_AGENT}")
    print(f"Request delay: {REQUEST_DELAY}s")
    print()

    books = scrape_all(max_pages=3)
    save_json(books)

    print()
    print(f"Total books collected: {len(books)}")
