from grawlix import arguments, config

from dataclasses import dataclass
import os

@dataclass(slots=True)
class Options:
    """
    Combined options from cli arguments and config file.
    """
    urls: list[str]
    cookie_file: str | None
    book_output_template: str
    series_output_template: str
    username: str | None
    password: str | None
    debug: bool
    source_options: dict[str, config.SourceConfig]


def load_options() -> Options:
    """
    Load options from command line arguments and configuration file.
    """
    args = arguments.parse_arguments()
    conf = config.load_config()

    urls = []
    if args.urls:
        urls.extend(args.urls)
    if args.file:
        with open(args.file, "r") as f:
            content = f.read()
            urls.extend(content.split("\n"))

    cookie_file = None
    if args.cookie_file is not None and os.path.exists(args.cookie_file):
        cookie_file = args.cookie_file
    elif os.path.exists("./cookies.txt"):
        cookie_file = "./cookies.txt"

    return Options(
        urls = urls,
        cookie_file = cookie_file,
        debug = args.debug,
        book_output_template = args.output or "{title}.{ext}",
        series_output_template = args.output or "{series}/{title}.{ext}",
        source_options = conf.sources,
        username = args.username,
        password = args.password,
    )
