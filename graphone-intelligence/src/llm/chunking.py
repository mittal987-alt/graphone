from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    estimated_tokens: int
    metadata: dict[str, int]


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def chunk_text(
    text: str,
    *,
    max_tokens: int,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    overlap_tokens = min(max(overlap_tokens, 0), max_tokens - 1)
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary == -1:
                boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start:
                end = boundary + 2

        chunk_text_value = text[start:end].strip()
        if chunk_text_value:
            chunks.append(
                Chunk(
                    index=index,
                    text=chunk_text_value,
                    estimated_tokens=estimate_tokens(chunk_text_value),
                    metadata={
                        "start_char": start,
                        "end_char": end,
                    },
                )
            )
            index += 1

        if end >= len(text):
            break
        start = max(start + 1, end - overlap_chars)

    return chunks
