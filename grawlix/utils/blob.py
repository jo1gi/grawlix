from grawlix.encryption import Encryption, decrypt
from grawlix.utils import http

from dataclasses import dataclass
from typing import TypeAlias, Any
from enum import Enum


class Format(Enum):
    """Description of the filetype of a blob."""
    Epub = 0x00
    Pdf = 0x01
    Html = 0x02
    Jpg = 0x10
    Png = 0x11
    Acsm = 0x20


def extension_of_format(format: Format) -> str:
    """
    Get the default file extension of a format.

    :param foramt: The format to get the file extension of.
    :returns: The default file extension.
    """
    match format:
        case Format.Epub: return "epub"
        case Format.Pdf: return "pdf"
        case Format.Html: return "html"
        case Format.Jpg: return "jpg"
        case Format.Png: return "png"
        case Format.Acsm: return "acsm"


@dataclass(slots=True)
class Blob:
    """
    Unstructured data. Can be remote.
    """
    content: http.Request | bytes
    format: Format
    encryption: Encryption | None = None


def request(
    url: str,
    format: Format,
    headers: dict[str, str] | None = None,
    cookies: Any = None,
    encryption: Encryption | None = None
) -> Blob:
    """Create a blob with a request."""
    return Blob(
        content = http.Request(
            method = "GET",
            url = url,
            headers = headers or {},
            cookies = cookies,
        ),
        format = format,
        encryption = encryption
    )


async def get_content(blob: Blob, client: http.Client, update: http.Update = None) -> bytes:
    """
    Get the content of a blob.

    Will download the content if it is described as a `http.Request`.
    Will decrypt the content if `blob.encryption` is defined.

    :param blob: The blob to retrieve content from.
    :param client: The http client used to download the blob.
    :returns: The content of the blob.
    """
    if isinstance(blob.content, http.Request):
        content = await http.download_with_progress(client, blob.content, update)
    else:
        content = blob.content

    if blob.encryption:
        decrypt(content, blob.encryption)

    return content


async def write_to_file(blob: Blob, path: str, client: http.Client, update: http.Update = None):
    """
    Write a blob to a file.

    :param blob: The blob to write.
    :param path: The path where the blob should be written to.
    :param client: The http client used to retrieve the blob.
    """
    content = await get_content(blob, client, update)
    with open(path, "wb") as f:
        f.write(content)
