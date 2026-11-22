from src.llm.chunking import chunk_text, estimate_tokens


def test_chunking_respects_maximum_and_overlap():
    text = "\n\n".join(
        f"This is paragraph {index} with enough source text." for index in range(30)
    )
    chunks = chunk_text(text, max_tokens=100, overlap_tokens=10)
    assert chunks
    assert all(chunk.estimated_tokens <= 100 for chunk in chunks)
    assert any(chunk.metadata["end_char"] > 0 for chunk in chunks)


def test_empty_document_returns_no_chunks():
    assert chunk_text("", max_tokens=100) == []


def test_token_estimate_is_bounded():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100
