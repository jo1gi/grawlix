from dataclasses import dataclass
from typing import Optional
import tomli
from platformdirs import user_config_dir
import os


@dataclass(slots=True)
class SourceConfig:
    """Stores configuration for source"""
    username: Optional[str]
    password: Optional[str]


@dataclass(slots=True)
class Config:
    """Grawlix configuration"""
    sources: dict[str, SourceConfig]
    write_metadata_to_epub: bool = False
    output: Optional[str] = None


def load_config() -> Config:
    """
    Load config from disk

    :returns: Config object
    """
    config_dir = user_config_dir("grawlix", "jo1gi")
    config_file = os.path.join(config_dir, "grawlix.toml")
    if os.path.exists(config_file):
        try:
            with open(config_file, "rb") as f:
                config_dict = tomli.load(f)
        except tomli.TOMLDecodeError as e:
            print(f"Error parsing config file: {config_file}")
            print(f"  {e}")
            print("\nPlease check your TOML syntax. Common issues:")
            print("  - Strings must be quoted: output = \"{title}.{ext}\" not output = {title}.{ext}")
            print("  - Booleans are lowercase: write_metadata_to_epub = true (not True)")
            print("  - Use double quotes for strings containing special characters")
            raise
    else:
        config_dict = {}
    sources = {}
    if "sources" in config_dict:
        for key, values in config_dict["sources"].items():
            sources[key] = SourceConfig (
                username = values.get("username"),
                password = values.get("password"),
            )

    # Load general settings
    write_metadata_to_epub = config_dict.get("write_metadata_to_epub", False)
    output = config_dict.get("output")

    return Config(sources, write_metadata_to_epub, output)
