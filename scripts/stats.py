"""stats.py — Compute knowledge growth statistics from wiki pages."""
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"


def _detect_source_type(content: str) -> str:
    # Check for explicit SourceType metadata first
    m = re.search(r"\*\*SourceType:\*\*\s*(\w+)", content, re.IGNORECASE)
    if m:
        return m.group(1).lower()

    # Detect from URLs in content
    urls = re.findall(r"https?://[^\s\)\"\'\]]+", content)
    for url in urls:
        u = url.lower()
        if "youtube.com" in u or "youtu.be" in u:
            return "youtube"
        if "twitter.com" in u or "x.com" in u:
            return "twitter"
        if "xiaohongshu.com" in u or "xhslink.com" in u or "redbook" in u:
            return "xiaohongshu"
    return "article"


def compute_stats() -> dict:
    pages = list(WIKI.rglob("*.md"))
    total = len(pages)

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    year_ago = now - timedelta(weeks=52)

    weekly_new = 0
    prev_weekly = 0
    daily_counts: dict[str, int] = defaultdict(int)
    source_dist: dict[str, int] = defaultdict(int)
    tag_counts: dict[str, int] = defaultdict(int)
    type_counts: dict[str, int] = defaultdict(int)

    for p in pages:
        mtime = datetime.fromtimestamp(p.stat().st_mtime)

        if mtime >= week_ago:
            weekly_new += 1
        elif mtime >= two_weeks_ago:
            prev_weekly += 1

        if mtime >= year_ago:
            date_key = mtime.strftime("%Y-%m-%d")
            daily_counts[date_key] += 1

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            source_dist[_detect_source_type(content)] += 1

            # Knowledge type distribution
            type_m = re.search(r"\*\*Type:\*\*\s*(\w+)", content)
            if type_m:
                type_counts[type_m.group(1).lower()] += 1

            # Extract tags from **Tags:** line
            tags_m = re.search(r"\*\*Tags:\*\*\s*(.+)", content)
            if tags_m:
                for tag in re.findall(r"[#\w]+", tags_m.group(1)):
                    tag = tag.lstrip("#")
                    if len(tag) > 1:
                        tag_counts[tag] += 1
        except Exception:
            pass

    # Weekly delta percentage
    if prev_weekly > 0:
        delta_pct = round((weekly_new - prev_weekly) / prev_weekly * 100)
    elif weekly_new > 0:
        delta_pct = 100
    else:
        delta_pct = 0

    return {
        "total": total,
        "weekly_new": weekly_new,
        "weekly_prev": prev_weekly,
        "weekly_delta_pct": delta_pct,
        "daily_counts": dict(daily_counts),
        "source_dist": dict(source_dist),
        "type_dist": dict(type_counts),
        "top_tags": sorted(tag_counts.items(), key=lambda x: -x[1])[:20],
    }
