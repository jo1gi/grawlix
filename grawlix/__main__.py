from grawlix import source, output
from .book import Book, Series, Result
from .exceptions import SourceNotAuthenticated, GrawlixError, AccessDenied
from .sources import find_source
from .output import download_book, context
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


async def run(options: Options) -> None:
    logging.debug_mode = options.debug
    logging.trace_mode = options.trace

    for url in options.urls:
        try:
            definition: source.Source = find_source(url)
            instance: source.Instance = await instanciate(url, definition, options)
            logging.debug(f"Finding id of {url}")
            id = await definition.id_of_url(instance.state, url)
            logging.debug(f"{id=}")
            result = await definition.download(instance.state, id)

            await download(instance, result, options)

            logging.info("")

        except GrawlixError as error:
            error.print_error()
            if logging.debug_mode:
                traceback.print_exc()
            exit(1)


async def download(instance: source.Instance, result: Result, options: Options) -> None:
    if isinstance(result, Book):
        with logging.progress(result.metadata.title, instance.source.name) as progress:
            await download_with_progress(result, progress, options.book_output_template, options)

    elif isinstance(result, Series):
        await download_series(instance, result, options)


async def download_series(instance: source.Instance, series: Series, options: Options) -> None:
    """
    Download books in series

    :param series: Series to download
    :param options: User defined options
    """
    with logging.progress(series.title, instance.source.name, len(series.book_ids)) as progress:
        for book_id in series.book_ids:
            book = await instance.download(book_id)
            await download_with_progress(book, progress, options.series_output_template, options)


async def download_with_progress(book: Book, progress: Progress, template: str, options: Options):
    """
    Download book with progress bar in cli

    :param book: Book to download
    :param progress: Progress object
    :param template: Output template
    """
    current_context = context.create_context(progress, book.metadata.title)
    await download_book(current_context, book, template)
    if options.export_metadata:
        output.write_metadata(book, template)


def main() -> None:
    """Start main function"""
    options = load_options()
    asyncio.run(run(options))


if __name__ == "__main__":
    main()
