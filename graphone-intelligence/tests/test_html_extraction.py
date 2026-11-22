from datetime import UTC, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from src.processors.freshness import is_within_24_hours, parse_verified_datetime


def test_fixture_html_extracts_article_paragraphs():
    html = (
        Path(__file__)
        .parent.joinpath("fixtures", "article.html")
        .read_text(encoding="utf-8")
    )
    soup = BeautifulSoup(html, "lxml")
    paragraphs = [
        paragraph.get_text(" ", strip=True) for paragraph in soup.select("article p")
    ]
    assert len(paragraphs) == 2
    assert "verified paragraph" in paragraphs[0]


def test_fixture_metadata_publication_date_is_verified():
    html = (
        Path(__file__)
        .parent.joinpath("fixtures", "article.html")
        .read_text(encoding="utf-8")
    )
    soup = BeautifulSoup(html, "lxml")
    value = soup.select_one('meta[property="article:published_time"]').get("content")
    parsed = parse_verified_datetime(value)
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.isoformat() == "2026-11-21T12:30:00+00:00"


def test_fixture_news_is_fresh_at_reference_time():
    now = datetime(2026, 11, 21, 13, 0, tzinfo=UTC)
    published = datetime(2026, 11, 21, 12, 30, tzinfo=UTC)
    assert is_within_24_hours(published, now=now)
