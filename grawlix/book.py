from grawlix import Encryption
from dataclasses import dataclass
from typing import Optional, Union, TypeVar, Generic

@dataclass(slots=True)
class Metadata:
    """Metadata about a book"""
    title: str
    series: Optional[str] = None
    publisher: Optional[str] = None
    identifier: Optional[str] = None


@dataclass(slots=True)
class OnlineFile:
    """Instructions for downloading an online file"""
    url: str
    extension: str
    encryption: Optional[Encryption] = None
    headers: Optional[dict[str, str]] = None


@dataclass(slots=True)
class SingleFile:
    """Bookdata in the form of a single file"""
    file: OnlineFile


@dataclass(slots=True)
class ImageList:
    """
    List of images
    Mostly used for comic books
    """
    images: list[OnlineFile]

BookData = Union[
    SingleFile,
    ImageList
]

@dataclass(slots=True)
class Book:
    """Stores information about a book"""
    metadata: Metadata
    data: BookData

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
