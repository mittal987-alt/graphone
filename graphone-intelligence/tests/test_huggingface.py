from src.crawlers.github import GITHUB_PATH_RE


def test_pricing_is_never_inferred():
    from src.crawlers.huggingface import HuggingFaceSpacesCrawler

    crawler = HuggingFaceSpacesCrawler()
    assert crawler.name == "Hugging Face Spaces"


def test_github_repository_path_is_extracted():
    match = GITHUB_PATH_RE.search("https://github.com/openai/openai-python")
    assert match is not None
    assert match.groups() == ("openai", "openai-python")
