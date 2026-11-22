from src.resolution.resolver import EntityResolver, normalize_name
from src.resolution.seeds import AI_STARTUP_SEEDS


def test_seed_database_contains_50_startups():
    assert len(AI_STARTUP_SEEDS) == 50


def test_normalization_removes_suffixes_and_punctuation():
    assert normalize_name("OpenAI, Inc.") == "openai"


def test_exact_match_resolves_openai():
    result = EntityResolver().resolve("Open AI")
    assert result.canonical_name == "OpenAI"
    assert result.match_method == "alias"
    assert result.confidence == 1.0


def test_alias_match_resolves_anthropic():
    result = EntityResolver().resolve("Anthropic AI")
    assert result.canonical_name == "Anthropic"
    assert result.match_method == "alias"


def test_unrelated_high_similarity_stays_unmatched():
    result = EntityResolver().resolve("Plai")
    assert result.match_method == "unmatched"
    assert result.canonical_name is None


def test_fuzzy_match_requires_high_threshold():
    resolver = EntityResolver(
        [
            ("Example Artificial Intelligence", ["Example AI"]),
            ("OpenAI", ["Open AI"]),
        ]
    )
    result = resolver.resolve("Example Artificial Inteligence")
    assert result.match_method == "fuzzy"
    assert result.canonical_name == "Example Artificial Intelligence"
    assert result.confidence >= 0.96
