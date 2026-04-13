#!/usr/bin/env python3
"""
scrape.py
─────────
Searches TikTok for the given query via web search URL,
picks the first video result, downloads the unwatermarked MP4, and writes:
  output/video.mp4
  output/meta.json

Usage:
  python scrape.py "posture corrector"
"""

import sys
import os
import json
import re
import urllib.request
import urllib.parse

import yt_dlp

QUERY = sys.argv[1] if len(sys.argv) > 1 else "trending product"
OUTPUT_DIR = "output"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tiktok.com/",
}


def find_video_url_via_search(query: str) -> dict:
    """
    Fetch TikTok search results page and extract the first video URL.
    Returns dict with source_url and title.
    """
    encoded = urllib.parse.quote(query)
    search_url = f"https://www.tiktok.com/search/video?q={encoded}"

    print(f"[scraper] Fetching search page: {search_url}")

    req = urllib.request.Request(search_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    # Extract video URLs from the HTML — TikTok embeds them as /@user/video/ID
    video_ids = re.findall(r'href="(https://www\.tiktok\.com/@[^"]+/video/\d+)', html)

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in video_ids:
        clean = url.split("?")[0]
        if clean not in seen:
            seen.add(clean)
            unique_urls.append(clean)

    if not unique_urls:
        raise RuntimeError(
            f"No TikTok video URLs found in search results for: '{query}'. "
            "TikTok may have blocked the request or changed their HTML structure."
        )

    best_url = unique_urls[0]
    print(f"[scraper] Found {len(unique_urls)} videos, using: {best_url}")
    return {"source_url": best_url, "title": query}


def find_video_url_via_ytdlp_search(query: str) -> dict:
    """
    Alternative: use yt-dlp's ytsearch on YouTube to find a TikTok-style
    UGC video if TikTok direct search is blocked.
    Falls back gracefully.
    """
    # Try a direct TikTok search URL as a playlist
    encoded = urllib.parse.quote(query)
    search_url = f"https://www.tiktok.com/search/video?q={encoded}"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": 5,
        "user_agent": USER_AGENT,
        "http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.tiktok.com/",
        },
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(search_url, download=False)

    entries = [e for e in (info.get("entries") or []) if e and e.get("url")]
    if not entries:
        raise RuntimeError(f"yt-dlp found no results at search URL for: {query}")

    best = entries[0]
    url = best.get("url") or best.get("webpage_url")
    return {"source_url": url, "title": best.get("title", query)}


def download_video(source_url: str, out_dir: str) -> str:
    """Download unwatermarked MP4 to out_dir/video.mp4."""
    os.makedirs(out_dir, exist_ok=True)
    out_template = os.path.join(out_dir, "video.%(ext)s")

    opts = {
        "quiet": False,
        "no_warnings": True,
        "user_agent": USER_AGENT,
        "http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.tiktok.com/",
        },
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "socket_timeout": 60,
        "retries": 5,
        "fragment_retries": 5,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([source_url])

    for fname in os.listdir(out_dir):
        if fname.startswith("video") and fname.endswith(".mp4"):
            return os.path.join(out_dir, fname)

    raise FileNotFoundError("Download completed but video.mp4 not found in output/")


def main():
    print(f"[scraper] Query: {QUERY}")

    # Try method 1: yt-dlp with TikTok search URL
    meta = None
    try:
        meta = find_video_url_via_ytdlp_search(QUERY)
        print(f"[scraper] Found via yt-dlp search: {meta['source_url']}")
    except Exception as e:
        print(f"[scraper] yt-dlp search failed ({e}), trying HTML scrape...")

    # Try method 2: raw HTML scrape of TikTok search page
    if not meta:
        try:
            meta = find_video_url_via_search(QUERY)
        except Exception as e:
            raise RuntimeError(f"Both search methods failed. Last error: {e}")

    print(f"[scraper] Downloading: {meta['source_url']}")
    video_path = download_video(meta["source_url"], OUTPUT_DIR)
    print(f"[scraper] Downloaded to: {video_path}")

    meta["video_filename"] = "video.mp4"
    meta_path = os.path.join(OUTPUT_DIR, "meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[scraper] Done. meta.json: {json.dumps(meta, indent=2)}")


if __name__ == "__main__":
    main()
