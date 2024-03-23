import requests

from .source import Source
from grawlix import Metadata

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from typing import Any, List, Dict, Optional
from urllib3.util import parse_url
from datetime import datetime, date
import pycountry
import json
import re
import os

from .. import Book
from ..book import Result, Series, BookData, OnlineFile, SingleFile

# fmt: off
metadata_corrections: dict[str, dict[str, Any]] = {
    "books": {
        "1623721": {"title": "Bibi & Tina: Schatten über dem Martinshof", "release_date": date(2010, 3, 12)},
        "1623873": {"title": "Bibi & Tina: Die ungarischen Reiter", "release_date": date(2010, 9, 10)},
        "1623776": {"title": "Bibi & Tina: Der wilde Hengst", "release_date": date(2009, 11, 20)},
        "1623780": {"title": "Bibi & Tina: Die geheimnisvolle Köchin", "release_date": date(2012, 6, 8)},
        "1623767": {"title": "Bibi & Tina: Der Tiger von Rotenbrunn", "release_date": date(2013, 9, 6)},
        "1623757": {"title": "Bibi & Tina: Die falschen Weihnachtsmänner", "release_date": date(2013, 11, 1)},
        "1623860": {"title": "Bibi & Tina: Indianerpferde in Gefahr", "release_date": date(2014, 9, 5)},
        "1623775": {"title": "Bibi & Tina: Der weiße Mustang", "release_date": date(2015, 9, 4)},
        "1623856": {"title": "Bibi & Tina: Holger verliebt sich", "release_date": date(2016, 9, 9)},
        "1623760": {"title": "Bibi & Tina: Das Fohlen im Schnee", "release_date": date(2017, 9, 8)},
        "1623855": {"title": "Bibi & Tina: Ein heißer Sommer", "release_date": date(2018, 7, 6)},
        "1623857": {"title": "Bibi & Tina: Im Land der weißen Pferde", "release_date": date(2019, 9, 6)},
        "1048495": {"title": "Bibi & Tina: Der mysteriöse Fremde",
                    "description": "Graf Falko von Falkenstein ist verzweifelt! Er leidet unter Schlaflosigkeit und bittet schließlich einen Wunderheiler um Hilfe. Der mysteriöse Fremde heilt nicht nur den Grafen, sondern wickelt sogar Frau Martin um den Finger. Tina ist gar nicht begeistert und auch Bibi misstraut dem Mann. Als die Freundinnen und Alex versuchen, dem Geheimnis des Heilers auf die Spur zu kommen, überschlagen sich die Ereignisse und die Kinder geraten in Gefahr.",
                    "release_date": date(2020, 10, 23)},
        # MP3 contains the audio twice in a row (second one starts at 2:34:52)
        "1397689": {"title": "Bibi & Tina: Ein Monster im Wald", "release_date": date(2021, 10, 22)},

        "1615235": {"title": "Bibi Blocksberg - Hörbuch: Im Tal der wilden Hexen", "release_date": date(2010, 3, 20)},
        "1615295": {"title": "Bibi Blocksberg - Das verhexte Wunschhaus", "release_date": date(2011, 3, 4)},
        "1615294": {"title": "Bibi Blocksberg - Die Gewitterhexe", "release_date": date(2012, 10, 19)},
        "1615236": {"title": "Bibi Blocksberg - Zickia-Alarm!", "release_date": date(2013, 6, 7)},
        "1615182": {"title": "Bibi Blocksberg - Das verhexte Schwein", "release_date": date(2013, 10, 11)},
        "1615288": {"title": "Bibi Blocksberg - Bibi total verknallt!", "release_date": date(2014, 6, 6)},
        "1615205": {"title": "Bibi Blocksberg - Hexkraft gesucht!", "release_date": date(2014, 10, 10)},
        "1615204": {"title": "Bibi Blocksberg - Wo ist Moni?", "release_date": date(2015, 6, 12)},
        "1615203": {"title": "Bibi Blocksberg - Gustav, der Hexendrache", "release_date": date(2015, 10, 9)},
        "1615175": {"title": "Bibi Blocksberg - Abenteuer Indien!", "release_date": date(2017, 10, 13)},
        "1615201": {"title": "Bibi Blocksberg - Die Schule ist weg!", "release_date": date(2018, 10, 12)},
        "1022245": {"title": "Bibi Blocksberg - Bibi und Herr Fu", "release_date": date(2020, 9, 18)},

        "522762": {"title": "Alvin und die Chipmunks: Der Katzenfluch"},

        "1260956": {"title": "Fast and Furious Spy Racer: Folge 1"},

        "1878866": {"title": "Ghostforce: Folge 1"},
        "1878880": {"title": "Ghostforce: Folge 2"},
        "2642089": {"title": "Ghostforce: Folge 3"},
        "2642148": {"title": "Ghostforce: Folge 4"},

        "1168061": {"title": "Leo Da Vinci: Folge 1", "series": "Leo Da Vinci", "series_order": 1},
        "1176396": {"title": "Leo Da Vinci: Folge 2", "series": "Leo Da Vinci", "series_order": 2},
        "1178721": {"title": "Leo Da Vinci: Folge 3", "series": "Leo Da Vinci", "series_order": 3},
        "1176422": {"title": "Leo Da Vinci: Folge 4", "series": "Leo Da Vinci", "series_order": 4},
        "1176424": {"title": "Leo Da Vinci: Folge 5", "series": "Leo Da Vinci", "series_order": 5},
        "1176462": {"title": "Leo Da Vinci: Folge 6", "series": "Leo Da Vinci", "series_order": 6},
        "1262342": {"title": "Leo Da Vinci: Folge 7", "series": "Leo Da Vinci", "series_order": 7},
        "1263433": {"title": "Leo Da Vinci: Folge 8", "series": "Leo Da Vinci", "series_order": 8},
        "1263421": {"title": "Leo Da Vinci: Folge 9", "series": "Leo Da Vinci", "series_order": 9},
        "1309115": {"title": "Leo Da Vinci: Folge 10", "series": "Leo Da Vinci", "series_order": 10},
        "1320400": {"title": "Leo Da Vinci: Folge 11", "series": "Leo Da Vinci", "series_order": 11},
        "1328193": {"title": "Leo Da Vinci: Folge 12", "series": "Leo Da Vinci", "series_order": 12},
    }
}
# fmt: on


