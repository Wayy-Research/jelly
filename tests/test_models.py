"""Tests for JellyJelly Pydantic models."""

from __future__ import annotations

from jellyjelly.models import (
    AuthSession,
    Comment,
    CommentsResponse,
    Jelly,
    JellyDetail,
    LikesResponse,
    SearchResponse,
)

from .conftest import (
    make_comment,
    make_comments_response,
    make_jelly_detail,
    make_jelly_summary,
    make_likes_response,
    make_search_response,
)


class TestJelly:
    def test_parse_summary(self) -> None:
        data = make_jelly_summary()
        jelly = Jelly.model_validate(data)
        assert jelly.id == "01KJB81V9Q1J349XBHFM90GQC0"
        assert jelly.title == "Fintech is eating Wall Street"
        assert len(jelly.participants) == 1
        assert jelly.participants[0].username == "rick"
        assert jelly.participants[0].full_name == "Rick G"

    def test_parse_minimal(self) -> None:
        jelly = Jelly.model_validate({"id": "abc"})
        assert jelly.id == "abc"
        assert jelly.title == ""
        assert jelly.participants == []

    def test_posted_at_parsed(self) -> None:
        data = make_jelly_summary()
        jelly = Jelly.model_validate(data)
        assert jelly.posted_at is not None
        assert jelly.posted_at.year == 2026


class TestJellyDetail:
    def test_transcript_text_from_joined(self) -> None:
        text = "Hello world this is a test"
        data = make_jelly_detail(transcript_text=text)
        detail = JellyDetail.model_validate(data["jelly"])
        assert detail.transcript_text == text

    def test_transcript_text_from_words(self) -> None:
        """When transcript string is empty, reconstruct from words."""
        text = "Fallback test"
        data = make_jelly_detail(transcript_text=text)
        jelly = data["jelly"]
        # Clear the joined transcript to test word-level fallback
        channel = jelly["transcript_overlay"]["results"]["channels"][0]
        channel["alternatives"][0]["transcript"] = ""
        detail = JellyDetail.model_validate(jelly)
        assert detail.transcript_text == text

    def test_transcript_text_empty(self) -> None:
        data = make_jelly_detail()
        jelly = data["jelly"]
        jelly["transcript_overlay"] = None
        detail = JellyDetail.model_validate(jelly)
        assert detail.transcript_text == ""

    def test_creator_property(self) -> None:
        data = make_jelly_detail()
        detail = JellyDetail.model_validate(data["jelly"])
        assert detail.creator is not None
        assert detail.creator.username == "rick"

    def test_creator_none_when_empty(self) -> None:
        data = make_jelly_detail()
        jelly = data["jelly"]
        jelly["participants"] = []
        detail = JellyDetail.model_validate(jelly)
        assert detail.creator is None

    def test_duration_seconds(self) -> None:
        data = make_jelly_detail()
        detail = JellyDetail.model_validate(data["jelly"])
        assert detail.duration_seconds == 45.2

    def test_duration_no_video(self) -> None:
        data = make_jelly_detail()
        jelly = data["jelly"]
        jelly["video"] = None
        detail = JellyDetail.model_validate(jelly)
        assert detail.duration_seconds == 0.0

    def test_engagement_metrics(self) -> None:
        data = make_jelly_detail()
        detail = JellyDetail.model_validate(data["jelly"])
        assert detail.likes_count == 42
        assert detail.comments_count == 7
        assert detail.all_views == 1500
        assert detail.tips_total == 3.5

    def test_summary_field(self) -> None:
        data = make_jelly_detail()
        detail = JellyDetail.model_validate(data["jelly"])
        assert detail.summary is not None
        assert "fintech" in detail.summary.lower()

    def test_null_participant_fields(self) -> None:
        """API can return null for pfp_url and full_name."""
        data = make_jelly_detail()
        jelly = data["jelly"]
        jelly["participants"] = [
            {
                "id": "user-001",
                "username": "rick",
                "full_name": None,
                "pfp_url": None,
            }
        ]
        detail = JellyDetail.model_validate(jelly)
        assert detail.creator is not None
        assert detail.creator.pfp_url is None
        assert detail.creator.full_name is None

    def test_extended_fields(self) -> None:
        """Extended fields from API probing parse correctly."""
        data = make_jelly_detail()
        jelly = data["jelly"]
        jelly["access"] = "free"
        jelly["distinct_views"] = 1200
        jelly["anon_views"] = 300
        jelly["price"] = 0.0
        jelly["pay_to_watch"] = False
        jelly["allow_preview"] = True
        jelly["has_poll"] = False
        jelly["has_event"] = True
        jelly["created_at"] = "2026-02-28T14:00:00Z"
        jelly["updated_at"] = "2026-02-28T15:00:00Z"
        jelly["deleted_at"] = None
        detail = JellyDetail.model_validate(jelly)
        assert detail.access == "free"
        assert detail.distinct_views == 1200
        assert detail.anon_views == 300
        assert detail.has_event is True
        assert detail.created_at is not None
        assert detail.deleted_at is None


class TestSearchResponse:
    def test_parse_response(self) -> None:
        data = make_search_response()
        resp = SearchResponse.model_validate(data)
        assert resp.total == 1
        assert len(resp.jellies) == 1
        assert resp.jellies[0].id == "01KJB81V9Q1J349XBHFM90GQC0"
        assert resp.page == 1

    def test_empty_response(self) -> None:
        data = make_search_response(jellies=[], total=0)
        resp = SearchResponse.model_validate(data)
        assert resp.total == 0
        assert resp.jellies == []


class TestComment:
    def test_parse_comment(self) -> None:
        data = make_comment()
        comment = Comment.model_validate(data)
        assert comment.id == "comment-001"
        assert comment.username == "rick"
        assert comment.text == "Great jelly!"
        assert comment.created_at is not None

    def test_minimal_comment(self) -> None:
        comment = Comment.model_validate({"id": "c1"})
        assert comment.id == "c1"
        assert comment.text == ""


class TestCommentsResponse:
    def test_parse_comments_response(self) -> None:
        data = make_comments_response()
        resp = CommentsResponse.model_validate(data)
        assert len(resp.comments) == 1
        assert resp.total == 1
        assert resp.page == 1

    def test_empty_comments(self) -> None:
        data = make_comments_response(comments=[], total=0)
        resp = CommentsResponse.model_validate(data)
        assert resp.comments == []
        assert resp.total == 0


class TestLikesResponse:
    def test_parse_likes_response(self) -> None:
        data = make_likes_response()
        resp = LikesResponse.model_validate(data)
        assert resp.total == 2
        assert "user-001" in resp.likes

    def test_empty_likes(self) -> None:
        data = make_likes_response(likes=[], total=0)
        resp = LikesResponse.model_validate(data)
        assert resp.likes == []
        assert resp.total == 0


class TestAuthSession:
    def test_parse_auth_session(self) -> None:
        session = AuthSession(
            access_token="tok",
            refresh_token="ref",
            expires_at=123456,
            user_id="user-001",
        )
        assert session.access_token == "tok"
        assert session.expires_at == 123456

    def test_defaults(self) -> None:
        session = AuthSession(access_token="tok", refresh_token="ref")
        assert session.expires_at == 0
        assert session.user_id == ""
