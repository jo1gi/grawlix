from grawlix.book import Book, BookData, SingleFile, ImageList, OnlineFile, HtmlFiles, EpubInParts
from grawlix.exceptions import GrawlixError, UnsupportedOutputFormat

from .output_format import OutputFormat
from .acsm import Acsm
from .cbz import Cbz
from .epub import Epub
from .pdf import Pdf
from .pdf_converter import pdf_path_for

from typing import Callable, Optional
from pathlib import Path
import os
import platform

async def download_book(book: Book, update_func: Callable, template: str) -> Optional[str]:
    """
    Download and write book to disk

    :param book: Book to download
    :param update_func: Progress callback
    :param template: Output path template
    :returns: A skip reason if the book was skipped, otherwise None
    """
    _, ext = os.path.splitext(template)
    ext = ext[1:]
    if ext in get_valid_extensions():
        output_format = find_output_format(book, ext)()
    else:
        output_format = get_default_format(book)()
    location = format_output_location(book, output_format, template)
    # Split epubs may have been converted to PDF on an earlier run
    existing = [location]
    if isinstance(book.data, EpubInParts):
        existing.append(pdf_path_for(location))
    if not book.overwrite and any(os.path.exists(path) for path in existing):
        return "Skipping - File already exists"
    parent = Path(location).parent
    if not parent.exists():
        os.makedirs(parent)
    try:
        await output_format.download(book, location, update_func)
    finally:
        await output_format.close()
    return None


def format_output_location(book: Book, output_format: OutputFormat | type[OutputFormat], template: str) -> str:
    """
    Create path to output location of book

    :param book: Book to download
    :param output_format: Output format of book
    :param template: Template for output path (supports ~, environment variables, and absolute paths)
    :returns: Output path
    """
    # Expand ~ and environment variables in the template only, so metadata
    # values like "$HOME" or "~" are kept literal
    template = os.path.expandvars(os.path.expanduser(template))
    values = { key: remove_unwanted_chars(value) for key, value in book.metadata.as_dict().items() }
    path = template.format(**values, ext = output_format.extension)

    # Normalize path separators for current OS
    path = os.path.normpath(path)

    return path


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
        # Only / is forbidden on POSIX; : is replaced too since macOS Finder shows it as /
        output = output.replace('/', '-')
        output = output.replace(':', '-')

    output = output.strip()

    # Limit filename length (most filesystems have 255 byte limit)
    # Reserve some space for extensions and numbering
    max_length = 200
    if len(output.encode('utf-8')) > max_length:
        # Truncate while respecting UTF-8 character boundaries
        output_bytes = output.encode('utf-8')[:max_length]
        # Decode, ignoring partial characters at the end
        output = output_bytes.decode('utf-8', errors='ignore').rstrip()

    # "." and ".." would escape the intended directory
    if not output or output in (".", ".."):
        output = "untitled"

    return output


def get_default_format(book: Book) -> type[OutputFormat]:
    """
    Get default output format for bookdata.
    Should only be used if no format was specified by the user

    :param book: Content of book
    :returns: OutputFormat type matching the default
    """
    bookdata = book.data
    if isinstance(bookdata, SingleFile):
        extension = bookdata.file.extension
    elif isinstance(bookdata, ImageList):
        extension = "cbz"
    elif isinstance(bookdata, HtmlFiles) or isinstance(bookdata, EpubInParts):
        extension = "epub"
    return find_output_format(book, extension)


def find_output_format(book: Book, extension: str) -> type[OutputFormat]:
    """
    Find a compatible output format

    :param book: Book to download
    :param extension: Extension of output file
    :returns: Compatible OutputFormat type
    :raises UnsupportedOutputFormat: If nothing is found
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
