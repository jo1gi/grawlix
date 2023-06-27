from grawlix.book import Metadata

import xml.etree.ElementTree as ET
from typing import Optional


def add_value(element: ET.Element, name: str, value: Optional[str]) -> None:
    """
    Add new tag to element

    :param element: Element to add tag to
    :param name: Name of new tag
    :param value: Contents of new tag
    """
    if value:
        subelement = ET.SubElement(element, name)
        subelement.text = str(value)


def to_comic_info(metadata: Metadata) -> str:
    """
    Output as ComicRack metadata format (ComicInfo)
    Documentation: https://anansi-project.github.io/docs/comicinfo

    :param metadata: Book metadata
    :returns: ComicInfo xml as a string
    """
    root = ET.Element("ComicInfo")
    add_value(root, "Title", metadata.title)
    add_value(root, "Series", metadata.series)
    add_value(root, "Summary", metadata.description)
    add_value(root, "Publisher", metadata.publisher)
    add_value(root, "Year", getattr(metadata.release_date, "year", None))
    add_value(root, "Month", getattr(metadata.release_date, "month", None))
    add_value(root, "Day", getattr(metadata.release_date, "day", None))
    add_value(root, "Format", "Web")
    return ET.tostring(root).decode("utf8")
