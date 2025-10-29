"""
Source-specific EPUB metadata transformers

Each source can provide a transformer function that converts their source_data
into a standardized metadata format for EPUB writing.
"""

from datetime import datetime
from typing import Optional


def storytel_transformer(details: dict) -> dict:
    """
    Transform Storytel book details JSON into standardized EPUB metadata format

    :param details: Storytel book details JSON
    :return: Standardized metadata dict
    """
    # Extract ebook format
    ebook_format = None
    for fmt in details.get("formats", []):
        if fmt.get("type") == "ebook":
            ebook_format = fmt
            break

    metadata = {
        "title": details.get("title"),
        "original_title": details.get("originalTitle"),
        "authors": [author.get("name", "") for author in details.get("authors", [])],
        "translators": [translator.get("name", "") for translator in details.get("translators", [])],
        "description": details.get("description"),
        "language": details.get("language"),
        "category": details.get("category", {}).get("name"),
        "tags": [tag.get("name", "") for tag in details.get("tags", [])[:10]],  # Max 10
    }

    # Ebook-specific metadata
    if ebook_format:
        metadata["publisher"] = ebook_format.get("publisher", {}).get("name")
        metadata["isbn"] = ebook_format.get("isbn")

        release_date = ebook_format.get("releaseDate")
        if release_date:
            # Format as YYYY-MM-DD
            date_obj = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
            metadata["release_date"] = date_obj.strftime("%Y-%m-%d")

    # Series info
    series_info = details.get("seriesInfo")
    if series_info:
        metadata["series_name"] = series_info.get("name")
        metadata["series_index"] = series_info.get("orderInSeries")

    return metadata


def nextory_transformer(details: dict) -> dict:
    """
    Transform Nextory book details JSON into standardized EPUB metadata format

    :param details: Nextory book details JSON
    :return: Standardized metadata dict
    """
    # Extract epub format
    epub_format = None
    for fmt in details.get("formats", []):
        if fmt.get("type") == "epub":
            epub_format = fmt
            break

    metadata = {
        "title": details.get("title"),
        "authors": [author.get("name", "") for author in details.get("authors", [])],
        "translators": [translator.get("name", "") for translator in epub_format.get("translators", []) if epub_format],
        "description": details.get("description_full"),
        "language": details.get("language"),
    }

    # Epub-specific metadata
    if epub_format:
        metadata["publisher"] = epub_format.get("publisher", {}).get("name")
        metadata["isbn"] = epub_format.get("isbn")

        publication_date = epub_format.get("publication_date")
        if publication_date:
            # Already in YYYY-MM-DD format
            metadata["release_date"] = publication_date

    # Series info
    series_info = details.get("series")
    if series_info:
        metadata["series_name"] = series_info.get("name")
        # Nextory uses "volume" at top level, not in series info
        volume = details.get("volume")
        if volume:
            metadata["series_index"] = volume

    return metadata


# Registry of transformers by source name
TRANSFORMERS = {
    "storytel": storytel_transformer,
    "nextory": nextory_transformer,
    # Add more sources here as they're implemented
}


def get_transformer(source_name: str):
    """
    Get the metadata transformer for a given source

    :param source_name: Name of the source (lowercase)
    :return: Transformer function or None if not found
    """
    return TRANSFORMERS.get(source_name.lower())
