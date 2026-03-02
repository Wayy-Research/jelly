"""Shared fixtures for JellyJelly SDK tests."""

from __future__ import annotations

from typing import Any

import pytest
import respx


@pytest.fixture()
def mock_api() -> respx.MockRouter:
    """Return a respx mock router scoped to the JellyJelly API base URL."""
    with respx.mock(
        base_url="https://api.jellyjelly.com",
        assert_all_called=False,
    ) as router:
        yield router


def make_search_response(
    jellies: list[dict[str, Any]] | None = None,
    total: int | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Build a realistic search response payload."""
    if jellies is None:
        jellies = [make_jelly_summary()]
    return {
        "status": "success",
        "jellies": jellies,
        "total": total if total is not None else len(jellies),
        "page": page,
        "page_size": page_size,
        "query": "",
        "username": "",
        "sort_by": "",
        "ascending": False,
        "start_date": "",
        "end_date": "",
    }


def make_jelly_summary(
    jelly_id: str = "01KJB81V9Q1J349XBHFM90GQC0",
    title: str = "Fintech is eating Wall Street",
    username: str = "rick",
) -> dict[str, Any]:
    """Build a realistic jelly summary (search result item)."""
    return {
        "id": jelly_id,
        "started_by_id": "user-001",
        "title": title,
        "participants": [
            {
                "id": "user-001",
                "username": username,
                "full_name": "Rick G",
                "pfp_url": "https://user-pfp.jellyjelly.com/user-001/pic.jpeg",
            }
        ],
        "thumbnail_url": "https://dist.jellyjelly.com/thumb.jpeg",
        "posted_at": "2026-02-28T14:30:00Z",
    }


def make_jelly_detail(
    jelly_id: str = "01KJB81V9Q1J349XBHFM90GQC0",
    title: str = "Fintech is eating Wall Street",
    transcript_text: str = "So the thing about fintech is "
    "really democratizing access to markets.",
) -> dict[str, Any]:
    """Build a realistic jelly detail response with Deepgram transcript."""
    words = []
    start = 0.0
    for w in transcript_text.split():
        words.append(
            {
                "word": w.lower().strip(".,!?"),
                "start": start,
                "end": start + 0.3,
                "confidence": 0.95,
                "punctuated_word": w,
            }
        )
        start += 0.35

    return {
        "status": "success",
        "jelly": {
            "id": jelly_id,
            "started_by_id": "user-001",
            "title": title,
            "participants": [
                {
                    "id": "user-001",
                    "username": "rick",
                    "full_name": "Rick G",
                    "pfp_url": "https://user-pfp.jellyjelly.com/user-001/pic.jpeg",
                }
            ],
            "posted_at": "2026-02-28T14:30:00Z",
            "summary": "A discussion about fintech democratizing markets.",
            "privacy": "public",
            "thumbnail_url": "https://dist.jellyjelly.com/thumb.jpeg",
            "video": {
                "original_duration": 45.2,
                "preview_timecode": None,
                "hls_master": "https://dist.jellyjelly.com/video.m3u8",
            },
            "transcript_overlay": {
                "results": {
                    "channels": [
                        {
                            "alternatives": [
                                {
                                    "words": words,
                                    "transcript": transcript_text,
                                }
                            ]
                        }
                    ]
                }
            },
            "likes_count": 42,
            "comments_count": 7,
            "all_views": 1500,
            "tips_total": 3.5,
        },
    }
