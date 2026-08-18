from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from .errors import ConfigNormalizationError


def normalize_key(key: str) -> str:
    return key.strip().replace("-", "_").lower()


def normalize_value(value: Any, *, path: str = "") -> Any:
    if isinstance(value, Mapping):
        return normalize_mapping(value, path=path)
    if isinstance(value, list):
        return [
            normalize_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return tuple(
            normalize_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    if isinstance(value, set):
        return {
            normalize_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        }
    if isinstance(value, frozenset):
        return frozenset(
            normalize_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    return deepcopy(value)


def normalize_mapping(
    data: Mapping[str, Any], *, path: str = ""
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    original_keys: dict[str, str] = {}
    for key, value in data.items():
        original_key = str(key)
        normalized_key = normalize_key(original_key)
        if normalized_key in normalized:
            previous_key = original_keys[normalized_key]
            location = path or "<root>"
            raise ConfigNormalizationError(
                f"Normalized key collision at {location}: "
                f"{previous_key!r} and {original_key!r} both normalize to "
                f"{normalized_key!r}"
            )
        original_keys[normalized_key] = original_key
        child_path = f"{path}.{normalized_key}" if path else normalized_key
        normalized[normalized_key] = normalize_value(value, path=child_path)
    return normalized


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = normalize_mapping(base)
    for key, value in override.items():
        normalized_key = normalize_key(str(key))
        normalized_value = normalize_value(value)
        current = merged.get(normalized_key)
        if isinstance(current, dict) and isinstance(normalized_value, dict):
            merged[normalized_key] = deep_merge(current, normalized_value)
            continue
        merged[normalized_key] = normalized_value
    return merged


def build_nested_mapping(
    items: Iterable[tuple[str, Any]],
    *,
    prefix: str | None,
    prefix_separator: str,
    nested_delimiter: str,
) -> dict[str, Any]:
    if not prefix_separator or not nested_delimiter:
        raise ValueError("Environment key delimiters must not be empty")

    result: dict[str, Any] = {}
    seen_paths: dict[tuple[str, ...], str] = {}
    prefix_token = None
    normalized_prefix = None
    if prefix:
        normalized_prefix = prefix.strip().upper()
        prefix_token = f"{normalized_prefix}{prefix_separator}"

    for raw_key, raw_value in items:
        env_key = raw_key.strip()
        if not env_key:
            continue

        if normalized_prefix:
            if env_key == normalized_prefix:
                key_body = ""
            elif prefix_token and env_key.startswith(prefix_token):
                key_body = env_key[len(prefix_token) :]
            else:
                continue
        else:
            key_body = env_key

        if not key_body:
            continue

        parts = [
            normalize_key(part)
            for part in key_body.split(nested_delimiter)
            if part and part.strip()
        ]
        if not parts:
            continue
        path = tuple(parts)
        for previous_path, previous_key in seen_paths.items():
            if (
                previous_path == path
                or previous_path[: len(path)] == path
                or path[: len(previous_path)] == previous_path
            ):
                raise ConfigNormalizationError(
                    f"Conflicting environment keys at {'.'.join(parts)!r}: "
                    f"{previous_key!r} and {raw_key!r}"
                )
        seen_paths[path] = raw_key
        set_path(result, parts, raw_value)
    return result


def set_path(data: dict[str, Any], parts: list[str], value: Any) -> None:
    cursor = data
    for part in parts[:-1]:
        current = cursor.get(part)
        if not isinstance(current, dict):
            current = {}
            cursor[part] = current
        cursor = current
    cursor[parts[-1]] = normalize_value(value)


def get_path(data: Mapping[str, Any], key: str, *, delimiter: str) -> Any:
    cursor: Any = data
    for part in [normalize_key(part) for part in key.split(delimiter) if part.strip()]:
        if not isinstance(cursor, Mapping) or part not in cursor:
            raise KeyError(key)
        cursor = cursor[part]
    return cursor
