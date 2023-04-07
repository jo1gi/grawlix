from grawlix.book import Book, BookData, SingleFile, ImageList, OnlineFile
from grawlix.exceptions import GrawlixError

from .output_format import OutputFormat
from .epub import Epub
from .cbz import Cbz

from typing import Callable
from pathlib import Path
import os

def download_book(book: Book, update_func: Callable, template: str) -> None:
    """
    Download and write book to disk

    :param book: Book to download
    """
    output_format = get_default_format(book.data)
    location = format_output_location(book, output_format, template)
    parent = Path(location).parent
    if not parent.exists():
        os.makedirs(parent)
    if isinstance(book.data, SingleFile):
        output_format.dl_single_file(book.data, location, update_func)
    elif isinstance(book.data, ImageList):
        output_format.dl_image_list(book.data, location, update_func)
    else:
        raise NotImplementedError


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


def get_default_format(bookdata: BookData) -> OutputFormat:
    """
    Get default output format for bookdata.
    Should only be used if no format was specified by the user

    :param bookdata: Content of book
    :returns: OutputFormat object matching the default
    """
    if isinstance(bookdata, SingleFile):
        return output_format_from_str(bookdata.file.extension)
    if isinstance(bookdata, ImageList):
        return Cbz()
    raise GrawlixError


def output_format_from_str(name: str) -> OutputFormat:
    """
    Convert string to outputformat object

    :param name: Name of output format
    :returns: OutputFormat object
    """
    for output_format in get_output_formats():
        if output_format.extension == name:
            return output_format()
    raise GrawlixError


def get_output_formats() -> list[type[OutputFormat]]:
    """
    Get a list of all available output formats

    :returns: List of available output format classes
    """
    return [
        Cbz,
        Epub,
    ]
