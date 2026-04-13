#!/usr/bin/env python3
"""
scraper/scrape.py
─────────────────
Searches TikTok for the given query, picks the highest-view video,
downloads the unwatermarked MP4, and writes:
  output/video.mp4
  output/meta.json   ← { title, source_url, view_count, video_url }

Usage:
  python scraper/scrape.py "posture corrector"
"""

import sys
import os
import json
import shutil

import yt_dlp


QUERY = sys.argv[1] if len(sys.argv) > 1 else "trending product"
OUTPUT_DIR = "output"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tiktok.com/",
}


def search_top_video(query: str) -> dict:
    """Return metadata for the highest-view TikTok video matching query."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": 8,
        "user_agent": USER_AGENT,
        "http_headers": HEADERS,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"tiktoksearch:{query}", download=False)

    entries = [e for e in (info.get("entries") or []) if e and e.get("url")]
    if not entries:
        raise RuntimeError(f"No TikTok results found for: {query}")

    best = max(entries, key=lambda e: e.get("view_count") or 0)
    return {
        "source_url": best.get("url") or best.get("webpage_url"),
        "title": best.get("title", query),
        "view_count": best.get("view_count"),
    }


def download_video(source_url: str, out_dir: str) -> str:
    """Download unwatermarked MP4 to out_dir/video.mp4. Returns final path."""
    os.makedirs(out_dir, exist_ok=True)
    out_template = os.path.join(out_dir, "video.%(ext)s")

    opts = {
        "quiet": False,
        "no_warnings": True,
        "user_agent": USER_AGENT,
        "http_headers": HEADERS,
        # Prefer mp4, no watermark format
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "extractor_args": {
            "tiktok": {"webpage_download": True}
        },
        # Merge streams with ffmpeg if needed
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "socket_timeout": 60,
        "retries": 5,
        "fragment_retries": 5,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([source_url])

    # Find the output file
    for fname in os.listdir(out_dir):
        if fname.startswith("video") and fname.endswith(".mp4"):
            return os.path.join(out_dir, fname)

    raise FileNotFoundError("Download completed but video.mp4 not found in output/")


def main():
    print(f"[scraper] Query: {QUERY}")

    meta = search_top_video(QUERY)
    print(f"[scraper] Top video: {meta['title']} ({meta['view_count']} views)")
    print(f"[scraper] Source URL: {meta['source_url']}")

    video_path = download_video(meta["source_url"], OUTPUT_DIR)
    print(f"[scraper] Downloaded to: {video_path}")

    # Write metadata so n8n can read it from the artifact
    meta["video_filename"] = "video.mp4"
    meta_path = os.path.join(OUTPUT_DIR, "meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[scraper] meta.json written: {json.dumps(meta, indent=2)}")


if __name__ == "__main__":
    main()
