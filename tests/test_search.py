"""Tests for high-level search helpers."""

from __future__ import annotations

import httpx
import respx

from jellyjelly.client import JellyClient
from jellyjelly.search import by_creator, by_topic, search_all_pages, trending

from .conftest import make_jelly_summary, make_search_response


class TestTrending:
    async def test_returns_jellies(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(
                200,
                json=make_search_response(
                    jellies=[
                        make_jelly_summary(jelly_id="j1"),
                        make_jelly_summary(jelly_id="j2"),
                    ]
                ),
            )
        )
        async with JellyClient() as client:
            results = await trending(client)
        assert len(results) == 2


class TestByCreator:
    async def test_filters_by_username(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(
                200,
                json=make_search_response(
                    jellies=[
                        make_jelly_summary(jelly_id="j1", username="rick"),
                        make_jelly_summary(jelly_id="j2", username="other"),
                    ]
                ),
            )
        )
        async with JellyClient() as client:
            results = await by_creator(client, "rick")
        assert len(results) == 1
        assert results[0].id == "j1"


class TestByTopic:
    async def test_returns_topic_results(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(
                200,
                json=make_search_response(jellies=[make_jelly_summary()]),
            )
        )
        async with JellyClient() as client:
            results = await by_topic(client, "quant")
        assert len(results) == 1


class TestSearchAllPages:
    async def test_paginates(self, mock_api: respx.MockRouter) -> None:
        page1 = make_search_response(
            jellies=[make_jelly_summary(jelly_id=f"j{i}") for i in range(10)],
            page=1,
            page_size=10,
        )
        page2 = make_search_response(
            jellies=[make_jelly_summary(jelly_id=f"j{i}") for i in range(10, 15)],
            page=2,
            page_size=10,
        )
        route = mock_api.get("/v3/jelly/search")
        route.side_effect = [
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
        async with JellyClient() as client:
            results = await search_all_pages(client, "fintech", max_pages=5)
        assert len(results) == 15

    async def test_stops_on_short_page(self, mock_api: respx.MockRouter) -> None:
        short_page = make_search_response(
            jellies=[make_jelly_summary(jelly_id="j1")],
            page=1,
            page_size=10,
        )
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(200, json=short_page)
        )
        async with JellyClient() as client:
            results = await search_all_pages(client, "niche", max_pages=5)
        assert len(results) == 1
