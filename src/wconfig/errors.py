class ConfigError(Exception):
    """Base error for all package-level configuration failures."""


class ConfigDecodeError(ConfigError):
    """Raised when configuration content cannot be parsed or decoded."""


class ConfigFileNotFoundError(ConfigError, FileNotFoundError):
    """Raised when a requested configuration file does not exist."""


class UnsupportedConfigFormatError(ConfigError):
    """Raised when a config file extension is not supported."""


class MissingConfigKeyError(ConfigError, KeyError):
    """Raised when a required key cannot be found in the merged config."""
