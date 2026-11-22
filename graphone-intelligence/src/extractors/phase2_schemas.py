from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class NewsRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    publisher: str
    source_url: HttpUrl
    publication_date: datetime
    last_modified: datetime | None = None
    full_text: str | None = None
    collected_at: datetime

    @field_validator("publication_date", "last_modified", "collected_at")
    @classmethod
    def require_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("News timestamps must include timezone information")
        return value.astimezone(UTC)


class JobRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str
    title: str
    role_family: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    published_at: datetime
    last_modified: datetime | None = None
    source_url: HttpUrl
    source_name: str
    description: str | None = None

    @field_validator("published_at", "last_modified")
    @classmethod
    def require_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Job timestamps must include timezone information")
        return value.astimezone(UTC)
