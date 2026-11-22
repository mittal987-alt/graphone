import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    base_url: Mapped[str] = mapped_column(String(2048), unique=True)
    source_type: Mapped[str] = mapped_column(String(50))
    source_identifier: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Startup(Base):
    __tablename__ = "startups"
    __table_args__ = (UniqueConstraint("source_url", name="uq_startup_source_url"),)
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_name: Mapped[str] = mapped_column(String(500), index=True)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str] = mapped_column(String(2048), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("source_url", name="uq_product_source_url"),)
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(500), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    startup_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pricing_model: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str] = mapped_column(String(2048), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class ResearchPaper(Base):
    __tablename__ = "research_papers"
    __table_args__ = (UniqueConstraint("paper_url", name="uq_paper_url"),)
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(1000), index=True)
    authors: Mapped[list] = mapped_column(JSON, default=list)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    paper_url: Mapped[str] = mapped_column(String(2048), index=True)
    github_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    github_stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_news_source_url"),
        UniqueConstraint("content_hash", name="uq_news_content_hash"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(1000), index=True)
    publisher: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str] = mapped_column(String(2048), index=True)
    publication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_job_source_url"),
        UniqueConstraint("content_hash", name="uq_job_content_hash"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company: Mapped[str] = mapped_column(String(500), index=True)
    title: Mapped[str] = mapped_column(String(1000), index=True)
    role_family: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_remote: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_url: Mapped[str] = mapped_column(String(2048), index=True)
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class QuarantineRecord(Base):
    __tablename__ = "quarantine_records"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    record_type: Mapped[str] = mapped_column(String(30), index=True)
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class CrawlCheckpoint(Base):
    __tablename__ = "crawl_checkpoints"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    cursor: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    last_crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    blocking_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class ExtractionTask(Base):
    __tablename__ = "extraction_tasks"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    record_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="queued")
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class FailedTask(Base):
    __tablename__ = "failed_tasks"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_type: Mapped[str] = mapped_column(String(50), index=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_kind: Mapped[str] = mapped_column(String(50), index=True)
    error_message: Mapped[str] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("canonical_id", name="uq_entity_canonical_id"),)
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    canonical_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String(500), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class EntityAlias(Base):
    __tablename__ = "entity_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", "entity_type", name="uq_alias_entity"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    alias: Mapped[str] = mapped_column(String(500), index=True)
    normalized_alias: Mapped[str] = mapped_column(String(500), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)


class EntityMappingLog(Base):
    __tablename__ = "entity_mapping_logs"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    raw_name: Mapped[str] = mapped_column(String(500), index=True)
    canonical_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    match_method: Mapped[str] = mapped_column(String(50), index=True)
    confidence_score: Mapped[float] = mapped_column(Float, index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class EntityReviewQueue(Base):
    __tablename__ = "entity_review_queue"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    raw_name: Mapped[str] = mapped_column(String(500), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    candidates: Mapped[dict] = mapped_column(JSON, default=dict)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class GitHubRepository(Base):
    __tablename__ = "github_repositories"
    __table_args__ = (
        UniqueConstraint("repository_url", name="uq_github_repository_url"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    repository_url: Mapped[str] = mapped_column(String(2048), index=True)
    owner: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pipeline_name: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    quarantined_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    task_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="pending")
    cursor: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class ExportCheckpoint(Base):
    __tablename__ = "export_checkpoints"
    __table_args__ = (UniqueConstraint("tab_name", name="uq_export_checkpoint_tab"),)
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tab_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    last_record_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_row_count: Mapped[int] = mapped_column(Integer, default=0)
    last_exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
