#!/usr/bin/env python3
"""
scrape.py
─────────
Searches DuckDuckGo for a TikTok video matching the given query,
picks the first video result, downloads the unwatermarked MP4 using yt-dlp, 
and writes:
  output/video.mp4
  output/meta.json

Usage:
  python scrape.py "IP68 Shellbox Waterproof Case For Samsung"
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

# User-Agent for yt-dlp downloading
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def find_video_url_via_duckduckgo(query: str) -> dict:
    """
    Bypasses TikTok's search protections by using DuckDuckGo HTML search.
    Searches for: site:tiktok.com "query"
    """
    # Adding 'site:tiktok.com' restricts results to TikTok
    search_query = f'site:tiktok.com {query}'
    encoded = urllib.parse.quote(search_query)
    
    # Using the HTML-only version of DDG avoids JavaScript requirements
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    
    print(f"[scraper] Fetching DDG search: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        
    # Extract direct TikTok video URLs from the raw HTML
    video_urls = re.findall(r'(https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+)', html)
    
    if not video_urls:
        raise RuntimeError(
            f"Could not find any TikTok URLs via DuckDuckGo for: '{query}'. "
            "Try shortening or simplifying the search terms."
        )
        
    # Get the first unique URL and decode it (DDG sometimes URL-encodes the links)
    best_url = urllib.parse.unquote(video_urls[0])
    
    print(f"[scraper] Found via DDG: {best_url}")
    return {"source_url": best_url, "title": query}


def download_video(source_url: str, out_dir: str) -> str:
    """Download unwatermarked MP4 to out_dir/video.mp4 using yt-dlp."""
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

    # 1. Search via DuckDuckGo
    try:
        meta = find_video_url_via_duckduckgo(QUERY)
    except Exception as e:
        print(f"[scraper] Search failed. Error: {e}")
        sys.exit(1)

    # 2. Download via yt-dlp
    print(f"[scraper] Downloading: {meta['source_url']}")
    try:
        video_path = download_video(meta["source_url"], OUTPUT_DIR)
        print(f"[scraper] Downloaded to: {video_path}")
    except Exception as e:
        print(f"[scraper] Download failed. Error: {e}")
        sys.exit(1)

    # 3. Save Metadata
    meta["video_filename"] = "video.mp4"
    meta_path = os.path.join(OUTPUT_DIR, "meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[scraper] Done. Saved data to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
