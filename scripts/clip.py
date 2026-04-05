"""
clip.py — fetch an article from a URL, extract text and download images.
"""
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:60]


def extract_image_urls(html: str, base_url: str) -> list[str]:
    """Extract significant image URLs from raw HTML."""
    seen = set()
    urls = []
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE):
        src = m.group(1).strip()
        if not src or src.startswith("data:") or src in seen:
            continue
        seen.add(src)
        absolute = urljoin(base_url, src)
        skip_tokens = {"logo", "icon", "pixel", "spacer", "avatar", "badge", "1x1", "tracking"}
        if any(t in absolute.lower() for t in skip_tokens):
            continue
        urls.append(absolute)
    return urls[:12]


def download_image(url: str, dest: Path) -> bool:
    """Download image to dest. Returns True on success."""
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and len(resp.content) > 2000:
                dest.write_bytes(resp.content)
                return True
    except Exception:
        pass
    return False


def clip(url: str, raw_dir: Path) -> dict:
    """
    Fetch article from URL, save as .md in raw_dir/articles/.
    Downloads images to raw_dir/images/.
    Returns {title, path, images_saved, error}.
    """
    articles_dir = raw_dir / "articles"
    images_dir = raw_dir / "images"
    articles_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        downloaded = trafilatura.fetch_url(url)
    except Exception as e:
        return {"error": f"Failed to fetch: {e}"}

    if not downloaded:
        return {"error": "Could not download page (may require login or JS rendering)"}

    content = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_links=True,
        include_images=False,
        no_fallback=False,
    )
    if not content:
        return {"error": "Could not extract article content"}

    meta = trafilatura.extract_metadata(downloaded)
    title = (meta.title if meta and meta.title else None) or urlparse(url).netloc or "Untitled"
    date_str = meta.date if meta and meta.date else ""

    # Download images, replace URLs with local paths in content
    image_urls = extract_image_urls(downloaded, url)
    images_saved = []
    slug = slugify(title)
    for i, img_url in enumerate(image_urls):
        ext = Path(urlparse(img_url).path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            ext = ".jpg"
        filename = f"{slug}-img{i + 1}{ext}"
        dest = images_dir / filename
        if download_image(img_url, dest):
            images_saved.append(filename)
            content = content.replace(img_url, f"../images/{filename}")

    # Build markdown
    md = f"# {title}\n\n"
    if date_str:
        md += f"**Date:** {date_str}  \n"
    md += f"**Source:** {url}\n\n---\n\n{content}\n"

    # Avoid overwriting existing files
    out_path = articles_dir / f"{slug}.md"
    if out_path.exists():
        n = 2
        while (articles_dir / f"{slug}-{n}.md").exists():
            n += 1
        out_path = articles_dir / f"{slug}-{n}.md"

    out_path.write_text(md, encoding="utf-8")

    return {
        "title": title,
        "path": str(out_path.relative_to(raw_dir.parent)),
        "filename": out_path.name,
        "images_saved": len(images_saved),
        "images": images_saved,
        "error": None,
    }
