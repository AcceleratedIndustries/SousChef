"""URL-based recipe scraping utilities."""
import hashlib
import re
from pathlib import Path
from typing import Optional

import httpx
from recipe_scrapers import scrape_html

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
}


def scrape_recipe(url: str, html: str) -> dict:
    """Scrape a recipe from HTML content.

    Uses recipe_scrapers to extract recipe data. Each field is wrapped in
    try/except so failures return None for that field gracefully.

    Args:
        url: The original URL of the recipe page.
        html: The HTML content of the recipe page.

    Returns:
        Dict with keys: title, ingredients_raw, instructions, image_url,
        total_time_minutes, servings, source_url.
    """
    scraper = scrape_html(html=html, org_url=url)

    def safe(fn):
        try:
            return fn()
        except Exception:
            return None

    title = safe(scraper.title)
    ingredients_raw = safe(scraper.ingredients)
    instructions = safe(scraper.instructions_list)
    image_url = safe(scraper.image)
    total_time_minutes = safe(scraper.total_time)

    servings = None
    raw_yields = safe(scraper.yields)
    if raw_yields is not None:
        match = re.search(r"\d+", str(raw_yields))
        if match:
            servings = int(match.group())

    return {
        "title": title,
        "ingredients_raw": ingredients_raw,
        "instructions": instructions,
        "image_url": image_url,
        "total_time_minutes": total_time_minutes,
        "servings": servings,
        "source_url": url,
    }


def download_image(url: str, images_dir: Path) -> Optional[Path]:
    """Download an image from a URL and save it to images_dir.

    Uses the sha256 hash of the URL (first 12 chars) as the filename.
    Extension is determined from the content-type header.

    Args:
        url: The image URL to download.
        images_dir: Directory to save the image in.

    Returns:
        Path to the saved image on success, None on any exception.
    """
    try:
        response = httpx.get(url, timeout=30, follow_redirects=True, headers=_HEADERS)
        content_type = response.headers.get("content-type", "")

        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"
        elif "gif" in content_type:
            ext = ".gif"
        else:
            ext = ".jpg"

        filename = hashlib.sha256(url.encode()).hexdigest()[:12] + ext
        output_path = Path(images_dir) / filename
        output_path.write_bytes(response.content)
        return output_path
    except Exception:
        return None


def fetch_and_scrape(url: str, images_dir: Path) -> dict:
    """Fetch a URL, scrape the recipe, and download the image.

    Args:
        url: The recipe page URL to fetch and scrape.
        images_dir: Directory to save the downloaded image in.

    Returns:
        Dict with all scraped recipe fields plus image_path (Path or None).
    """
    response = httpx.get(url, timeout=30, follow_redirects=True, headers=_HEADERS)
    html = response.text

    result = scrape_recipe(url, html)

    image_path = None
    if result.get("image_url"):
        image_path = download_image(result["image_url"], images_dir)

    result["image_path"] = image_path
    return result
