from .book import Book, Series
from .config import load_config, Config, SourceConfig
from .exceptions import SourceNotAuthenticated, GrawlixError, AccessDenied
from .sources import load_source, Source
from .output import download_book
from . import  arguments, logging

from typing import Tuple, Optional
from rich.progress import Progress
from functools import partial
import os
import asyncio
import traceback


def get_login(source: Source, config: Config, options) -> Tuple[str, str, Optional[str]]:
    """
    Get login credentials for source

    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    :returns: Login credentials
    """
    source_name = source.name.lower().replace(" ", "")
    if source_name in config.sources:
        username = config.sources[source_name].username or options.username
        password = config.sources[source_name].password or options.password
        library = config.sources[source_name].library or options.library
    else:
        username = options.username
        password = options.password
        library = options.library
    return username, password, library


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


async def authenticate(source: Source, config: Config, options):
    """
    Authenticate with source

    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    """
    logging.info(f"Authenticating with source [magenta]{source.name}[/]")
    if source.supports_login:
        username, password, library = get_login(source, config, options)
        await source.login(username, password, library=library)
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
                await authenticate(source, config, args)
            result = await source.download(url)
            if isinstance(result, Book):
                with logging.progress(result.metadata.title, source.name) as progress:
                    template: str = args.output or "{title}.{ext}"
                    await download_with_progress(result, progress, template)
            elif isinstance(result, Series):
                await download_series(source, result, args)
            logging.info("")
        except GrawlixError as error:
            error.print_error()
            if logging.debug_mode:
                traceback.print_exc()
            exit(1)


async def download_series(source: Source, series: Series, args) -> None:
    """
    Download books in series

    :param series: Series to download
    """
    template = args.output or "{series}/{title}.{ext}"
    with logging.progress(series.title, source.name, len(series.book_ids)) as progress:
        for book_id in series.book_ids:
            try:
                book: Book = await source.download_book_from_id(book_id)
                await download_with_progress(book, progress, template)
            except AccessDenied as error:
                logging.info("Skipping - Access Denied")



async def download_with_progress(book: Book, progress: Progress, template: str):
    """
    Download book with progress bar in cli

    :param book: Book to download
    :param progress: Progress object
    :param template: Output template
    """
    task = logging.add_book(progress, book)
    update_function = partial(progress.advance, task)
    await download_book(book, update_function, template)
    progress.advance(task, 1)


def run() -> None:
    """Start main function"""
    asyncio.run(main())


if __name__ == "__main__":
    run()
