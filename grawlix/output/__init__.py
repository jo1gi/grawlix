from grawlix.book import Book, BookData, ImageList, HtmlFiles, EpubInParts
from grawlix.exceptions import GrawlixError, UnsupportedOutputFormat
from grawlix import logging
from grawlix.utils import blob, http

from . import cbz, epub

import json
import dataclasses
from typing import Callable, Iterable, Awaitable
from pathlib import Path
import os
import platform


@dataclasses.dataclass(slots=True)
class Output[T: BookData]:
    f: Callable[[Book[T], str, Callable], Awaitable[None]]
    extension: str
    book_data_format: type[T]

    async def download(self, book: Book[T], location: str, update: Callable) -> None:
        await self.f(book, location, update)


async def download_blob(book: Book[blob.Blob], location: str, update: Callable) -> None:
    client = http.create_client()
    await blob.write_to_file(book.data, location, client, update)


async def download_book(book: Book, update: Callable, template: str) -> None:
    """
    Download and write book to disk.

    :param book: Book to download.
    :param update: Function called to indicate progression.
    :param template: Template used to generate output path.
    """
    logging.trace(f"Downloading {book}")
    output: Output
    match book.data:
        case blob.Blob(_, _, _):
            output = Output(download_blob, blob.extension_of_format(book.data.format), blob.Blob)
        case ImageList(_):
            output = Output(cbz.create_cbz_file, "cbz", ImageList)
        case HtmlFiles(_, _):
            output = Output(epub.download_html_files, "epub", HtmlFiles)
        case EpubInParts(_, _):
            output = Output(epub.merge_epubs, "epub", EpubInParts)
        case _:
            raise UnsupportedOutputFormat

    location = format_output_location(book, output.extension, template)

    if not book.overwrite and os.path.exists(location):
        # TODO: Better formatting
        logging.info("Skipping - File already exists")
        return

    parent = Path(location).parent
    if not parent.exists():
        os.makedirs(parent)

    await output.download(book, location, update)


def write_metadata(book: Book, template: str):
    """
    Write book metadata to a file.

    :param book: The book with metadata.
    :param template: Template for the output path.
    """
    path = format_output_location(book, "json", template)

    parent = Path(path).parent
    if not parent.exists():
        os.makedirs(parent)

    metadata = book.metadata
    formatted = {
        "title": metadata.title,
        "authors": metadata.authors,
        "series": metadata.series,
        "series_index": metadata.index,
        "release_date": metadata.release_date.isoformat() if metadata.release_date else None,
        "publisher": metadata.publisher,
        "description": metadata.description,
        "isbn": metadata.isbn,
        "language": metadata.language,
        "cover_link": metadata.cover_link,
    }
    with open(path, "w") as f:
        json.dump(formatted, f, indent=4)


def format_output_location(book: Book, extension: str, template: str) -> str:
    """
    Create path to output location of book

    :param book: Book to download
    :param output_format: Extension of the output format
    :param template: Template for output path
    :returns: Output path
    """
    values = { key: remove_unwanted_chars(str(value)) for key, value in book.metadata.as_dict().items() }
    path = template.format(**values, ext = extension)
    return os.path.expanduser(path)


def remove_strings(input: str, strings: Iterable[str]) -> str:
    """
    Remove strings from input

    :param input: the string to remove strings from
    :param strings: the list of strings to remove from input
    :returns: input without strinfs
    """
    for c in strings:
        input = input.replace(c, "")
    return input


def remove_unwanted_chars(input: str) -> str:
    """
    Remove chars from string that are not supported in output path

    :param input: The string to remove chars from
    :returns: input without unsupported chars
    """
    if platform.system() == "Windows":
        return remove_strings(input, "<>:\"/\\|?*")
    else:
        return remove_strings(input, "/")
