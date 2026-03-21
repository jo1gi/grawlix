from grawlix import source
from .book import Book, Series
from .config import load_config, Config, SourceConfig
from .exceptions import SourceNotAuthenticated, GrawlixError, AccessDenied
from .sources import find_source
from .output import download_book
from . import  arguments, logging

from typing import Tuple, Optional
from rich.prompt import Prompt
from rich.progress import Progress
from functools import partial
import os
import asyncio
import traceback


def get_or_ask(attr: str, hidden: bool, source_config: Optional[SourceConfig], options) -> str:
    return getattr(options, attr, None) \
    or getattr(source_config, attr, None) \
    or Prompt.ask(attr.capitalize(), password=hidden)


def get_login(source_name: str, config: Config, options) -> Tuple[str, str]:
    """
    Get login credentials for source

    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    :returns: Login credentials
    """
    source_name = source_name.lower().replace(" ", "")
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


async def instanciate(url: str, definition: source.Source, config: Config, options):
    """
    Create an instance of the source. This usually requires logging in or
    loading cookies.

    :param url: The url of the book currently being downloaded
    :param source: Source to authenticate
    :param config: Content of config file
    :param options: Command line options
    """
    logging.info(f"Authenticating with source [magenta]{definition.name}[/]")
    if definition.login is not None:
        username, password = get_login(definition.name, config, options)
        state = await definition.login(url, username, password)
        return source.Instance(definition, state)

    if definition.load_cookies is not None:
        cookie_file = get_cookie_file(options)
        if cookie_file:
            state = await definition.load_cookies(cookie_file)
            return source.Instance(definition, state)

    if definition.instanciate_without_login is not None:
        state = await definition.instanciate_without_login(url)
        return source.Instance(definition, state)
    raise SourceNotAuthenticated


async def main() -> None:
    args = arguments.parse_arguments()
    config = load_config()
    logging.debug_mode = args.debug
    urls = get_urls(args)
    for url in urls:
        try:
            definition: source.Source = find_source(url)
            instance: source.Instance = await instanciate(url, definition, config, args)
            logging.debug(f"Finding id of {url}")
            id = await definition.id_of_url(instance.state, url)
            logging.debug(f"{id=}")
            result = await definition.download(instance.state, id)
            if isinstance(result, Book):
                with logging.progress(result.metadata.title, definition.name) as progress:
                    template: str = args.output or "{title}.{ext}"
                    await download_with_progress(result, progress, template)
            elif isinstance(result, Series):
                await download_series(instance, result, args)
            logging.info("")
        except GrawlixError as error:
            error.print_error()
            if logging.debug_mode:
                traceback.print_exc()
            exit(1)


async def download_series(instance: source.Instance, series: Series, args) -> None:
    """
    Download books in series

    :param series: Series to download
    """
    template = args.output or "{series}/{title}.{ext}"
    with logging.progress(series.title, instance.source.name, len(series.book_ids)) as progress:
        for book_id in series.book_ids:
            try:
                book = await instance.download(book_id)
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
