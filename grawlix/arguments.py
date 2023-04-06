from grawlix import __version__

import argparse

def parse_arguments():
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
    # Outputs
    return parser.parse_args()
