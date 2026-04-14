from __future__ import annotations

import ast
import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._utils import normalize_mapping
from .errors import ConfigDecodeError, ConfigFileNotFoundError, UnsupportedConfigFormatError


def load_file_data(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigFileNotFoundError(f"Configuration file does not exist: {file_path}")
    if not file_path.is_file():
        raise ConfigDecodeError(f"Configuration path is not a file: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".json":
        data = _load_json(file_path)
    elif suffix == ".toml":
        data = _load_toml(file_path)
    elif suffix in {".yaml", ".yml"}:
        data = _load_yaml(file_path)
    else:
        raise UnsupportedConfigFormatError(
            f"Unsupported config format for {file_path.name!r}: expected .json, .toml, .yaml, or .yml"
        )

    if not isinstance(data, Mapping):
        raise ConfigDecodeError(f"Top-level config in {file_path} must be a mapping")
    return normalize_mapping(data)


def load_dotenv_data(path: str | Path) -> dict[str, str]:
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigFileNotFoundError(f".env file does not exist: {file_path}")
    if not file_path.is_file():
        raise ConfigDecodeError(f".env path is not a file: {file_path}")

    items: list[tuple[str, str]] = []
    for line_number, raw_line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        if "=" not in stripped:
            raise ConfigDecodeError(f"Invalid .env assignment at {file_path}:{line_number}")

        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            raise ConfigDecodeError(f"Missing key in .env assignment at {file_path}:{line_number}")

        items.append((key, _parse_dotenv_value(raw_value.strip(), file_path, line_number)))
    return dict(items)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigDecodeError(f"Invalid JSON in {path}: {exc}") from exc


def _load_toml(path: Path) -> Any:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigDecodeError(f"Invalid TOML in {path}: {exc}") from exc


def _load_yaml(path: Path) -> Any:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ConfigDecodeError("YAML support requires the PyYAML dependency") from exc

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigDecodeError(f"Invalid YAML in {path}: {exc}") from exc
    return {} if data is None else data


def _parse_dotenv_value(raw_value: str, path: Path, line_number: int) -> str:
    if not raw_value:
        return ""

    if raw_value[0] in {'"', "'"}:
        try:
            value = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError) as exc:
            raise ConfigDecodeError(f"Invalid quoted .env value at {path}:{line_number}") from exc
        if not isinstance(value, str):
            raise ConfigDecodeError(f"Quoted .env value must resolve to a string at {path}:{line_number}")
        return value

    hash_index = raw_value.find(" #")
    if hash_index >= 0:
        return raw_value[:hash_index].rstrip()
    return raw_value
