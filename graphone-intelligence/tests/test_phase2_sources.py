from src.crawlers.jobs import JOB_SOURCES
from src.crawlers.news import NEWS_SOURCES


def test_five_news_sources_are_configured():
    assert len(NEWS_SOURCES) == 5
    assert all(url.startswith("http") for url in NEWS_SOURCES.values())


def test_five_job_sources_are_configured():
    assert len(JOB_SOURCES) == 5
    assert all(url.startswith("http") for url in JOB_SOURCES.values())
