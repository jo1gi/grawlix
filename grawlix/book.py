from grawlix import Encryption
from dataclasses import dataclass, field
from typing import Optional, Union, TypeVar, Generic, Any

@dataclass(slots=True)
class Metadata:
    """Metadata about a book"""
    title: str
    series: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    language: Optional[str] = None
    publisher: Optional[str] = None
    identifier: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "series": self.series or "UNKNOWN",
            "publisher": self.publisher or "UNKNOWN",
            "identifier": self.identifier or "UNKNOWN",
            "language": self.language or "UNKNOWN",
            "authors": "; ".join(self.authors),
        }


@dataclass(slots=True)
class OnlineFile:
    """Instructions for downloading an online file"""
    url: str
    extension: str
    encryption: Optional[Encryption] = None
    headers: Optional[dict[str, str]] = None
    cookies: Optional[Any] = None # TODO Change type

@dataclass(slots=True)
class OfflineFile:
    """Stores content of a file"""
    content: bytes
    extension: str
    encryption: Optional[Encryption] = None

File = Union[OnlineFile, OfflineFile]


@dataclass(slots=True)
class SingleFile:
    """Bookdata in the form of a single file"""
    file: File


@dataclass(slots=True)
class ImageList:
    """
    List of images
    Mostly used for comic books
    """
    images: list[OnlineFile]

@dataclass(slots=True)
class HtmlFile:
    title: str
    file: OnlineFile
    selector: Optional[dict[str, str]]

@dataclass(slots=True)
class HtmlFiles:
    htmlfiles: list[HtmlFile]
    cover: Optional[OnlineFile] = None

BookData = Union[
    SingleFile,
    ImageList,
    HtmlFiles
]

@dataclass(slots=True)
class Book:
    """Stores information about a book"""
    metadata: Metadata
    data: BookData
    overwrite: bool = False

T = TypeVar("T")

@dataclass(slots=True)
class Series(Generic[T]):
    """Stores a series of books"""
    title: str
    book_ids: list[T]

Result = Union[
    Book,
    Series[T]
]