# path data of the headphone icon on the website used to identify audiobooks
svg_headphone_path = "M8.25 12.371h-.625c-1.38 0-2.5 1.121-2.5 2.505v3.12a2.503 2.503 0 0 0 2.5 2.504h.625c.69 0 1.25-.56 1.25-1.252v-5.627c0-.691-.559-1.25-1.25-1.25Zm-.625 6.254a.628.628 0 0 1-.625-.63v-3.12c0-.347.28-.63.625-.63v4.38ZM12 3C6.41 3 2.178 7.652 2 13v4.375c0 .346.28.625.625.625h.625a.626.626 0 0 0 .625-.627V13c0-4.48 3.646-8.117 8.125-8.117 4.48 0 8.125 3.637 8.125 8.117v4.371c-.035.348.281.629.625.629l.625.001c.346 0 .625-.28.625-.625v-4.411C21.82 7.652 17.59 3 12 3Zm4.375 9.371h-.625c-.69 0-1.25.56-1.25 1.252v5.625c0 .692.56 1.252 1.25 1.252h.625c1.38 0 2.5-1.121 2.5-2.505v-3.12a2.503 2.503 0 0 0-2.5-2.504ZM17 17.996a.628.628 0 0 1-.625.629v-4.379c.345 0 .625.283.625.63v3.12Z"


