"""High-level search helpers built on JellyClient."""

from __future__ import annotations

from jellyjelly.client import JellyClient
from jellyjelly.models import Jelly, SearchResponse


async def trending(client: JellyClient, page_size: int = 10) -> list[Jelly]:
    """Fetch trending jellies (empty query, sorted by recency)."""
    resp = await client.search("", page_size=page_size)
    return resp.jellies


async def by_creator(
    client: JellyClient, username: str, page_size: int = 10
) -> list[Jelly]:
    """Search for jellies by a specific creator's username.

    Uses keyword search and client-side filtering. Results may be
    incomplete if the API does not index usernames or if the creator's
    jellies span multiple pages.
    """
    resp = await client.search(username, page_size=page_size)
    return [
        j for j in resp.jellies if any(p.username == username for p in j.participants)
    ]


async def by_topic(client: JellyClient, topic: str, page_size: int = 10) -> list[Jelly]:
    """Search for jellies matching a topic keyword."""
    resp = await client.search(topic, page_size=page_size)
    return resp.jellies


async def search_all_pages(
    client: JellyClient,
    query: str,
    max_pages: int = 5,
    page_size: int = 10,
) -> list[Jelly]:
    """Paginate through search results up to max_pages.

    Args:
        client: Active JellyClient instance.
        query: Search term.
        max_pages: Maximum number of pages to fetch.
        page_size: Results per page.

    Returns:
        Aggregated list of jellies across all pages.
    """
    all_jellies: list[Jelly] = []

    for page_num in range(1, max_pages + 1):
        resp: SearchResponse = await client.search(
            query, page=page_num, page_size=page_size
        )
        all_jellies.extend(resp.jellies)

        # Stop if we got fewer results than requested (last page)
        if len(resp.jellies) < page_size:
            break

    return all_jellies
