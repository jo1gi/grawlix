from .book import Book, Series
from .config import load_config, Config, SourceConfig
from .exceptions import SourceNotAuthenticated, GrawlixError, AccessDenied
from .sources import load_source, Source
from .output import download_book
from . import  arguments, logging

from typing import Tuple, Optional
from rich.prompt import Prompt
from rich.progress import Progress
from functools import partial
import os
import asyncio
import traceback
import warnings

# Suppress deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")


def get_or_ask(attr: str, hidden: bool, source_config: Optional[SourceConfig], options) -> str:
    return getattr(options, attr, None) \
    or getattr(source_config, attr, None) \
    or Prompt.ask(attr.capitalize(), password=hidden)


def get_login(source: Source, config: Config, options) -> Tuple[str, str]:
    """
    Get login credentials for source

    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    :returns: Login credentials
    """
    source_name = source.name.lower().replace(" ", "")
    source_config = config.sources.get(source_name)

    username = get_or_ask("username", False, source_config, options)
    password = get_or_ask("password", True, source_config, options)

    return username, password


def get_urls(options) -> list[str]:
    """
    Retrieves all available urls from input arguments
    - From urls argument
    - From file argument

    :param options: Cli options
    :returns: All urls listed in arguments
    """
    urls = []
    if options.urls:
        urls.extend(options.urls)
    if options.file:
        with open(options.file, "r") as f:
            content = f.read()
            urls.extend(content.split("\n"))
    return urls


def get_cookie_file(options) -> Optional[str]:
    """
    Get path to cookie file

    :param options: Cli arguments
    :returns: Path to cookie file
    """
    if options.cookie_file is not None and os.path.exists(options.cookie_file):
        return options.cookie_file
    if os.path.exists("./cookies.txt"):
        return "./cookies.txt"
    return None


async def authenticate(url: str, source: Source, config: Config, options):
    """
    Authenticate with source

    :param url: The url of the book currently being downloaded
    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    """
    logging.info(f"Authenticating with source [magenta]{source.name}[/]")
    if source.supports_login:
        username, password = get_login(source, config, options)
        await source.login(url, username, password)
        source.authenticated = True
    if not source.authenticated and source.supports_cookies:
        cookie_file = get_cookie_file(options)
        if cookie_file:
            source.load_cookies(cookie_file)
            source.authenticated = True
    if not source.authenticated:
        raise SourceNotAuthenticated


async def main() -> None:
    args = arguments.parse_arguments()
    config = load_config()
    logging.debug_mode = args.debug
    urls = get_urls(args)
    for url in urls:
        try:
            source: Source = load_source(url)
            if not source.authenticated and source.requires_authentication:
                await authenticate(url, source, config, args)
            result = await source.download(url)
            if isinstance(result, Book):
                with logging.progress(result.metadata.title, source.name) as progress:
                    # Check CLI flag first, then config file, then default
                    template: str = args.output or config.output or "{title}.{ext}"
                    # Check both CLI flag and config file
                    write_metadata = args.write_metadata_to_epub or config.write_metadata_to_epub
                    await download_with_progress(result, progress, template, write_metadata)
            elif isinstance(result, Series):
                await download_series(source, result, args, config)
            logging.info("")
        except GrawlixError as error:
            error.print_error()
            if logging.debug_mode:
                traceback.print_exc()
            exit(1)


async def download_series(source: Source, series: Series, args, config: Config) -> None:
    """
    Download books in series

    :param series: Series to download
    :param args: CLI arguments
    :param config: Configuration
    """
    # Check CLI flag first, then config file, then default
    template = args.output or config.output or "{series}/{title}.{ext}"
    # Check both CLI flag and config file
    write_metadata = args.write_metadata_to_epub or config.write_metadata_to_epub
    with logging.progress(series.title, source.name, len(series.book_ids)) as progress:
        for book_id in series.book_ids:
            try:
                book: Book = await source.download_book_from_id(book_id)
                await download_with_progress(book, progress, template, write_metadata)
            except AccessDenied as error:
                logging.info("Skipping - Access Denied")



async def download_with_progress(book: Book, progress: Progress, template: str, write_metadata: bool = False):
    """
    Download book with progress bar in cli

    :param book: Book to download
    :param progress: Progress object
    :param template: Output template
    :param write_metadata: Whether to write metadata to EPUB files
    """
    task = logging.add_book(progress, book)
    update_function = partial(progress.advance, task)

    # Download the book
    await download_book(book, update_function, template)

    # Convert PDF-in-epub to PDF if needed (Nextory wraps PDFs in epub containers)
    if book.metadata.source == "Nextory":
        from .output import format_output_location, get_default_format
        from .output.pdf_converter import convert_pdf_epub_to_pdf, is_pdf_in_epub

        output_format = get_default_format(book)
        location = format_output_location(book, output_format, template)

        if location.endswith('.epub') and os.path.exists(location) and is_pdf_in_epub(location):
            convert_pdf_epub_to_pdf(location)
            logging.debug(f"Converted PDF-in-epub to PDF: {location}")

    # Write metadata if requested
    if write_metadata:
        from .output import format_output_location, get_default_format, find_output_format, get_valid_extensions
        from .output.metadata import epub_metadata

        # Determine output file location
        _, ext = os.path.splitext(template)
        ext = ext[1:]

        # Handle {ext} placeholder - use default format for the book type
        if ext and ext not in ['{ext}', 'ext'] and ext in get_valid_extensions():
            output_format = find_output_format(book, ext)()
        else:
            output_format = get_default_format(book)

        location = format_output_location(book, output_format, template)
        logging.debug(f"Output location: {location}, exists={os.path.exists(location)}, ends_with_epub={location.endswith('.epub')}")

        # Write metadata if it's an EPUB file
        if location.endswith('.epub') and os.path.exists(location):
            epub_metadata.write_metadata_to_epub(book.metadata, location)

    progress.advance(task, 1)


def run() -> None:
    """Start main function"""
    asyncio.run(main())


if __name__ == "__main__":
    run()
