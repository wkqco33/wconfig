from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import count
import os
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
    name: str
    kind: str
    priority: int
    order: int
    origin: str | None = None


@dataclass(frozen=True, slots=True)
class _SourceLayer:
    info: SourceInfo
    data: dict[str, Any]


class Config:
    def __init__(
        self,
        *,
        env_prefix: str | None = None,
        env_prefix_separator: str = "_",
        env_nested_delimiter: str = "__",
        key_delimiter: str = ".",
    ) -> None:
        self._env_prefix = env_prefix
        self._env_prefix_separator = env_prefix_separator
        self._env_nested_delimiter = env_nested_delimiter
        self._key_delimiter = key_delimiter
        self._sources: list[_SourceLayer] = []
        self._counter = count()
        self._merged: dict[str, Any] = {}

    def set_defaults(self, data: Mapping[str, Any], *, name: str = "defaults") -> Config:
        return self._add_source(kind="defaults", name=name, data=normalize_mapping(data), priority=_DEFAULTS_PRIORITY)

    def load_mapping(
        self,
        data: Mapping[str, Any],
        *,
        name: str = "mapping",
        priority: int = _FILE_PRIORITY,
    ) -> Config:
        return self._add_source(kind="mapping", name=name, data=normalize_mapping(data), priority=priority)

    def load_file(self, path: str | Path, *, name: str | None = None) -> Config:
        file_path = Path(path)
        return self._add_source(
            kind="file",
            name=name or file_path.name,
            origin=str(file_path),
            data=load_file_data(file_path),
            priority=_FILE_PRIORITY,
        )

    def load_files(self, *paths: str | Path) -> Config:
        for path in paths:
            self.load_file(path)
        return self

    def load_dotenv(
        self,
        path: str | Path = ".env",
        *,
        name: str | None = None,
        prefix: str | None = None,
    ) -> Config:
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
        mapping = dict(os.environ if environ is None else environ)
        data = build_nested_mapping(
            mapping.items(),
            prefix=self._env_prefix if prefix is None else prefix,
            prefix_separator=self._env_prefix_separator,
            nested_delimiter=self._env_nested_delimiter,
        )
        return self._add_source(kind="env", name=name, data=data, priority=_ENV_PRIORITY)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return get_path(self._merged, key, delimiter=self._key_delimiter)
        except KeyError:
            return default

    def require(self, key: str) -> Any:
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise MissingConfigKeyError(key)
        return value

    def has(self, key: str) -> bool:
        return self.get(key, _MISSING) is not _MISSING

    def as_dict(self) -> dict[str, Any]:
        return deep_merge({}, self._merged)

    def decode(self, target_type: type[T], *, key: str | None = None) -> T:
        source = self.require(key) if key else self.as_dict()
        path = key or target_type.__name__
        return decode_to_type(source, target_type, path=path)

    def sources(self) -> tuple[SourceInfo, ...]:
        return tuple(layer.info for layer in sorted(self._sources, key=lambda layer: (layer.info.priority, layer.info.order)))

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
        for layer in sorted(self._sources, key=lambda item: (item.info.priority, item.info.order)):
            merged = deep_merge(merged, layer.data)
        self._merged = merged


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
    config = Config(
        env_prefix=env_prefix,
        env_prefix_separator=env_prefix_separator,
        env_nested_delimiter=env_nested_delimiter,
    )
    if defaults:
        config.set_defaults(defaults)
    for path in files:
        config.load_file(path)
    if dotenv is not None:
        config.load_dotenv(dotenv)
    if env:
        config.load_env(environ)
    return config
