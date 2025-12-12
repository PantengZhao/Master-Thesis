"""
Fetch transcripts for manually selected core videos (Core_video = 1).

Usage:
1) Export your Numbers sheet to CSV (e.g., youtube_core.csv) with columns:
   - video_id
   - Core_video (1 = need transcript)
   - any other metadata you want to carry through
2) Run:
   python fetch_core_transcripts.py --input youtube_core.csv --output youtube_core_transcripts.csv
"""

from __future__ import annotations

import argparse
from typing import List

import pandas as pd
from tqdm import tqdm
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

LANGS: List[str] = ["en", "en-US", "en-GB"]


def load_core_csv(path: str) -> pd.DataFrame:
    """
    Load CSV exported from Numbers.

    Numbers often uses ';' as delimiter and puts the sheet name on the first line.
    """
    try:
        df = pd.read_csv(path, sep=";", dtype=str, engine="python", skiprows=1)
    except Exception:
        df = pd.read_csv(path, dtype=str)

    # Drop completely empty columns (e.g., trailing delimiter)
    df = df.dropna(axis=1, how="all")
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    return df


def get_transcript(video_id: str) -> str:
    """Fetch transcript text; return empty string if unavailable."""
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=LANGS)
        return " ".join(getattr(entry, "text", "") for entry in fetched).strip()
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        # Fall back to generated transcripts if available
        try:
            transcripts = api.list(video_id)
            gen = transcripts.find_generated_transcript(LANGS)
            return " ".join(getattr(entry, "text", "") for entry in gen.fetch()).strip()
        except Exception:
            return ""
    except Exception:
        # Any other unexpected error: return empty
        return ""


def main():
    parser = argparse.ArgumentParser(description="Fetch transcripts for Core_video=1 rows.")
    parser.add_argument("--input", default="youtube_core.csv", help="Input CSV exported from Numbers")
    parser.add_argument("--output", default="youtube_core_transcripts.csv", help="Output CSV with transcripts")
    args = parser.parse_args()

    df = load_core_csv(args.input)
    if "Core_video" not in df.columns:
        raise ValueError("Input CSV must contain a 'Core_video' column.")
    if "video_id" not in df.columns:
        raise ValueError("Input CSV must contain a 'video_id' column.")

    core_df = df[df["Core_video"].astype(str) == "1"].copy()
    if core_df.empty:
        print("No rows with Core_video = 1 found.")
        return

    transcripts = []
    for vid in tqdm(core_df["video_id"], desc="Fetching transcripts", unit="video"):
        transcripts.append(get_transcript(vid))

    core_df["transcript"] = transcripts

    # Merge transcripts back to all rows (optional)
    merged = df.merge(core_df[["video_id", "transcript"]], on="video_id", how="left")

    merged.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved with transcripts to {args.output}")


if __name__ == "__main__":
    main()
