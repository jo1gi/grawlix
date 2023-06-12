from grawlix.book import Book, BookData, SingleFile, ImageList, OnlineFile, HtmlFiles, EpubInParts
from grawlix.exceptions import GrawlixError, UnsupportedOutputFormat
from grawlix.logging import info

from .output_format import OutputFormat
from .acsm import Acsm
from .cbz import Cbz
from .epub import Epub

from typing import Callable
from pathlib import Path
import os

async def download_book(book: Book, update_func: Callable, template: str) -> None:
    """
    Download and write book to disk

    :param book: Book to download
    """
    _, ext = os.path.splitext(template)
    ext = ext[1:]
    if ext in get_valid_extensions():
        output_format = find_output_format(book, ext)()
    else:
        output_format = get_default_format(book)
    location = format_output_location(book, output_format, template)
    if not book.overwrite and os.path.exists(location):
        info("Skipping - File already exists")
        return
    parent = Path(location).parent
    if not parent.exists():
        os.makedirs(parent)
    await output_format.download(book, location, update_func)
    await output_format.close()


def format_output_location(book: Book, output_format: OutputFormat, template: str) -> str:
    """
    Create path to output location of book

    :param book: Book to download
    :param output_format: Output format of book
    :param template: Template for output path
    :returns: Output path
    """
    values = book.metadata.as_dict()
    return template.format(**values, ext = output_format.extension)


def get_default_format(book: Book) -> OutputFormat:
    """
    Get default output format for bookdata.
    Should only be used if no format was specified by the user

    :param book: Content of book
    :returns: OutputFormat object matching the default
    """
    bookdata = book.data
    if isinstance(bookdata, SingleFile):
        extension = bookdata.file.extension
    elif isinstance(bookdata, ImageList):
        extension = "cbz"
    elif isinstance(bookdata, HtmlFiles) or isinstance(bookdata, EpubInParts):
        extension = "epub"
    output_format = find_output_format(book, extension)
    return output_format()


def find_output_format(book: Book, extension: str) -> type[OutputFormat]:
    """
    Find a compatible output format

    :param book: Book to download
    :param extension: Extension of output file
    :returns: Compatible OutputFormat type
    :raises: UnsupportedOutputFormat if nothing is found
    """
    for output_format in get_output_formats():
        matches_extension = output_format.extension == extension
        supports_bookdata = type(book.data) in output_format.input_types
        if matches_extension and supports_bookdata:
            return output_format
    raise UnsupportedOutputFormat

def get_valid_extensions() -> list[str]:
    return [output_format.extension for output_format in get_output_formats()]


def get_output_formats() -> list[type[OutputFormat]]:
    """
    Get a list of all available output formats

    :returns: List of available output format classes
    """
    return [
        Acsm,
        Cbz,
        Epub,
    ]
