from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "architecture.pdf"


def build() -> None:
    styles = getSampleStyleSheet()
    title = styles["Title"]
    heading = styles["Heading2"]
    body = styles["BodyText"]
    body.fontName = "Helvetica"
    body.leading = 12

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="GraphOne Intelligence Architecture",
        author="GraphOne Intelligence",
    )
    story = []

    story.append(Paragraph("GraphOne Intelligence", title))
    story.append(Paragraph("Production architecture brief", heading))
    story.append(Spacer(1, 0.15 * inch))
    story.append(
        Paragraph(
            "Traceable AI startup, product, paper, news, and job intelligence "
            "with PostgreSQL authority, Redis coordination, bounded async crawling, "
            "deterministic entity resolution, and provider-independent LLM extraction.",
            body,
        )
    )
    story.append(Spacer(1, 0.12 * inch))
    flow = [
        ["Source adapters", "Async crawling", "Pydantic validation"],
        ["Raw evidence", "LLM orchestration", "Entity resolution"],
        ["PostgreSQL", "Celery / Redis", "Sheets / API"],
    ]
    table = Table(flow, colWidths=[2.25 * inch] * 3)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF3F8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#7A8A99")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)

    story.append(PageBreak())
    story.append(Paragraph("Scaling and resilient ingestion", heading))
    story.append(
        Paragraph(
            "<b>500,000+ scale:</b> Add stateless API and worker replicas, retain bounded "
            "queues, partition timestamp-heavy tables, and use database uniqueness constraints "
            "for distributed deduplication. Redis coordinates tasks and rate limits; "
            "PostgreSQL remains the authoritative provenance store.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Freshness:</b> News and jobs require a verified original publication timestamp "
            "inside the inclusive 24-hour window. Missing dates are quarantined. Updated and "
            "modified timestamps are stored separately.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>LLM payload handling:</b> Provider context limits drive token-aware semantic "
            "chunks with overlap. HTTP 413 is retried only through smaller chunks or provider "
            "fallback. Oversized work is persisted for later retry.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>HTTP 429 handling:</b> Respect Retry-After when present, otherwise use bounded "
            "exponential backoff and jitter. Per-domain pacing and circuit breakers prevent "
            "repeated pressure.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Failure persistence:</b> Permanent authentication and invalid-request failures "
            "do not retry indefinitely. Transient and rate-limit failures are bounded and "
            "persisted as failed tasks for scheduled recovery.",
            body,
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Storage, resolution, and access policy", heading))
    story.append(
        Paragraph(
            "<b>PostgreSQL:</b> Authoritative relational storage for source URLs, timestamps, "
            "content hashes, entities, jobs, news, papers, tasks, runs, and export checkpoints. "
            "JSONB preserves raw evidence. UUIDs and unique constraints support horizontal workers.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Redis and Qdrant:</b> Redis coordinates queues and rate limits. Qdrant is an "
            "optional semantic retrieval index and cannot override canonical identity.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Entity resolution:</b> Normalize punctuation and legal suffixes, match exact "
            "canonical names and aliases first, then use RapidFuzz only at a conservative 96% "
            "threshold. Ambiguous or unmatched names enter human review.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Anti-bot strategy:</b> Prefer official APIs, RSS, and permitted pages. "
            "Playwright is explicit opt-in. Per-domain limits, polite delays, circuit breakers, "
            "and block detection stop unsafe or unauthorized crawling. CAPTCHA bypass is excluded.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Export and observability:</b> Google Sheets uses six batched tabs and database "
            "checkpoints. JSON logs carry run/task IDs, provider errors, retries, and crawl metrics.",
            body,
        )
    )

    doc.build(story)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
