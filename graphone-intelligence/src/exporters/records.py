from datetime import UTC, datetime
from ipaddress import ip_address
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from src.extractors.schemas import PricingModel


class ExportSource(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def require_public_http_url(cls, value: HttpUrl) -> HttpUrl:
        parsed = urlparse(str(value))
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Source URL must use HTTP or HTTPS")
        if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Source URL must be public")
        try:
            address = ip_address(parsed.hostname or "")
        except ValueError:
            address = None
        if address is not None and (address.is_private or address.is_loopback):
            raise ValueError("Source URL must be public")
        return value


class StartupExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "STARTUP"
    source: ExportSource
    entityName: str = Field(min_length=1)
    employeeCount: int | None = Field(default=None, ge=0)
    collectedAt: datetime

    @field_validator("collectedAt")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("collectedAt must be timezone-aware")
        return value.astimezone(UTC)


class ProductExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "PRODUCT"
    source: ExportSource
    entityName: str = Field(min_length=1)
    startupName: str | None = None
    pricingModel: PricingModel = PricingModel.UNKNOWN
    collectedAt: datetime

    @field_validator("collectedAt")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("collectedAt must be timezone-aware")
        return value.astimezone(UTC)


class ResearchExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "RESEARCH_PAPER"
    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    paperUrl: HttpUrl
    githubUrl: HttpUrl | None = None
    githubStars: int | None = Field(default=None, ge=0)
    publishedDate: datetime | None = None
    collectedAt: datetime

    @field_validator("collectedAt", "publishedDate")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware")
        return value.astimezone(UTC)


class JobExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "JOB"
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    date: datetime
    isRemote: bool | None = None
    roleFamily: str | None = None
    sourceUrl: HttpUrl
    sourceName: str = Field(min_length=1)

    @field_validator("date")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("date must be timezone-aware")
        return value.astimezone(UTC)


class NewsExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "NEWS"
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url: HttpUrl
    publicationDate: datetime
    lastModified: datetime | None = None
    fullText: str | None = None
    collectedAt: datetime

    @field_validator("publicationDate", "lastModified", "collectedAt")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware")
        return value.astimezone(UTC)
