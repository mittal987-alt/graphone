from datetime import UTC, datetime
from enum import Enum
from ipaddress import ip_address
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Source(BaseModel):
    name: str
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def require_public_http_url(cls, url: HttpUrl) -> HttpUrl:
        value = str(url)
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Source URL must use HTTP or HTTPS")
        if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Source URL must be publicly accessible")
        try:
            address = ip_address(parsed.hostname or "")
        except ValueError:
            address = None
        if address is not None and (address.is_private or address.is_loopback):
            raise ValueError("Source URL must not be a private or loopback address")
        return url


class StartupData(BaseModel):
    employeeCount: int | None = None


class StartupRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "STARTUP"
    source: Source
    content: "StartupContent"
    collectedAt: datetime

    @field_validator("collectedAt")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("collectedAt must include timezone information")
        return value.astimezone(UTC)


class StartupContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entityName: str = Field(min_length=1)
    data: StartupData


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"
    UNKNOWN = "UNKNOWN"


class ProductRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "PRODUCT"
    source: Source
    content: "ProductContent"
    collectedAt: datetime

    @field_validator("collectedAt")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("collectedAt must include timezone information")
        return value.astimezone(UTC)


class ProductContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entityName: str = Field(min_length=1)
    startupName: str | None = None
    pricingModel: PricingModel = PricingModel.UNKNOWN


class ResearchPaperRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str = "1.0"
    recordType: str = "RESEARCH_PAPER"
    content: "ResearchPaperContent"
    collectedAt: datetime

    @field_validator("collectedAt")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("collectedAt must include timezone information")
        return value.astimezone(UTC)


class ResearchPaperContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    paper_url: HttpUrl
    github_url: HttpUrl | None = None
    github_stars: int | None = Field(default=None, ge=0)
    published_date: datetime | None = None

    @field_validator("published_date")
    @classmethod
    def require_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("published_date must include timezone information")
        return value.astimezone(UTC)


StartupRecord.model_rebuild()
ProductRecord.model_rebuild()
ResearchPaperRecord.model_rebuild()
