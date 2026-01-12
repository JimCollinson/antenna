#!/usr/bin/env python3
"""
Marketing OS - Daily Briefing Generator

Fetches posts from social platforms, scores them against ICP criteria,
and outputs a single consolidated Daily Briefing for review.

No intermediate files - everything is processed in memory.

Usage:
    python marketing_os.py                    # Run full pipeline
    python marketing_os.py --dry-run          # Preview without API calls
    python marketing_os.py --platform bluesky # Specific platform only
"""

import argparse
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Bluesky SDK
try:
    from atproto import Client as BlueskyClient

    ATPROTO_AVAILABLE = True
except ImportError:
    ATPROTO_AVAILABLE = False

# Apify SDK (for YouTube)
try:
    from apify_client import ApifyClient

    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================


def get_project_root() -> Path:
    """Get the Marketing OS project root (parent of Scripts folder)."""
    return Path(__file__).parent.parent


def load_config() -> dict:
    """Load configuration from ../config.yaml"""
    config_path = get_project_root() / "config.yaml"

    if not config_path.exists():
        print(f"Error: config.yaml not found at {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def load_queries(platform: str) -> list:
    """Load active queries from ../queries/{platform}.yaml"""
    queries_path = get_project_root() / "queries" / f"{platform}.yaml"

    if not queries_path.exists():
        return []

    with open(queries_path) as f:
        data = yaml.safe_load(f) or {}
        return data.get("active", [])


def load_context_file(filename: str) -> str:
    """Load a context file from ../Context/"""
    context_path = get_project_root() / "Context" / filename
    if context_path.exists():
        return context_path.read_text()
    return ""


# =============================================================================
# SCORING
# =============================================================================


def score_post(post: dict, icp_context: str, positioning_context: str) -> dict:
    """
    Score a post against ICP criteria.
    Returns dict with score breakdown and total.

    Scoring dimensions (from MVP Requirements):
    - ICP Match (30%): Does author/content match Pioneer Advocate profile?
    - Topic Relevance (25%): How directly related to Autonomi's offering?
    - Reach Potential (15%): Engagement, follower influence
    - Timing (15%): Is conversation still active/fresh?
    - Conversation Stage (15%): Asking questions vs already decided
    """

    text = post.get("text", "").lower()
    engagement = post.get("engagement_total", 0)
    created_at = post.get("created_at", "")

    # --- ICP Match (0-100) ---
    icp_score = 0

    # High-value language patterns from ICP Profile
    high_value_terms = [
        "own my data",
        "data sovereignty",
        "self-sovereign",
        "privacy by design",
        "decentralized",
        "peer-to-peer",
        "no single point of failure",
        "big tech",
        "walled gardens",
        "surveillance capitalism",
        "self-hosting",
        "homelab",
        "cypherpunk",
        "open web",
        "the web we were promised",
        "digital rights",
        "data ownership",
    ]

    # Question/exploration signals (high value)
    question_signals = [
        "is there an alternative",
        "looking for",
        "anyone know",
        "what's actually",
        "recommendations for",
        "trying to find",
        "frustrated with",
        "tired of",
        "concerned about",
        "worried about",
    ]

    # Lower value signals
    low_value_terms = [
        "token price",
        "to the moon",
        "nft",
        "airdrop",
        "presale",
        "enterprise solution",
        "b2b",
        "roi",
        "kpi",
    ]

    # Calculate ICP match
    high_matches = sum(1 for term in high_value_terms if term in text)
    question_matches = sum(1 for term in question_signals if term in text)
    low_matches = sum(1 for term in low_value_terms if term in text)

    icp_score = min(100, (high_matches * 20) + (question_matches * 25))
    icp_score = max(0, icp_score - (low_matches * 30))

    # Baseline for matching our search terms at all
    if icp_score == 0:
        icp_score = 30  # They matched a query, so some baseline relevance

    # --- Topic Relevance (0-100) ---
    topic_score = 0

    # Direct relevance to what Autonomi offers
    direct_relevance = [
        "decentralized storage",
        "encrypted storage",
        "private storage",
        "data privacy",
        "end-to-end encryption",
        "self-encrypting",
        "no servers",
        "serverless",
        "permanent storage",
        "censorship resistant",
    ]

    # Adjacent/comparative topics
    adjacent_topics = [
        "ipfs",
        "filecoin",
        "storj",
        "sia",
        "nextcloud",
        "syncthing",
        "proton",
        "signal",
        "cloud storage",
        "google drive",
        "dropbox",
        "aws",
        "azure",
        "cloud costs",
    ]

    direct_matches = sum(1 for term in direct_relevance if term in text)
    adjacent_matches = sum(1 for term in adjacent_topics if term in text)

    topic_score = min(100, (direct_matches * 30) + (adjacent_matches * 15))
    if topic_score == 0:
        topic_score = 25  # Baseline for matching search query

    # --- Reach Potential (0-100) ---
    reach_score = 0

    if engagement >= 100:
        reach_score = 100
    elif engagement >= 50:
        reach_score = 80
    elif engagement >= 20:
        reach_score = 60
    elif engagement >= 10:
        reach_score = 40
    elif engagement >= 5:
        reach_score = 25
    else:
        reach_score = 10

    # --- Timing (0-100) ---
    timing_score = 80  # Default to good timing since we're searching recent

    # Could enhance with actual timestamp comparison

    # --- Conversation Stage (0-100) ---
    stage_score = 50  # Default

    # Questions and exploration = high value
    if any(
        q in text
        for q in ["?", "anyone", "looking for", "recommendations", "trying to"]
    ):
        stage_score = 85
    # Statements of frustration = good opportunity
    elif any(
        f in text for f in ["frustrated", "tired of", "hate", "annoyed", "sick of"]
    ):
        stage_score = 75
    # Already decided/using something = lower value
    elif any(d in text for d in ["i use", "switched to", "moved to", "loving"]):
        stage_score = 30

    # --- Calculate weighted total ---
    weights = {
        "icp_match": 0.30,
        "topic_relevance": 0.25,
        "reach_potential": 0.15,
        "timing": 0.15,
        "conversation_stage": 0.15,
    }

    total = (
        icp_score * weights["icp_match"]
        + topic_score * weights["topic_relevance"]
        + reach_score * weights["reach_potential"]
        + timing_score * weights["timing"]
        + stage_score * weights["conversation_stage"]
    )

    return {
        "total": round(total),
        "icp_match": icp_score,
        "topic_relevance": topic_score,
        "reach_potential": reach_score,
        "timing": timing_score,
        "conversation_stage": stage_score,
    }


def get_priority(score: int, config: dict) -> str:
    """Determine priority tier based on score."""
    thresholds = config.get("scorer", {}).get("thresholds", {})
    high_threshold = thresholds.get("high", 70)
    medium_threshold = thresholds.get("medium", 50)

    if score >= high_threshold:
        return "high"
    elif score >= medium_threshold:
        return "medium"
    else:
        return "low"


# =============================================================================
# BLUESKY PLATFORM
# =============================================================================


def get_bluesky_client(config: dict) -> "BlueskyClient":
    """Create and authenticate a Bluesky client."""
    if not ATPROTO_AVAILABLE:
        return None

    username = config.get("bluesky", {}).get("username", "")
    password = config.get("bluesky", {}).get("password", "")

    if not username or not password:
        return None

    try:
        client = BlueskyClient()
        client.login(username, password)
        return client
    except Exception as e:
        print(f"  Bluesky login failed: {e}")
        return None


def bluesky_search(client, query: str, limit: int = 25, lang: str = None) -> list:
    """Search Bluesky for posts matching a query."""
    if client is None:
        return []

    try:
        params = {"q": query, "limit": min(limit, 100), "sort": "latest"}
        if lang:
            params["lang"] = lang

        response = client.app.bsky.feed.search_posts(params)
        return response.posts if response and response.posts else []
    except Exception as e:
        print(f"  Error searching for '{query}': {e}")
        return []


def extract_bluesky_post(post) -> dict:
    """Extract relevant data from a Bluesky post object."""

    if hasattr(post, "record"):
        record = post.record
        author = post.author
        handle = author.handle if hasattr(author, "handle") else ""
        uri = post.uri if hasattr(post, "uri") else ""
        text = record.text if hasattr(record, "text") else ""
        created_at = record.created_at if hasattr(record, "created_at") else ""
        likes = post.like_count if hasattr(post, "like_count") else 0
        replies = post.reply_count if hasattr(post, "reply_count") else 0
        reposts = post.repost_count if hasattr(post, "repost_count") else 0
        author_name = author.display_name if hasattr(author, "display_name") else handle
    else:
        record = post.get("record", {})
        author = post.get("author", {})
        handle = author.get("handle", "")
        uri = post.get("uri", "")
        text = record.get("text", "")
        created_at = record.get("createdAt", "")
        likes = post.get("likeCount", 0)
        replies = post.get("replyCount", 0)
        reposts = post.get("repostCount", 0)
        author_name = author.get("displayName", handle)

    post_id = uri.split("/")[-1] if uri else ""
    web_url = (
        f"https://bsky.app/profile/{handle}/post/{post_id}"
        if handle and post_id
        else ""
    )

    return {
        "platform": "bluesky",
        "post_id": post_id,
        "url": web_url,
        "author_handle": handle,
        "author_name": author_name or handle,
        "text": text,
        "created_at": str(created_at),
        "likes": likes or 0,
        "replies": replies or 0,
        "reposts": reposts or 0,
        "engagement_total": (likes or 0) + (replies or 0) + (reposts or 0),
    }


def fetch_bluesky(config: dict) -> list:
    """Fetch all posts from Bluesky matching configured queries."""

    listener_config = config.get("listener", {}).get("bluesky", {})

    if not listener_config.get("enabled", False):
        print("Bluesky: Disabled in config")
        return []

    if not ATPROTO_AVAILABLE:
        print("Bluesky: atproto SDK not installed. Run: pip3 install atproto")
        return []

    queries = load_queries("bluesky")
    if not queries:
        print("Bluesky: No active queries")
        return []

    posts_per_query = listener_config.get("posts_per_query", 25)
    language = listener_config.get("language", "en")

    print(f"Bluesky: {len(queries)} queries, {posts_per_query} posts each")

    # Authenticate
    client = get_bluesky_client(config)
    if client is None:
        print("Bluesky: Authentication failed")
        return []

    # Fetch posts
    all_posts = []
    seen_ids = set()

    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {query}", end=" ")

        posts = bluesky_search(client, query, limit=posts_per_query, lang=language)
        print(f"-> {len(posts)} posts")

        for post in posts:
            extracted = extract_bluesky_post(post)
            extracted["matched_query"] = query

            # Deduplicate
            if extracted["post_id"] not in seen_ids:
                seen_ids.add(extracted["post_id"])
                all_posts.append(extracted)

        if i < len(queries):
            time.sleep(0.3)

    return all_posts


# =============================================================================
# YOUTUBE PLATFORM (via official YouTube Data API v3)
# =============================================================================

# Free tier: 10,000 quota units/day
# Search = 100 units, so ~100 searches/day free

import requests
from datetime import timedelta

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def get_published_after_date(listener_config: dict) -> str:
    """Get the publishedAfter date for YouTube API based on config."""
    days = listener_config.get("max_age_days", 90)  # Default 90 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_youtube(config: dict) -> list:
    """Fetch YouTube videos matching configured queries via YouTube Data API."""

    listener_config = config.get("listener", {}).get("youtube", {})

    if not listener_config.get("enabled", False):
        print("YouTube: Disabled in config")
        return []

    api_key = config.get("youtube", {}).get("api_key", "")
    if not api_key:
        print("YouTube: No API key in config. Get one from Google Cloud Console.")
        return []

    queries = load_queries("youtube")
    if not queries:
        print("YouTube: No active queries in queries/youtube.yaml")
        return []

    videos_per_query = listener_config.get("videos_per_query", 10)

    print(f"YouTube: {len(queries)} queries, {videos_per_query} videos each")

    all_videos = []
    seen_ids = set()

    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {query}", end=" ")

        try:
            # Search for videos
            search_url = f"{YOUTUBE_API_BASE}/search"
            params = {
                "key": api_key,
                "q": query,
                "part": "snippet",
                "type": "video",
                "maxResults": min(videos_per_query, 50),  # API max is 50
                "order": "date",  # Prioritise recent content
                "relevanceLanguage": "en",
                "publishedAfter": get_published_after_date(listener_config),
            }

            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            print(f"-> {len(items)} videos")

            # Get video IDs for statistics lookup
            video_ids = [
                item["id"]["videoId"]
                for item in items
                if "videoId" in item.get("id", {})
            ]

            # Fetch video statistics (views, likes, comments)
            stats = {}
            if video_ids:
                stats = fetch_youtube_stats(api_key, video_ids)

            for item in items:
                video_id = item.get("id", {}).get("videoId", "")
                if not video_id or video_id in seen_ids:
                    continue

                seen_ids.add(video_id)
                video_data = extract_youtube_video(item, query, stats.get(video_id, {}))
                all_videos.append(video_data)

        except Exception as e:
            print(f"-> ERROR: {e}")
            continue

        if i < len(queries):
            time.sleep(0.5)

    return all_videos


def fetch_youtube_stats(api_key: str, video_ids: list) -> dict:
    """Fetch statistics for a list of video IDs."""

    stats_url = f"{YOUTUBE_API_BASE}/videos"
    params = {
        "key": api_key,
        "id": ",".join(video_ids),
        "part": "statistics",
    }

    try:
        response = requests.get(stats_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        result = {}
        for item in data.get("items", []):
            vid = item.get("id", "")
            stats = item.get("statistics", {})
            result[vid] = {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
            }
        return result
    except:
        return {}


def extract_youtube_video(item: dict, query: str, stats: dict) -> dict:
    """Extract relevant data from a YouTube search result."""

    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId", "")

    title = snippet.get("title", "")
    description = snippet.get("description", "")
    channel_name = snippet.get("channelTitle", "")
    channel_id = snippet.get("channelId", "")
    published_at = snippet.get("publishedAt", "")

    url = f"https://www.youtube.com/watch?v={video_id}"
    channel_url = f"https://www.youtube.com/channel/{channel_id}" if channel_id else ""

    views = stats.get("views", 0)
    likes = stats.get("likes", 0)
    comments = stats.get("comments", 0)

    return {
        "platform": "youtube",
        "post_id": video_id,
        "url": url,
        "author_handle": channel_name,
        "author_name": channel_name,
        "text": f"**{title}**\n\n{description}" if description else f"**{title}**",
        "title": title,
        "description": description,
        "created_at": published_at,
        "likes": likes,
        "replies": comments,
        "reposts": 0,
        "views": views,
        "engagement_total": likes + comments,
        "channel_url": channel_url,
        "matched_query": query,
    }


# =============================================================================
# DAILY BRIEFING GENERATION
# =============================================================================


def generate_briefing(
    scored_posts: list, config: dict, stats: dict, max_results: int = 10
) -> str:
    """Generate the Daily Briefing markdown content."""

    now = datetime.now()
    date_str = now.strftime("%Y-%b-%d")

    # Sort all posts by score descending, take top N
    sorted_posts = sorted(scored_posts, key=lambda x: x["score"]["total"], reverse=True)
    top_posts = sorted_posts[:max_results]

    # Count priorities in full set
    high_count = sum(1 for p in scored_posts if p["priority"] == "high")
    medium_count = sum(1 for p in scored_posts if p["priority"] == "medium")
    low_count = sum(1 for p in scored_posts if p["priority"] == "low")

    # Build briefing
    lines = []

    # Frontmatter
    lines.append("---")
    lines.append(f"date: {date_str}")
    lines.append(f"generated: {now.isoformat()}")
    lines.append(f"posts_scanned: {stats['total_fetched']}")
    lines.append(f"showing: {len(top_posts)}")
    lines.append(f"high_priority_total: {high_count}")
    lines.append(f"medium_priority_total: {medium_count}")
    lines.append("status: unreviewed")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"Scanned **{stats['total_fetched']}** posts across {stats['platforms']}."
    )
    lines.append(f"Showing top **{len(top_posts)}** ranked by score.")
    lines.append("")
    if high_count > 0:
        lines.append(f"**{high_count}** high-signal posts found in this batch.")
    lines.append("")

    # Top 10 Posts
    lines.append("## Top Opportunities")
    lines.append("")

    for i, post in enumerate(top_posts, 1):
        # Priority badge
        priority = post["priority"]
        if priority == "high":
            badge = "HIGH SIGNAL"
        elif priority == "medium":
            badge = "Medium"
        else:
            badge = "Low"

        lines.append(
            f"### {i}. @{post['author_handle']} — Score: {post['score']['total']} ({badge})"
        )
        lines.append("")
        lines.append(
            f"**{post['author_name']}** · {post['likes']} likes · {post['replies']} replies · {post['reposts']} reposts"
        )
        lines.append("")
        # Full post text (no truncation)
        lines.append(f"> {post['text']}")
        lines.append("")
        lines.append(f"**Matched query:** `{post['matched_query']}`")
        lines.append(f"**Link:** {post['url']}")
        lines.append("")
        lines.append(f"<details><summary>Score breakdown</summary>")
        lines.append("")
        lines.append(f"| Dimension | Score |")
        lines.append(f"|-----------|-------|")
        lines.append(f"| ICP Match | {post['score']['icp_match']} |")
        lines.append(f"| Topic Relevance | {post['score']['topic_relevance']} |")
        lines.append(f"| Reach Potential | {post['score']['reach_potential']} |")
        lines.append(f"| Timing | {post['score']['timing']} |")
        lines.append(f"| Conversation Stage | {post['score']['conversation_stage']} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Stats
    lines.append("## Run Statistics")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Platforms | {stats['platforms']} |")
    lines.append(f"| Queries run | {stats['queries_run']} |")
    lines.append(f"| Posts scanned | {stats['total_fetched']} |")
    lines.append(f"| High signal (70+) | {high_count} |")
    lines.append(f"| Medium signal (50-69) | {medium_count} |")
    lines.append(f"| Low signal (<50) | {low_count} |")
    lines.append("")

    return "\n".join(lines)


def save_briefing(content: str, config: dict) -> Path:
    """Save the daily briefing to the Daily Review folder."""

    project_root = get_project_root()
    review_path = project_root / "Daily Review"
    review_path.mkdir(parents=True, exist_ok=True)

    # Always include timestamp so each run creates a new file
    now = datetime.now()
    date_str = now.strftime("%Y-%b-%d")
    time_str = now.strftime("%H%M")
    filename = f"{date_str} - Daily Briefing ({time_str}).md"
    filepath = review_path / filename

    filepath.write_text(content, encoding="utf-8")
    return filepath


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Marketing OS - Generate Daily Briefing from social signals"
    )
    parser.add_argument(
        "--platform",
        "-p",
        choices=["bluesky", "youtube", "twitter", "all"],
        default="all",
        help="Which platform to query (default: all enabled)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be fetched without making API calls",
    )

    args = parser.parse_args()

    # Load config and context
    config = load_config()
    icp_context = load_context_file("ICP Profile.md")
    positioning_context = load_context_file("Positioning.md")

    print("\n" + "=" * 60)
    print("MARKETING OS - DAILY BRIEFING")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.dry_run:
        print("Mode: DRY RUN")
        print("=" * 60 + "\n")
        return

    # Fetch posts from enabled platforms
    all_posts = []
    platforms_run = []
    queries_run = 0

    if args.platform in ["bluesky", "all"]:
        bluesky_posts = fetch_bluesky(config)
        all_posts.extend(bluesky_posts)
        if bluesky_posts:
            platforms_run.append("Bluesky")
            queries_run += len(load_queries("bluesky"))

    if args.platform in ["youtube", "all"]:
        youtube_videos = fetch_youtube(config)
        all_posts.extend(youtube_videos)
        if youtube_videos:
            platforms_run.append("YouTube")
            queries_run += len(load_queries("youtube"))

    # Twitter would go here when enabled

    print(f"\nTotal fetched: {len(all_posts)} unique posts")

    if not all_posts:
        print("No posts found. Check your configuration.")
        return

    # Score all posts
    print("Scoring posts against ICP criteria...")
    scored_posts = []

    for post in all_posts:
        score = score_post(post, icp_context, positioning_context)
        priority = get_priority(score["total"], config)

        scored_posts.append({**post, "score": score, "priority": priority})

    # Count priorities
    high_count = sum(1 for p in scored_posts if p["priority"] == "high")
    medium_count = sum(1 for p in scored_posts if p["priority"] == "medium")
    low_count = sum(1 for p in scored_posts if p["priority"] == "low")

    print(f"  High: {high_count} | Medium: {medium_count} | Low: {low_count}")

    # Generate briefing
    stats = {
        "platforms": ", ".join(platforms_run) if platforms_run else "None",
        "queries_run": queries_run,
        "total_fetched": len(all_posts),
        "unique_posts": len(all_posts),
    }

    briefing_content = generate_briefing(scored_posts, config, stats)

    # Save briefing
    filepath = save_briefing(briefing_content, config)

    print(f"\n{'=' * 60}")
    print("COMPLETE")
    print("=" * 60)
    print(f"Daily Briefing saved to:")
    print(f"  {filepath}")
    print(f"\nHigh priority: {high_count} opportunities")
    print(f"Medium priority: {medium_count} opportunities")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
