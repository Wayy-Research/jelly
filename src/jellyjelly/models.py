"""Pydantic v2 models for JellyJelly API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Participant(BaseModel):
    """A participant (creator) of a jelly."""

    id: str
    username: str
    full_name: str | None = None
    pfp_url: str | None = None


class VideoInfo(BaseModel):
    """Video metadata from a jelly detail response."""

    original_duration: float = 0.0
    preview_timecode: float | None = None
    hls_master: str = ""


class TranscriptWord(BaseModel):
    """A single word from Deepgram transcript output."""

    word: str
    start: float = 0.0
    end: float = 0.0
    confidence: float = 0.0
    punctuated_word: str = ""


class TranscriptAlternative(BaseModel):
    """A transcript alternative containing word-level output."""

    words: list[TranscriptWord] = Field(default_factory=list)
    transcript: str = ""


class TranscriptChannel(BaseModel):
    """A transcript channel with alternatives."""

    alternatives: list[TranscriptAlternative] = Field(default_factory=list)


class TranscriptResults(BaseModel):
    """Deepgram transcript results container."""

    channels: list[TranscriptChannel] = Field(default_factory=list)


class TranscriptOverlay(BaseModel):
    """Top-level transcript overlay from jelly detail."""

    results: TranscriptResults | None = None


class AuthSession(BaseModel):
    """Supabase auth session tokens."""

    access_token: str
    refresh_token: str
    expires_at: int = 0
    user_id: str = ""


class Comment(BaseModel):
    """A comment on a jelly."""

    id: str
    user_id: str = ""
    username: str = ""
    text: str = ""
    created_at: datetime | None = None


class CommentsResponse(BaseModel):
    """Response from the comments endpoint."""

    comments: list[Comment] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10


class LikesResponse(BaseModel):
    """Response from the likes endpoint."""

    likes: list[str] = Field(default_factory=list)
    total: int = 0


class Jelly(BaseModel):
    """A jelly from search results (summary-level data).

    Search results only include id, title, participants, thumbnail_url,
    and posted_at. Engagement metrics require fetching the full detail.
    """

    id: str
    title: str = ""
    started_by_id: str | None = None
    participants: list[Participant] = Field(default_factory=list)
    thumbnail_url: str | None = None
    posted_at: datetime | None = None


class JellyDetail(BaseModel):
    """Full jelly detail including transcript, engagement, and video info."""

    id: str
    title: str = ""
    started_by_id: str | None = None
    participants: list[Participant] = Field(default_factory=list)
    posted_at: datetime | None = None
    summary: str | None = None
    privacy: str | None = None
    thumbnail_url: str | None = None
    video: VideoInfo | None = None
    transcript_overlay: TranscriptOverlay | None = None
    # Engagement metrics (only available in detail, not search)
    likes_count: int = 0
    comments_count: int = 0
    all_views: int = 0
    tips_total: float = 0.0
    # Extended fields from API probing
    access: str | None = None
    distinct_views: int = 0
    anon_views: int = 0
    price: float | None = None
    pay_to_watch: bool = False
    allow_preview: bool = True
    has_poll: bool = False
    has_event: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def transcript_text(self) -> str:
        """Return transcript from the first channel/alternative.

        Prefers the pre-joined transcript string. Falls back to
        reconstructing from punctuated words.
        """
        if not self.transcript_overlay or not self.transcript_overlay.results:
            return ""

        for channel in self.transcript_overlay.results.channels:
            for alt in channel.alternatives:
                if alt.transcript:
                    return alt.transcript
                if alt.words:
                    return " ".join(w.punctuated_word or w.word for w in alt.words)

        return ""

    @property
    def creator(self) -> Participant | None:
        """Return the first participant (creator) if available."""
        return self.participants[0] if self.participants else None

    @property
    def duration_seconds(self) -> float:
        """Return video duration in seconds."""
        return self.video.original_duration if self.video else 0.0


class SearchResponse(BaseModel):
    """Response from the /v3/jelly/search endpoint."""

    jellies: list[Jelly] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
