from .book import Book, Series
from .config import load_config, Config, SourceConfig
from .exceptions import SourceNotAuthenticated
from .sources import find_source, Source
from .output import download_book
from . import  arguments, logging

from typing import Tuple
from rich.progress import Progress
from functools import partial


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


def authenticate(source: Source, config: Config, options):
    """
    Authenticate with source

    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    """
    if source.supports_login:
        username, password = get_login(source, config, options)
        source.login(username, password) 
    else:
        raise SourceNotAuthenticated


def main() -> None:
    args = arguments.parse_arguments()
    config = load_config()
    for url in args.urls:
        source: Source = find_source(url)
        if source.requires_authentication:
            authenticate(source, config, args)
        result = source.download(url)
        if isinstance(result, Book):
            with logging.progress(result.metadata.title, source.name) as progress:
                download_with_progress(result, progress)
        elif isinstance(result, Series):
            with logging.progress(result.title, source.name, len(result.book_ids)) as progress:
                for book_id in result.book_ids:
                    book = source.download_book_from_id(book_id)
                    download_with_progress(book, progress)


def download_with_progress(book: Book, progress: Progress):
    """
    Download book with progress bar in cli

    :param book: Book to download
    :param progress: Progress object
    """
    task = logging.add_book(progress, book)
    update_function = partial(progress.advance, task)
    download_book(book, update_function)
    progress.advance(task, 1)


if __name__ == "__main__":
    main()
