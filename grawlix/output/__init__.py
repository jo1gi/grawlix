from grawlix.book import Book, BookData, SingleFile, ImageList, OnlineFile, HtmlFiles, EpubInParts
from grawlix.exceptions import GrawlixError, UnsupportedOutputFormat
from grawlix.logging import info

from .output_format import OutputFormat
from .acsm import Acsm
from .cbz import Cbz
from .epub import Epub
from .pdf import Pdf

from typing import Callable, Iterable
from pathlib import Path
import os
import platform

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
    :param template: Template for output path (supports ~, environment variables, and absolute paths)
    :returns: Output path
    """
    values = { key: remove_unwanted_chars(value) for key, value in book.metadata.as_dict().items() }
    path = template.format(**values, ext = output_format.extension)

    # Expand user home directory (~/... or ~user/...)
    path = os.path.expanduser(path)

    # Expand environment variables ($VAR or %VAR% depending on OS)
    path = os.path.expandvars(path)

    # Normalize path separators for current OS
    path = os.path.normpath(path)

    return path


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
    Sanitize string for use in file paths across all operating systems.
    Replaces forbidden characters with safe alternatives and handles edge cases.

    :param input: The string to sanitize
    :returns: Safe filename string
    """
    import re

    # Replace null bytes and control characters
    output = re.sub(r'[\x00-\x1f\x7f]', '', input)

    # Platform-specific forbidden characters - replace with underscore
    if platform.system() == "Windows":
        # Windows forbidden: < > : " / \ | ? *
        forbidden_chars = '<>:"|?*'
        for char in forbidden_chars:
            output = output.replace(char, '_')
        # Replace slashes with dash for better readability
        output = output.replace('/', '-')
        output = output.replace('\\', '-')

        # Windows reserved names (case-insensitive)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        # Check if the name (without extension) is reserved
        name_part = output.split('.')[0].upper()
        if name_part in reserved_names:
            output = f"_{output}"

        # Remove trailing spaces and periods (Windows doesn't allow these)
        output = output.rstrip('. ')

    else:
        # Unix-like systems (macOS, Linux)
        # Only / is truly forbidden, but : can cause issues on macOS
        output = output.replace('/', '-')
        # Some versions of macOS have issues with :
        output = output.replace(':', '-')

    # Remove leading/trailing whitespace
    output = output.strip()

    # Limit filename length (most filesystems have 255 byte limit)
    # Reserve some space for extensions and numbering
    max_length = 200
    if len(output.encode('utf-8')) > max_length:
        # Truncate while respecting UTF-8 character boundaries
        output_bytes = output.encode('utf-8')[:max_length]
        # Decode, ignoring partial characters at the end
        output = output_bytes.decode('utf-8', errors='ignore').rstrip()

    # Ensure we don't return an empty string
    if not output:
        output = "untitled"

    return output


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
        Pdf,
    ]
