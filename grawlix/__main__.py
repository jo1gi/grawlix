from .book import Book, Series
from .config import load_config, Config, SourceConfig
from .exceptions import SourceNotAuthenticated
from .sources import load_source, Source
from .output import download_book
from . import  arguments, logging

from typing import Tuple, Optional
from rich.progress import Progress
from functools import partial
import os


def get_login(source: Source, config: Config, options) -> Tuple[str, str]:
    """
    Get login credentials for source

    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    :returns: Login credentials
    """
    source_name = source.name.lower()
    if source_name in config.sources:
        username = config.sources[source_name].username or options.username
        password = config.sources[source_name].password or options.password
    else:
        username = options.username
        password = options.password
    return username, password


def get_urls(options) -> list[str]:
    """
    Retrieves all available urls from input arguments
    - From urls argument
    - From file argument
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


def authenticate(source: Source, config: Config, options):
    """
    Authenticate with source

    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    """
    logging.info(f"Authenticating with source [magenta]{source.name}[/]")
    if source.supports_login:
        username, password = get_login(source, config, options)
        source.login(username, password)
        source.authenticated = True
    if source.supports_cookies:
        cookie_file = get_cookie_file(options)
        if cookie_file:
            source.load_cookies(cookie_file)
    else:
        raise SourceNotAuthenticated


def main() -> None:
    args = arguments.parse_arguments()
    config = load_config()
    urls = get_urls(args)
    for url in urls:
        source: Source = load_source(url)
        if not source.authenticated and source.requires_authentication:
            authenticate(source, config, args)
        result = source.download(url)
        if isinstance(result, Book):
            with logging.progress(result.metadata.title, source.name) as progress:
                template = args.output or "{title}.{ext}"
                download_with_progress(result, progress, template)
        elif isinstance(result, Series):
            with logging.progress(result.title, source.name, len(result.book_ids)) as progress:
                for book_id in result.book_ids:
                    book = source.download_book_from_id(book_id)
                    template = args.output or "{series}/{title}.{ext}"
                    download_with_progress(book, progress, template)
        logging.info("")


def download_with_progress(book: Book, progress: Progress, template: str):
    """
    Download book with progress bar in cli

    :param book: Book to download
    :param progress: Progress object
    :param template: Output template
    """
    task = logging.add_book(progress, book)
    update_function = partial(progress.advance, task)
    download_book(book, update_function, template)
    progress.advance(task, 1)


if __name__ == "__main__":
    main()
