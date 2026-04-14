from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any


def normalize_key(key: str) -> str:
    return key.strip().replace("-", "_").lower()


def normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return normalize_mapping(value)
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    return deepcopy(value)


def normalize_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    return {normalize_key(str(key)): normalize_value(value) for key, value in data.items()}


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
    result: dict[str, Any] = {}
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
