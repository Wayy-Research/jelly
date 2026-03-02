# jellyjelly

> Async Python client for the JellyJelly public API

[![PyPI](https://img.shields.io/pypi/v/jellyjelly)](https://pypi.org/project/jellyjelly/)
[![Tests](https://github.com/Wayy-Research/jelly/actions/workflows/ci.yml/badge.svg)](https://github.com/Wayy-Research/jelly/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

Search, retrieve, and analyze content from JellyJelly -- the video-first SocialFi platform built on Solana. No API key required.

## What is JellyJelly?

[JellyJelly](https://jellyjelly.com) is a video-first social platform founded by Iqram Magdon-Ismail (co-founder of Venmo). Users create short video "jellies" -- think conversations, interviews, and hot takes -- with built-in social tokens on Solana. Each jelly includes engagement metrics (views, likes, comments, tips) and Deepgram-powered transcripts.

The API is public and requires no authentication.

## Installation

```bash
pip install jellyjelly
```

From source:

```bash
git clone https://github.com/Wayy-Research/jelly.git
cd jelly
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from jellyjelly import JellyClient

async def main():
    async with JellyClient() as client:
        # Search for jellies by keyword
        results = await client.search("fintech")
        for jelly in results.jellies:
            print(f"{jelly.title} by @{jelly.participants[0].username}")

        # Get full detail: transcript, engagement metrics, video info
        detail = await client.get_jelly(results.jellies[0].id)
        print(f"Views: {detail.all_views}")
        print(f"Likes: {detail.likes_count}")
        print(f"Transcript: {detail.transcript_text[:200]}")

asyncio.run(main())
```

## Features

- **Async-first**: Built on `httpx` -- non-blocking by default, works with `asyncio`
- **Typed responses**: Pydantic v2 models for every API response, full `mypy --strict` compliance
- **Search + detail**: Keyword search with pagination, full jelly detail with Deepgram transcripts
- **High-level helpers**: `trending()`, `by_creator()`, `by_topic()`, `search_all_pages()` for common patterns
- **Automatic retries**: Exponential backoff on 429 rate limits and 5xx server errors
- **Path traversal protection**: ID validation prevents injection of malicious paths
- **No auth required**: The JellyJelly API is public -- just install and go

## Examples

### Search with Pagination

```python
from jellyjelly import JellyClient

async def main():
    async with JellyClient() as client:
        # Page through results (1-indexed, max 100 per page)
        page1 = await client.search("crypto", page=1, page_size=20)
        page2 = await client.search("crypto", page=2, page_size=20)

        print(f"Total results: {page1.total}")
        print(f"Page 1: {len(page1.jellies)} jellies")
        print(f"Page 2: {len(page2.jellies)} jellies")
```

### High-Level Search Helpers

```python
from jellyjelly import JellyClient, trending, by_creator, by_topic, search_all_pages

async def main():
    async with JellyClient() as client:
        # Trending jellies (empty query, sorted by recency)
        top = await trending(client)

        # Filter by creator username
        iqram = await by_creator(client, "iqram")

        # Topic search
        crypto = await by_topic(client, "crypto")

        # Auto-paginate up to N pages
        all_results = await search_all_pages(client, "startup", max_pages=3)
        print(f"Collected {len(all_results)} jellies across pages")
```

### Working with Jelly Details

```python
from jellyjelly import JellyClient

async def main():
    async with JellyClient() as client:
        results = await client.search("AI")
        detail = await client.get_jelly(results.jellies[0].id)

        # Engagement metrics
        print(f"Views: {detail.all_views}")
        print(f"Likes: {detail.likes_count}")
        print(f"Comments: {detail.comments_count}")
        print(f"Tips: {detail.tips_total}")

        # Transcript (Deepgram)
        print(f"Transcript: {detail.transcript_text}")

        # AI-generated summary
        print(f"Summary: {detail.summary}")

        # Video info
        print(f"Duration: {detail.duration_seconds}s")

        # Creator shortcut
        if detail.creator:
            print(f"Created by: @{detail.creator.username}")
```

### Custom Client Configuration

```python
from jellyjelly import JellyClient

async def main():
    async with JellyClient(
        timeout=60.0,           # Request timeout in seconds (default: 30)
        max_retries=5,          # Retry attempts on 429/5xx (default: 3)
        retry_backoff_base=2.0, # Base delay for exponential backoff (default: 1.0)
    ) as client:
        results = await client.search("fintech")
```

### Error Handling

```python
from jellyjelly import JellyClient, JellyAPIError

async def main():
    async with JellyClient() as client:
        try:
            detail = await client.get_jelly("nonexistent-id")
        except JellyAPIError as e:
            print(f"API error {e.status_code}: {e.detail}")
```

## API Reference

### `JellyClient`

| Method | Description |
|--------|-------------|
| `search(query, page=1, page_size=10)` | Search jellies by keyword. Returns `SearchResponse`. |
| `get_jelly(jelly_id)` | Get full detail for a jelly. Returns `JellyDetail`. |
| `close()` | Close the underlying httpx client. |

### Search Helpers

| Function | Description |
|----------|-------------|
| `trending(client, page_size=10)` | Fetch trending jellies. Returns `list[Jelly]`. |
| `by_creator(client, username, page_size=10)` | Search by creator username (client-side filtered). Returns `list[Jelly]`. |
| `by_topic(client, topic, page_size=10)` | Search by topic keyword. Returns `list[Jelly]`. |
| `search_all_pages(client, query, max_pages=5, page_size=10)` | Auto-paginate through results. Returns `list[Jelly]`. |

### Models

| Model | Key Fields |
|-------|------------|
| `SearchResponse` | `jellies`, `total`, `page`, `page_size` |
| `Jelly` | `id`, `title`, `participants`, `thumbnail_url`, `posted_at` |
| `JellyDetail` | Everything in `Jelly` + `all_views`, `likes_count`, `comments_count`, `tips_total`, `summary`, `video`, `transcript_overlay` |
| `JellyDetail` (properties) | `transcript_text`, `creator`, `duration_seconds` |
| `Participant` | `id`, `username`, `full_name`, `pfp_url` |
| `VideoInfo` | `original_duration`, `preview_timecode`, `hls_master` |
| `TranscriptWord` | `word`, `start`, `end`, `confidence`, `punctuated_word` |

### API Endpoints

| Endpoint | SDK Method |
|----------|------------|
| `GET /v3/jelly/search?q=...&page=1&page_size=10` | `client.search()` |
| `GET /v3/jelly/{id}` | `client.get_jelly()` |

## Development

```bash
git clone https://github.com/Wayy-Research/jelly.git
cd jelly
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest -v

# Type checking
mypy --strict src/

# Linting + formatting
ruff check .
black .
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with frustration and determination by [Wayy Research](https://wayyresearch.com) -- Buffalo, NY.
*People for research, research for people.*
