from grawlix import __version__

import argparse

def parse_arguments() -> argparse.Namespace:
    # Help
    parser = argparse.ArgumentParser(
        prog = "grawlix",
        description = "Download ebooks"
    )
    parser.add_argument(
        '-v',
        '--version',
        action = "version",
        version = f"grawlix {__version__}"
    )
    # Basics
    parser.add_argument(
        'urls',
        help = "Links to ebooks",
        nargs = "*"
    )
    parser.add_argument(
        '-f',
        '--file',
        help = "File with links (One link per line)",
        dest = "file"
    )
    # Authentication
    parser.add_argument(
        '-u',
        '--username',
        help = "Username for login",
        dest = "username",
    )
    parser.add_argument(
        '-p',
        '--password',
        help = "Password for login",
        dest = "password",
    )
    parser.add_argument(
        '--library',
        help = "Library for login",
        dest = "library",
    )
    parser.add_argument(
        '-c',
        '--cookies',
        help = "Path to netscape cookie file",
        dest = "cookie_file"
    )
    # Outputs
    parser.add_argument(
        '-o',
        '--output',
        help = "Output destination",
        dest = "output"
    )
    # Logging
    parser.add_argument(
        '--debug',
        help = "Enable debug messages",
        dest = "debug",
        action="store_true",
    )
    return parser.parse_args()
