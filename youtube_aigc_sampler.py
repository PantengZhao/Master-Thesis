"""
Basic YouTube search + stats collector for manual screening.

Steps:
1) Search a single date window for three generic queries.
2) Deduplicate video_ids across queries.
3) Fetch view/like/comment counts.
4) Add month_bucket and export to CSV for manual review.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
from googleapiclient.discovery import build
from tqdm import tqdm

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Replace with your key if needed
API_KEY = "AIzaSyCnR1WTqcxp-irDIXcD53KvcrstX4EOk10"

# Single-layer queries
QUERIES = [
    "AI tools for content creation",
    "AI tools for content creators",
    "AI workflow for content creation",
]


def iso_date(y: int, m: int, d: int) -> str:
    """Convert to ISO format with Z for YouTube API."""
    return datetime(y, m, d).isoformat("T") + "Z"


# Time window: 2025-08-01 ~ 2025-11-22
START_DATE = iso_date(2025, 8, 1)
END_DATE = iso_date(2025, 11, 22)


# --------------------------------------------------------------------------- #
# API helpers
# --------------------------------------------------------------------------- #

def build_client():
    """Create a YouTube Data API client."""
    return build("youtube", "v3", developerKey=API_KEY)


def search_videos_for_query(youtube, query: str, max_results: int = 40) -> List[Dict[str, str]]:
    """
    Search one query across the whole time window.

    Default order is relevance; change to "viewCount" to sort by views.
    """
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results,
        publishedAfter=START_DATE,
        publishedBefore=END_DATE,
        order="relevance",
    )
    response = request.execute()

    rows: List[Dict[str, str]] = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        rows.append(
            {
                "video_id": item["id"]["videoId"],
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "publish_date": snippet.get("publishedAt"),
                "title": snippet.get("title"),
                "description": snippet.get("description", ""),
                "query": query,
            }
        )
    return rows


def fetch_video_details(youtube, video_ids: List[str]) -> pd.DataFrame:
    """
    Fetch full descriptions plus view/like/comment counts in batches of up to 50 IDs.
    """
    detail_rows: List[Dict[str, str]] = []
    for i in tqdm(range(0, len(video_ids), 50), desc="Fetching details"):
        batch = video_ids[i : i + 50]
        request = youtube.videos().list(part="snippet,statistics", id=",".join(batch))
        response = request.execute()
        for item in response.get("items", []):
            vid = item.get("id")
            s = item.get("statistics", {})
            snippet = item.get("snippet", {})
            detail_rows.append(
                {
                    "video_id": vid,
                    "view_count": int(s.get("viewCount", 0)),
                    "like_count": int(s.get("likeCount", 0)),
                    "comment_count": int(s.get("commentCount", 0)),
                    "full_title": snippet.get("title", ""),
                    "full_description": snippet.get("description", ""),
                    "publish_date_full": snippet.get("publishedAt", ""),
                }
            )
    return pd.DataFrame(detail_rows)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    youtube = build_client()

    # 1) Search each query
    all_rows: List[Dict[str, str]] = []
    for q in QUERIES:
        print(f"Searching for query: {q}")
        all_rows.extend(search_videos_for_query(youtube, q, max_results=40))

    df = pd.DataFrame(all_rows)
    print("Raw candidates (before dedupe):", df.shape[0])

    # 2) Deduplicate across queries
    df = df.drop_duplicates(subset="video_id").reset_index(drop=True)
    print("After dedupe:", df.shape[0])

    if df.empty:
        print("No videos found in the specified window/queries.")
        return

    # 3) Fetch full descriptions and statistics
    details_df = fetch_video_details(youtube, df["video_id"].tolist())
    df = df.merge(details_df, on="video_id", how="left")

    # Prefer full_description/full_title when available
    df["description"] = df["full_description"].fillna(df["description"])
    df["title"] = df["full_title"].fillna(df["title"])
    df["publish_date"] = df["publish_date_full"].fillna(df["publish_date"])
    df = df.drop(columns=["full_description", "full_title", "publish_date_full"], errors="ignore")

    # 4) Add month bucket
    df["month_bucket"] = df["publish_date"].str.slice(0, 7)

    # 5) Save CSV for manual review
    df.to_csv("youtube_candidates_basic.csv", index=False, encoding="utf-8-sig")
    print("Saved to youtube_candidates_basic.csv")


if __name__ == "__main__":
    main()
