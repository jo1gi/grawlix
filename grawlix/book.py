from grawlix.encryption import Encryption
from dataclasses import dataclass, field
from typing import Optional, Union, TypeVar, Generic, Any, Literal
from datetime import date
from grawlix.utils import blob

@dataclass(slots=True)
class Metadata:
    """Metadata about a book"""
    title: str
    series: Optional[str] = None
    index: Optional[int] = None
    authors: list[str] = field(default_factory=list)
    language: Optional[str] = None
    publisher: Optional[str] = None
    identifier: Optional[str] = None
    description: Optional[str] = None
    release_date: Optional[date] = None

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "series": self.series or "UNKNOWN",
            "index": self.index or "UNKNOWN",
            "publisher": self.publisher or "UNKNOWN",
            "identifier": self.identifier or "UNKNOWN",
            "language": self.language or "UNKNOWN",
            "authors": "; ".join(self.authors),
            "description": self.description or "UNKNOWN",
            "release_date": self.release_date.isoformat() if self.release_date else "UNKNOWN",
        }


@dataclass(slots=True)
class ImageList:
    """
    List of images
    Mostly used for comic books
    """
    images: list[blob.Blob]


@dataclass(slots=True)
class EpubInParts:
    """
    Epub split up into smaller epubs
    """
    files: list[blob.Blob]
    files_in_toc: dict[str, str]


@dataclass(slots=True)
class HtmlFile:
    title: str
    file: blob.Blob
    selector: Optional[dict[str, str]]


@dataclass(slots=True)
class HtmlFiles:
    htmlfiles: list[HtmlFile]
    cover: Optional[blob.Blob] = None


BookData = Union[
    blob.Blob,
    EpubInParts,
    ImageList,
    HtmlFiles
]


@dataclass(slots=True)
class Book[T: BookData]:
    """Stores information about a book"""
    metadata: Metadata
    data: T
    overwrite: bool = False

T = TypeVar("T")


@dataclass(slots=True)
class Series[T]:
    """Stores a series of books"""
    title: str
    book_ids: list[T]


Result = Union[
    Book,
    Series[T]
]


@dataclass(slots=True)
class StandardBookId[T]:
    """
    A book id wih two variants: "book" and "series".
    """
    variant: Literal["series", "book"]
    value: T
