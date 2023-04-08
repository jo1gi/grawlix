from grawlix.book import Book

from rich.console import Console
from rich.progress import Progress, BarColumn, ProgressColumn, TaskID, SpinnerColumn
import rich

from typing import Union
from dataclasses import dataclass

console = Console(stderr=True)

def info(msg: str) -> None:
    """
    Print message in log

    :param msg: Message to print
    """
    console.print(msg)

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
