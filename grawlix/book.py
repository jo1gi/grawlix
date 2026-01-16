from grawlix import Encryption
from dataclasses import dataclass, field
from typing import Optional, Union, TypeVar, Generic, Any
from datetime import date

@dataclass(slots=True)
class Metadata:
    """Metadata about a book"""
    title: str
    series: Optional[str] = None
    index: Optional[int] = None
    authors: list[str] = field(default_factory=list)
    language: Optional[str] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    release_date: Optional[date] = None
    source: Optional[str] = None
    original_title: Optional[str] = None
    translators: list[str] = field(default_factory=list)
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    # EPUB 3 rendition properties (fixed-layout support)
    rendition_layout: Optional[str] = None      # "pre-paginated" or "reflowable"
    rendition_spread: Optional[str] = None      # "none", "auto", "landscape", "portrait", "both"
    rendition_orientation: Optional[str] = None # "auto", "landscape", "portrait"

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "series": self.series or "UNKNOWN",
            "index": str(self.index) if self.index is not None else "UNKNOWN",
            "publisher": self.publisher or "UNKNOWN",
            "isbn": self.isbn or "UNKNOWN",
            "language": self.language or "UNKNOWN",
            "authors": "; ".join(self.authors),
            "description": self.description or "UNKNOWN",
            "release_date": self.release_date.isoformat() if self.release_date else "UNKNOWN",
            "source": self.source or "UNKNOWN",
            "original_title": self.original_title or "UNKNOWN",
            "translators": "; ".join(self.translators),
            "category": self.category or "UNKNOWN",
            "tags": "; ".join(self.tags),
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
class EpubInParts:
    """
    Epub split up into smaller epubs
    """
    files: list[OnlineFile]
    files_in_toc: dict[str, str]


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
    EpubInParts,
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
