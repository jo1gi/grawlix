from grawlix import logging
from grawlix.utils import http

import dataclasses
from rich.progress import Progress, TaskID

@dataclasses.dataclass(slots=True)
class Context:
    progress: Progress
    task_id: TaskID
    book_name: str
    client: http.Client


    def advance(self, amount: float) -> None:
        """
        Advance the progress of the book.

        :param amount: The amount of progress made (between 0 and 1).
        """
        self.progress.advance(self.task_id, amount)


    def abort(self, reason: str, completed: bool) -> None:
        """
        Abort the progress of the book.

        :param reason: The reason the progress was aborted.
        :param completed: True if the progress was completed; False otherwise.
        """
        self.progress.reset(
            self.task_id,
            completed = 1 if completed else 0,
            description = f"[blue]{self.book_name}[/]: {reason}",
        )


    def complete(self) -> None:
        """Complete the progress of the book."""
        self.advance(1)


def create_context(progress: Progress, book_name: str) -> Context:
    task_id = logging.add_book(progress, book_name)
    return Context(
        progress = progress,
        task_id = task_id,
        book_name = book_name,
        client = http.create_client()
    )
