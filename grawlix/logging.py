from grawlix.book import Book

import rich
from rich.console import Console
from rich.markup import render
from rich.progress import Progress, BarColumn, ProgressColumn, TaskID, SpinnerColumn
from rich.style import Style

from typing import Union
from dataclasses import dataclass
import importlib.resources

console = Console(stderr=True)

debug_mode = False
DEBUG_PREFIX = render("[yellow bold]DEBUG[/]")


def debug(msg: str, remove_styling=False) -> None:
    """
    Print debug message in console

    :param msg: Message to print
    :param remove_styling: Remove automated styling from message
    """
    if debug_mode:
        if remove_styling:
            rendered_msg = render(msg, style=Style(bold=False, color="white"))
            console.print(DEBUG_PREFIX, rendered_msg)
        else:
            console.print(DEBUG_PREFIX, msg)


def info(msg: str) -> None:
    """
    Print message in console

    :param msg: Message to print
    """
    console.print(msg)


def error(msg: str) -> None:
    console.print(msg)


def print_error_file(name: str, **kwargs) -> None:
    """
    Print predefined error message

    :param name: Name of error file
    """
    message = importlib.resources.files("grawlix") \
        .joinpath(f"assets/errors/{name}.txt") \
        .read_text("utf8") \
        .format(**kwargs) \
        .strip()
    error(message)


def progress(category_name: str, source_name: str, count=1) -> Progress:
    if count > 1:
        console.print(f"Downloading [yellow not bold]{count}[/] books in [blue]{category_name}[/] from [magenta]{source_name}[/]")
    else:
        console.print(f"Downloading [blue bold]{category_name}[/] from [magenta]{source_name}[/]")
    progress = Progress(
        SpinnerColumn(),
        "{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        console = console,
    )
    return progress


def add_book(progress: Progress, book: Book) -> TaskID:
    task = progress.add_task(
        f"[blue]{book.metadata.title}[/]",
        total = 1
    )
    return task
