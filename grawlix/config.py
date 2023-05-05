from dataclasses import dataclass
from typing import Optional
import tomli
import appdirs
import os


@dataclass(slots=True)
class SourceConfig:
    """Stores configuration for source"""
    username: Optional[str]
    password: Optional[str]
    library: Optional[str]


@dataclass(slots=True)
class Config:
    """Grawlix configuration"""
    sources: dict[str, SourceConfig]


def load_config() -> Config:
    """
    Load config from disk

    :returns: Config object
    """
    config_dir = appdirs.user_config_dir("grawlix", "jo1gi")
    config_file = os.path.join(config_dir, "grawlix.toml")
    if os.path.exists(config_file):
        with open(config_file, "rb") as f:
            config_dict = tomli.load(f)
    else:
        config_dict = {}
    sources = {}
    if "sources" in config_dict:
        for key, values in config_dict["sources"].items():
            sources[key] = SourceConfig (
                username = values.get("username"),
                password = values.get("password"),
                library = values.get("library"),
            )
    return Config(sources)
