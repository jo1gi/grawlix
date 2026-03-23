from grawlix import source
from .book import Book, Series
from .exceptions import SourceNotAuthenticated, GrawlixError, AccessDenied
from .sources import find_source
from .output import download_book
from .options import load_options, Options
from . import config, logging

from typing import Tuple, Optional
from rich.prompt import Prompt
from rich.progress import Progress
from functools import partial
import os
import asyncio
import traceback


def get_or_ask(attr: str, hidden: bool, source_config: Optional[config.SourceConfig], options: Options) -> str:
    return getattr(options, attr, None) \
    or getattr(source_config, attr, None) \
    or Prompt.ask(attr.capitalize(), password=hidden)


def get_login(source_name: str, options: Options) -> Tuple[str, str]:
    """
    Get login credentials for source

    :param source: Source to authenticate
    :param options: User defined options
    :returns: Login credentials
    """
    source_name = source_name.lower().replace(" ", "")
    source_config = options.source_options.get(source_name)

    username = get_or_ask("username", False, source_config, options)
    password = get_or_ask("password", True, source_config, options)

    return username, password


async def instanciate(url: str, definition: source.Source, options: Options):
    """
    Create an instance of the source. This usually requires logging in or
    loading cookies.

    :param url: The url of the book currently being downloaded
    :param source: Source to authenticate
    :param options: User defined options
    """
    logging.info(f"Authenticating with source [magenta]{definition.name}[/]")

    if definition.load_cookies and options.cookie_file:
        state = await definition.load_cookies(options.cookie_file)
        return source.Instance(definition, state)

    if definition.login:
        username, password = get_login(definition.name, options)
        state = await definition.login(url, username, password)
        return source.Instance(definition, state)

    if definition.instanciate_without_login:
        state = await definition.instanciate_without_login(url)
        return source.Instance(definition, state)

    raise SourceNotAuthenticated


async def main() -> None:
    options = load_options()
    logging.debug_mode = options.debug

    for url in options.urls:
        try:
            definition: source.Source = find_source(url)
            instance: source.Instance = await instanciate(url, definition, options)
            logging.debug(f"Finding id of {url}")
            id = await definition.id_of_url(instance.state, url)
            logging.debug(f"{id=}")
            result = await definition.download(instance.state, id)

            if isinstance(result, Book):
                with logging.progress(result.metadata.title, definition.name) as progress:
                    await download_with_progress(result, progress, options.book_output_template)

            elif isinstance(result, Series):
                await download_series(instance, result, options)

            logging.info("")

        except GrawlixError as error:
            error.print_error()
            if logging.debug_mode:
                traceback.print_exc()
            exit(1)


async def download_series(instance: source.Instance, series: Series, options: Options) -> None:
    """
    Download books in series

    :param series: Series to download
    :param options: User defined options
    """
    with logging.progress(series.title, instance.source.name, len(series.book_ids)) as progress:
        for book_id in series.book_ids:
            try:
                book = await instance.download(book_id)
                await download_with_progress(book, progress, options.series_output_template)
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
