import re

from src.utils.http import AsyncHttpClient

GITHUB_PATH_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


async def get_github_metrics(
    github_url: str | None,
    token: str | None = None,
    *,
    client: AsyncHttpClient | None = None,
) -> tuple[str | None, int | None]:
    if not github_url:
        return None, None
    match = GITHUB_PATH_RE.search(github_url)
    if not match:
        return None, None
    owner, repo = match.groups()
    repo = repo.rstrip("/.git").strip()
    canonical_url = f"https://github.com/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if client is None:
        requests_per_second = 1.0 if token else 1.0 / 60
        client = AsyncHttpClient(requests_per_second=requests_per_second)
    payload = await client.get_json(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
    )
    stars = payload.get("stargazers_count")
    return canonical_url if isinstance(
        stars, int
    ) else canonical_url, stars if isinstance(stars, int) else None
