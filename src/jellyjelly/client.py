"""Async httpx client for the JellyJelly API."""

from __future__ import annotations

import asyncio
import re
from types import TracebackType
from typing import Any

import httpx

from jellyjelly.models import JellyDetail, SearchResponse

BASE_URL = "https://api.jellyjelly.com"

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0  # seconds
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_JELLY_ID_RE = re.compile(r"^[\w-]+$")


class JellyAPIError(Exception):
    """Raised when a JellyJelly API request fails after retries."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"JellyJelly API error {status_code}: {detail}")


class JellyClient:
    """Async client for the JellyJelly public API.

    Usage::

        async with JellyClient() as client:
            results = await client.search("fintech")
            detail = await client.get_jelly(results.jellies[0].id)
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        max_retries: int = MAX_RETRIES,
        retry_backoff_base: float = RETRY_BACKOFF_BASE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_backoff_base = retry_backoff_base
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def __aenter__(self) -> JellyClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make a request with retry and exponential backoff."""
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.request(method, path, **kwargs)

                if resp.status_code < 400:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        raise JellyAPIError(
                            resp.status_code,
                            f"Invalid JSON: {resp.text[:200]}",
                        ) from exc

                retryable = resp.status_code in RETRYABLE_STATUS_CODES
                if retryable and attempt < self._max_retries:
                    delay = self._retry_backoff_base * (2**attempt)
                    await asyncio.sleep(delay)
                    continue

                raise JellyAPIError(resp.status_code, resp.text)

            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_backoff_base * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise

        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected retry loop exit")  # pragma: no cover

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
    ) -> SearchResponse:
        """Search jellies by keyword.

        Args:
            query: Search term.
            page: Page number (1-indexed).
            page_size: Results per page (max 100).

        Returns:
            Parsed search response with list of jellies.
        """
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size < 1 or page_size > 100:
            raise ValueError(f"page_size must be 1-100, got {page_size}")
        data = await self._request(
            "GET",
            "/v3/jelly/search",
            params={"q": query, "page": page, "page_size": page_size},
        )
        return SearchResponse.model_validate(data)

    async def get_jelly(self, jelly_id: str) -> JellyDetail:
        """Get full detail for a single jelly including transcript.

        Args:
            jelly_id: The jelly's unique ID.

        Returns:
            Full jelly detail with transcript and video info.

        Raises:
            ValueError: If jelly_id contains invalid characters.
        """
        if not _JELLY_ID_RE.match(jelly_id):
            raise ValueError(f"Invalid jelly_id: {jelly_id!r}")
        data = await self._request("GET", f"/v3/jelly/{jelly_id}")
        # Detail response wraps the jelly in {"status": ..., "jelly": {...}}
        jelly_data: Any = data.get("jelly", data) if isinstance(data, dict) else data
        return JellyDetail.model_validate(jelly_data)
