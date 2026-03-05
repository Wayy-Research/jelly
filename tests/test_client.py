"""Tests for JellyClient async HTTP client."""

from __future__ import annotations

import httpx
import pytest
import respx

from jellyjelly.client import JellyAPIError, JellyClient

from .conftest import (
    make_comments_response,
    make_jelly_detail,
    make_likes_response,
    make_search_response,
)

# All tests use retry_backoff_base=0.0 to avoid real sleeps.
FAST = {"retry_backoff_base": 0.0}


class TestSearch:
    async def test_search_returns_jellies(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(200, json=make_search_response())
        )
        async with JellyClient() as client:
            resp = await client.search("fintech")
        assert len(resp.jellies) == 1
        assert resp.jellies[0].id == "01KJB81V9Q1J349XBHFM90GQC0"

    async def test_search_passes_params(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(200, json=make_search_response())
        )
        async with JellyClient() as client:
            await client.search("quant", page=2, page_size=5)
        assert route.called
        request = route.calls[0].request
        assert b"q=quant" in request.url.raw_path
        assert b"page=2" in request.url.raw_path
        assert b"page_size=5" in request.url.raw_path

    async def test_search_with_username(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(200, json=make_search_response())
        )
        async with JellyClient() as client:
            await client.search("", username="marmo")
        request = route.calls[0].request
        assert b"username=marmo" in request.url.raw_path

    async def test_search_with_sort(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(200, json=make_search_response())
        )
        async with JellyClient() as client:
            await client.search("", sort_by="likes", ascending=False)
        request = route.calls[0].request
        assert b"sort_by=likes" in request.url.raw_path
        assert b"ascending=false" in request.url.raw_path

    async def test_search_with_dates(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(200, json=make_search_response())
        )
        async with JellyClient() as client:
            await client.search("", start_date="2026-01-01", end_date="2026-03-01")
        request = route.calls[0].request
        assert b"start_date=2026-01-01" in request.url.raw_path
        assert b"end_date=2026-03-01" in request.url.raw_path

    async def test_search_empty_result(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(
                200,
                json=make_search_response(jellies=[], total=0),
            )
        )
        async with JellyClient() as client:
            resp = await client.search("nonexistent")
        assert resp.jellies == []
        assert resp.total == 0

    async def test_search_rejects_zero_page(self) -> None:
        async with JellyClient() as client:
            with pytest.raises(ValueError, match="page must be"):
                await client.search("test", page=0)

    async def test_search_rejects_bad_page_size(self) -> None:
        async with JellyClient() as client:
            with pytest.raises(ValueError, match="page_size must be"):
                await client.search("test", page_size=0)


class TestGetJelly:
    async def test_get_jelly_detail(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/01KJB81V9Q1J349XBHFM90GQC0").mock(
            return_value=httpx.Response(200, json=make_jelly_detail())
        )
        async with JellyClient() as client:
            detail = await client.get_jelly("01KJB81V9Q1J349XBHFM90GQC0")
        assert detail.id == "01KJB81V9Q1J349XBHFM90GQC0"
        assert detail.transcript_text != ""
        assert detail.video is not None
        assert detail.likes_count == 42
        assert detail.all_views == 1500

    async def test_get_jelly_404(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/missing").mock(
            return_value=httpx.Response(404, text="Not found")
        )
        async with JellyClient() as client:
            with pytest.raises(JellyAPIError) as exc_info:
                await client.get_jelly("missing")
        assert exc_info.value.status_code == 404

    async def test_get_jelly_rejects_path_traversal(self) -> None:
        async with JellyClient() as client:
            with pytest.raises(ValueError, match="Invalid jelly_id"):
                await client.get_jelly("../../admin/users")

    async def test_get_jelly_rejects_slashes(self) -> None:
        async with JellyClient() as client:
            with pytest.raises(ValueError, match="Invalid jelly_id"):
                await client.get_jelly("foo/bar")


class TestAuth:
    async def test_authenticated_property(self) -> None:
        async with JellyClient() as client:
            assert not client.authenticated
            client.set_token("test-token")
            assert client.authenticated
            client.clear_token()
            assert not client.authenticated

    async def test_init_with_token(self) -> None:
        async with JellyClient(token="my-token") as client:
            assert client.authenticated

    async def test_require_auth_raises(self) -> None:
        async with JellyClient() as client:
            with pytest.raises(JellyAPIError) as exc_info:
                await client.get_comments("some-id")
            assert exc_info.value.status_code == 401

    async def test_auth_header_sent(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/test-id/comments").mock(
            return_value=httpx.Response(200, json=make_comments_response())
        )
        async with JellyClient(token="my-jwt") as client:
            await client.get_comments("test-id")
        request = route.calls[0].request
        assert request.headers["authorization"] == "Bearer my-jwt"


