from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from typing import Any, TypeVar

from ._decode import decode_to_type
from ._parsers import load_dotenv_data, load_file_data
from ._utils import build_nested_mapping, deep_merge, get_path, normalize_mapping
from .errors import MissingConfigKeyError

T = TypeVar("T")

_DEFAULTS_PRIORITY = 10
_FILE_PRIORITY = 20
_DOTENV_PRIORITY = 30
_ENV_PRIORITY = 40
_MISSING = object()


@dataclass(frozen=True, slots=True)
class SourceInfo:
    """Metadata describing a registered configuration source layer."""

    name: str
    kind: str
    priority: int
    order: int
    origin: str | None = None


@dataclass(frozen=True, slots=True)
class ValueSource:
    """A resolved configuration value alongside its origin source metadata."""

    key: str
    value: Any
    source: SourceInfo


@dataclass(frozen=True, slots=True)
class _SourceLayer:
    info: SourceInfo
    data: dict[str, Any]


class Config:
    """Hierarchical configuration loader and container."""

    def __init__(
        self,
        *,
        env_prefix: str | None = None,
        env_prefix_separator: str = "_",
        env_nested_delimiter: str = "__",
        key_delimiter: str = ".",
    ) -> None:
        self._env_prefix: str | None = env_prefix
        self._env_prefix_separator: str = env_prefix_separator
        self._env_nested_delimiter: str = env_nested_delimiter
        self._key_delimiter: str = key_delimiter
        self._sources: list[_SourceLayer] = []
        self._counter: Iterator[int] = count()
        self._merged: dict[str, Any] = {}

    def set_defaults(
        self, data: Mapping[str, Any], *, name: str = "defaults"
    ) -> Config:
        """Register default configuration values."""
        return self._add_source(
            kind="defaults",
            name=name,
            data=normalize_mapping(data),
            priority=_DEFAULTS_PRIORITY,
        )

    def load_mapping(
        self,
        data: Mapping[str, Any],
        *,
        name: str = "mapping",
        priority: int = _FILE_PRIORITY,
    ) -> Config:
        """Load configuration values from an in-memory mapping."""
        return self._add_source(
            kind="mapping", name=name, data=normalize_mapping(data), priority=priority
        )

    def load_file(self, path: str | Path, *, name: str | None = None) -> Config:
        """Load configuration values from a JSON, TOML, or YAML file."""
        file_path = Path(path)
        return self._add_source(
            kind="file",
            name=name or file_path.name,
            origin=str(file_path),
            data=load_file_data(file_path),
            priority=_FILE_PRIORITY,
        )

    def load_files(self, *paths: str | Path) -> Config:
        """Load configuration values from multiple files in order."""
        for path in paths:
            _ = self.load_file(path)
        return self

    def load_dotenv(
        self,
        path: str | Path = ".env",
        *,
        name: str | None = None,
        prefix: str | None = None,
    ) -> Config:
        """Load configuration values from a .env file."""
        dotenv_path = Path(path)
        data = build_nested_mapping(
            load_dotenv_data(dotenv_path).items(),
            prefix=self._env_prefix if prefix is None else prefix,
            prefix_separator=self._env_prefix_separator,
            nested_delimiter=self._env_nested_delimiter,
        )
        return self._add_source(
            kind="dotenv",
            name=name or dotenv_path.name,
            origin=str(dotenv_path),
            data=data,
            priority=_DOTENV_PRIORITY,
        )

    def load_env(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        name: str = "environment",
        prefix: str | None = None,
    ) -> Config:
        """Load configuration values from environment variables."""
        mapping = dict(os.environ if environ is None else environ)
        data = build_nested_mapping(
            mapping.items(),
            prefix=self._env_prefix if prefix is None else prefix,
            prefix_separator=self._env_prefix_separator,
            nested_delimiter=self._env_nested_delimiter,
        )
        return self._add_source(
            kind="env", name=name, data=data, priority=_ENV_PRIORITY
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value by dotted key path."""
        try:
            return get_path(self._merged, key, delimiter=self._key_delimiter)
        except KeyError:
            return default

    def require(self, key: str) -> Any:
        """Retrieve a configuration value, raising MissingConfigKeyError if missing."""
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise MissingConfigKeyError(key)
        return value

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return self.get(key, _MISSING) is not _MISSING

    def as_dict(self) -> dict[str, Any]:
        """Return the fully merged configuration as a dictionary."""
        return deep_merge({}, self._merged)

    def decode(self, target_type: type[T], *, key: str | None = None) -> T:
        """Decode the merged configuration or a subtree into a target type."""
        source = self.require(key) if key else self.as_dict()
        path = key or target_type.__name__
        return decode_to_type(source, target_type, path=path)

    def sources(self) -> tuple[SourceInfo, ...]:
        """Return all registered source layers sorted by priority and order."""
        return tuple(
            layer.info
            for layer in sorted(
                self._sources, key=lambda layer: (layer.info.priority, layer.info.order)
            )
        )

    def get_source(self, key: str) -> ValueSource:
        """Return the winning value and source layer metadata for a key."""
        normalized_key = self._normalize_lookup_key(key)
        for layer in sorted(
            self._sources,
            key=lambda item: (item.info.priority, item.info.order),
            reverse=True,
        ):
            try:
                value = get_path(
                    layer.data, normalized_key, delimiter=self._key_delimiter
                )
            except KeyError:
                continue
            return ValueSource(
                key=normalized_key,
                value=deep_merge({}, {"value": value})["value"],
                source=layer.info,
            )
        raise MissingConfigKeyError(key)

    def _add_source(
        self,
        *,
        kind: str,
        name: str,
        data: Mapping[str, Any],
        priority: int,
        origin: str | None = None,
    ) -> Config:
        info = SourceInfo(
            name=name,
            kind=kind,
            priority=priority,
            order=next(self._counter),
            origin=origin,
        )
        self._sources.append(_SourceLayer(info=info, data=normalize_mapping(data)))
        self._rebuild()
        return self

    def _rebuild(self) -> None:
        merged: dict[str, Any] = {}
        for layer in sorted(
            self._sources, key=lambda item: (item.info.priority, item.info.order)
        ):
            merged = deep_merge(merged, layer.data)
        self._merged = merged

    def _normalize_lookup_key(self, key: str) -> str:
        return self._key_delimiter.join(
            part.strip().replace("-", "_").lower()
            for part in key.split(self._key_delimiter)
            if part.strip()
        )


def load_config(
    *,
    defaults: Mapping[str, Any] | None = None,
    files: tuple[str | Path, ...] = (),
    dotenv: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    env: bool = True,
    env_prefix: str | None = None,
    env_prefix_separator: str = "_",
    env_nested_delimiter: str = "__",
) -> Config:
    """Convenience function to construct and populate a Config instance."""
    config = Config(
        env_prefix=env_prefix,
        env_prefix_separator=env_prefix_separator,
        env_nested_delimiter=env_nested_delimiter,
    )
    if defaults:
        _ = config.set_defaults(defaults)
    for path in files:
        _ = config.load_file(path)
    if dotenv is not None:
        _ = config.load_dotenv(dotenv)
    if env:
        _ = config.load_env(environ)
    return config
