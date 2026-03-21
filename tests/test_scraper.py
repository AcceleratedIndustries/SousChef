"""Tests for the URL scraper module."""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_scrape_recipe_with_recipe_scrapers(tmp_path):
    """Test scrape_recipe with a mocked recipe_scrapers scraper object."""
    from souschef.scraper.url import scrape_recipe

    mock_scraper = MagicMock()
    mock_scraper.title.return_value = "Chocolate Cake"
    mock_scraper.ingredients.return_value = ["2 cups flour", "1 cup sugar"]
    mock_scraper.instructions_list.return_value = ["Mix ingredients", "Bake at 350F"]
    mock_scraper.image.return_value = "https://example.com/cake.jpg"
    mock_scraper.total_time.return_value = 60
    mock_scraper.yields.return_value = "4 servings"

    with patch("souschef.scraper.url.scrape_html", return_value=mock_scraper):
        result = scrape_recipe("https://example.com/recipe", "<html></html>")

    assert result["title"] == "Chocolate Cake"
    assert result["ingredients_raw"] == ["2 cups flour", "1 cup sugar"]
    assert result["instructions"] == ["Mix ingredients", "Bake at 350F"]
    assert result["image_url"] == "https://example.com/cake.jpg"
    assert result["total_time_minutes"] == 60
    assert result["servings"] == 4
    assert result["source_url"] == "https://example.com/recipe"


def test_download_image_success(tmp_path):
    """Test download_image with a successful HTTP response."""
    from souschef.scraper.url import download_image

    fake_bytes = b"fake image data"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = fake_bytes
    mock_response.headers = {"content-type": "image/jpeg"}

    with patch("souschef.scraper.url.httpx.get", return_value=mock_response):
        result = download_image("https://example.com/cake.jpg", tmp_path)

    assert result is not None
    assert isinstance(result, Path)
    assert result.exists()
    assert result.read_bytes() == fake_bytes

    # Verify filename is sha256 hash (first 12 chars) with .jpg extension
    expected_hash = hashlib.sha256(b"https://example.com/cake.jpg").hexdigest()[:12]
    assert result.stem == expected_hash
    assert result.suffix == ".jpg"


def test_download_image_failure(tmp_path):
    """Test download_image returns None when httpx raises an exception."""
    from souschef.scraper.url import download_image

    with patch("souschef.scraper.url.httpx.get", side_effect=Exception("Network error")):
        result = download_image("https://example.com/cake.jpg", tmp_path)

    assert result is None