class Storytel(Source[str]):
    match = [
        r"https?://(?:www.)?(?:storytel|mofibo).com/(?P<language>\w+)(?:/(?P<language2>\w+))?/(?P<list_type>(?:books|series|authors|narrators|publishers|categories))/.+",
    ]
    names = ["Storytel", "Mofibo"]
    _authentication_methods = [
        "login",
    ]
    _download_counter = 0
    create_storage_dir = True

    def __init__(self) -> None:
        super().__init__()
        self._session = requests.Session()

    def _get_playback_metadata_path(self, consumableId: str) -> str:
        return os.path.join(
            self.database_directory_playback_metadata, f"{consumableId}.json"
        )

    def _get_lists_path(self, list_name: str, languages: str, formats: str) -> str:
        return os.path.join(
            self.database_directory_lists, f"{list_name}_{languages}_{formats}.json"
        )

    def _skip_download_check(self, book_id: str) -> bool:
        return False

    @staticmethod
    def encrypt_password(password: str) -> str:
        """
        Encrypt password with predefined keys.
        This encrypted password is used for login.

        :param password: User defined password
        :returns: Encrypted password
        """
        # Thanks to https://github.com/javsanpar/storytel-tui
        key = b"VQZBJ6TD8M9WBUWT"
        iv = b"joiwef08u23j341a"
        msg = pad(password.encode(), AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        cipher_text = cipher.encrypt(msg)
        return cipher_text.hex()

    async def login(self, username: str, password: str, **kwargs: str) -> None:
        self._username = username
        self._password = self.encrypt_password(password)
        self._headers = []

        self._session.headers.update(
            {
                "User-Agent": "Storytel/23.49 (Android 13; Pixel 6) Release/2288481",
            }
        )
        self._do_login()

    def _do_login(self) -> None:
        resp = self._session.post(
            f"https://www.storytel.com/api/login.action?m=1&token=guestsv&userid=-1&version=23.49&terminal=android&locale=sv&deviceId=995f2562-0e44-4410-b1b9-8d08261f33c4&kidsMode=false",
            data={
                "uid": self._username,
                "pwd": self._password,
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise ConnectionError
        user_data = resp.json()
        jwt = user_data["accountInfo"]["jwt"]
        self._language = user_data["accountInfo"]["lang"]
        self._session.headers.update({"authorization": f"Bearer {jwt}"})

    def _relogin_check(self) -> None:
        """
        There's a ratelimit for the MP3 download, if triggered, it will invalidate all sessions and you'll get an email about suspicios activities on your account
        To avoid the rate limtier we regularly re-login to get a new session token (which seems to byepass the rate limiter)
        """
        if self._download_counter > 0 and self._download_counter % 10 == 0:
            print("refreshing login")
            self._do_login()

    @staticmethod
    def _clean_share_url(url: str) -> str:
        """remove query string/fragment from url"""
        return url.split("?")[0]

    def download_from_id(self, book_id: str) -> Book:
        self._relogin_check()
        book = self.download_book_from_book_id(book_id)
        return book

    async def download(self, url: str) -> Result:
        self._relogin_check()

        if m := re.match(self.match[0], url):
            language, language2, list_type = m.groups()
            print(f"download: {url=}, {list_type=}, {language=}, {language2=}")
            # individual books
            if list_type == "books":
                return self.download_book_from_url(url)
        raise ConnectionError

    def download_book_from_book_id(
            self,
            consumableId: str,
    ) -> Book:
        book_details = self.download_book_details(consumableId)
        metadata = self.get_metadata(book_details)
        files = self.get_files(book_details)

        return Book(
            metadata=metadata,
            data=files,
        )

    def download_book_from_url(self, url: str) -> Book:
        consumableId = self.get_id_from_url(url)
        return self.download_book_from_book_id(consumableId)

    @staticmethod
    def get_id_from_url(url: str) -> str:
        """
        Find book id in url

        :param url: Url to book
        :returns: Id of book from url
        """
        parsed = parse_url(url)
        if parsed.path is None:
            raise ConnectionError
        return parsed.path.split("-")[-1]

    def download_bookshelf(self) -> Dict[str, Any]:
        """Download bookshelf data"""
        resp = self._session.post(
            "https://api.storytel.net/libraries/bookshelf",
            json={"items": []},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        data: Dict[str, Any] = resp.json()

        bookshelf_path = os.path.join(self.database_directory_lists, f"bookshelf.json")
        with open(bookshelf_path, "w") as json_file:
            json_data = json.dumps(data, indent=2)
            json_file.write(json_data)

        return data

    def download_book_details(self, consumableId: str) -> Dict[str, Any]:
        """Download books details"""
        resp = self._session.get(
            f"https://api.storytel.net/book-details/consumables/{consumableId}?kidsMode=false&configVariant=default"
        )
        if resp.status_code == 404:
            raise FileNotFoundError
        data = resp.json()
        return data

    def get_epub_url(self, consumableId: str) -> str:
        """get audio URL

        Get the final Audio URL by sending a requests to the assets API and return the redirect location.
        """
        resp = self._session.get(
            f"https://api.storytel.net/assets/v2/consumables/{consumableId}/ebook",
            allow_redirects=False,
        )
        self._download_counter += 1
        if resp.status_code != 302:
            raise Exception(
                f"request to {resp.url} failed, got {resp.status_code} response: {resp.text}"
            )
        location: str = resp.headers["Location"]
        return location

    def get_files(self, book_info) -> BookData:
        consumableId = book_info["consumableId"]
        audio_url = self.get_epub_url(consumableId)

        return SingleFile(
            OnlineFile(
                url=audio_url,
                headers=self._session.headers,
                extension="epub"
            )
        )

    def get_metadata(self, book_details) -> Metadata:
        title = book_details["title"]
        metadata = Metadata(title)
        for author in book_details["authors"]:
            metadata.authors += author["name"]
        if "isbn" in book_details:
            if book_details["isbn"]:
                metadata.isbn = book_details["isbn"]
        if "description" in book_details:
            metadata.description = book_details["description"]
        if "language" in book_details:
            if "name" in book_details["language"]:
                metadata.language = pycountry.languages.get(
                    name=book_details["language"]["name"]
                )
        if "seriesInfo" in book_details and book_details["seriesInfo"]:
            metadata.series = book_details["seriesInfo"]["name"]
            if "orderInSeries" in book_details["seriesInfo"]:
                metadata.series_order = book_details["seriesInfo"]["orderInSeries"]

        if not "formats" in book_details:
            raise Exception
        abook_formats = [f for f in book_details["formats"] if f["type"] == "abook"]
        if len(abook_formats) == 0:
            raise Exception
        elif len(abook_formats) != 1:
            raise Exception(
                "multiple abook formats",
                f"found multiple abook formats, please report this audiobook for bugfixing",
            )

        format = book_details["formats"][0]
        if "isReleased" in format:
            if not format["isReleased"]:
                raise Exception
        if "publisher" in format:
            if "name" in format["publisher"]:
                metadata.publisher = format["publisher"]["name"]
        if "releaseDate" in format:
            date_str: str = format["releaseDate"]
            # metadata.release_date = datetime.fromisoformat(date_str).date()
            metadata.release_date = datetime.strptime(
                date_str, "%Y-%m-%dT%H:%M:%SZ"
            ).date()
        return metadata