class TestGetComments:
    async def test_get_comments(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/test-id/comments").mock(
            return_value=httpx.Response(200, json=make_comments_response())
        )
        async with JellyClient(token="tok") as client:
            resp = await client.get_comments("test-id")
        assert len(resp.comments) == 1
        assert resp.comments[0].text == "Great jelly!"
        assert resp.total == 1

    async def test_get_comments_pagination(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/test-id/comments").mock(
            return_value=httpx.Response(200, json=make_comments_response())
        )
        async with JellyClient(token="tok") as client:
            await client.get_comments("test-id", page=2, page_size=5)
        request = route.calls[0].request
        assert b"page=2" in request.url.raw_path
        assert b"page_size=5" in request.url.raw_path


class TestGetLikes:
    async def test_get_likes(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/test-id/likes").mock(
            return_value=httpx.Response(200, json=make_likes_response())
        )
        async with JellyClient(token="tok") as client:
            resp = await client.get_likes("test-id")
        assert resp.total == 2
        assert "user-001" in resp.likes


class TestComment:
    async def test_post_comment(self, mock_api: respx.MockRouter) -> None:
        mock_api.post("/v3/jelly/test-id/comment").mock(
            return_value=httpx.Response(
                200, json={"status": "success", "id": "comment-new"}
            )
        )
        async with JellyClient(token="tok") as client:
            result = await client.comment("test-id", "Nice!")
        assert result["status"] == "success"

    async def test_comment_empty_text(self) -> None:
        async with JellyClient(token="tok") as client:
            with pytest.raises(ValueError, match="must not be empty"):
                await client.comment("test-id", "   ")

    async def test_comment_requires_auth(self) -> None:
        async with JellyClient() as client:
            with pytest.raises(JellyAPIError) as exc_info:
                await client.comment("test-id", "text")
            assert exc_info.value.status_code == 401


class TestLike:
    async def test_post_like(self, mock_api: respx.MockRouter) -> None:
        mock_api.post("/v3/jelly/test-id/like").mock(
            return_value=httpx.Response(200, json={"status": "success"})
        )
        async with JellyClient(token="tok") as client:
            result = await client.like("test-id")
        assert result["status"] == "success"

    async def test_like_requires_auth(self) -> None:
        async with JellyClient() as client:
            with pytest.raises(JellyAPIError) as exc_info:
                await client.like("test-id")
            assert exc_info.value.status_code == 401


class TestRetry:
    async def test_retries_on_429(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/search")
        route.side_effect = [
            httpx.Response(429, text="Rate limited"),
            httpx.Response(200, json=make_search_response()),
        ]
        async with JellyClient(max_retries=2, **FAST) as client:
            resp = await client.search("test")
        assert len(resp.jellies) == 1

    async def test_retries_on_500(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/search")
        route.side_effect = [
            httpx.Response(500, text="Server error"),
            httpx.Response(500, text="Server error"),
            httpx.Response(200, json=make_search_response()),
        ]
        async with JellyClient(max_retries=3, **FAST) as client:
            resp = await client.search("test")
        assert len(resp.jellies) == 1

    async def test_raises_after_max_retries(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(500, text="Server error")
        )
        async with JellyClient(max_retries=1, **FAST) as client:
            with pytest.raises(JellyAPIError) as exc_info:
                await client.search("test")
        assert exc_info.value.status_code == 500

    async def test_no_retry_on_400(self, mock_api: respx.MockRouter) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(400, text="Bad request")
        )
        async with JellyClient(max_retries=3, **FAST) as client:
            with pytest.raises(JellyAPIError) as exc_info:
                await client.search("test")
        assert exc_info.value.status_code == 400

    async def test_retries_on_network_error(self, mock_api: respx.MockRouter) -> None:
        route = mock_api.get("/v3/jelly/search")
        route.side_effect = [
            httpx.ConnectError("Connection refused"),
            httpx.Response(200, json=make_search_response()),
        ]
        async with JellyClient(max_retries=2, **FAST) as client:
            resp = await client.search("test")
        assert len(resp.jellies) == 1

    async def test_raises_network_error_after_retries(
        self, mock_api: respx.MockRouter
    ) -> None:
        mock_api.get("/v3/jelly/search").side_effect = httpx.ConnectError(
            "Connection refused"
        )
        async with JellyClient(max_retries=1, **FAST) as client:
            with pytest.raises(httpx.ConnectError):
                await client.search("test")


class TestClientLifecycle:
    async def test_close_without_context_manager(
        self, mock_api: respx.MockRouter
    ) -> None:
        mock_api.get("/v3/jelly/search").mock(
            return_value=httpx.Response(200, json=make_search_response())
        )
        client = JellyClient()
        try:
            resp = await client.search("fintech")
            assert len(resp.jellies) == 1
        finally:
            await client.close()
