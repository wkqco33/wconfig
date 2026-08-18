from __future__ import annotations

import json
from collections.abc import (
    Mapping as AbcMapping,
    MutableMapping as AbcMutableMapping,
    MutableSequence as AbcMutableSequence,
    MutableSet as AbcMutableSet,
    Sequence as AbcSequence,
    Set as AbcSet,
)
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, Literal, Union, cast, get_args, get_origin, get_type_hints

from ._utils import normalize_key
from .errors import ConfigDecodeError

_SEQUENCE_ORIGINS = {
    list,
    set,
    frozenset,
    AbcSequence,
    AbcMutableSequence,
    AbcSet,
    AbcMutableSet,
}
_MAPPING_ORIGINS = {dict, AbcMapping, AbcMutableMapping}


def decode_to_type(value: Any, target_type: type[Any], *, path: str) -> Any:
    origin = get_origin(target_type)

    if target_type in {Any, object}:
        return value
    if target_type is NoneType:
        if value is None:
            return None
        raise ConfigDecodeError(f"Expected null at {path}, got {type(value).__name__}")
    if is_dataclass(target_type):
        return _decode_dataclass(value, target_type, path=path)
    if isinstance(target_type, type) and issubclass(target_type, Enum):
        return _decode_enum(value, target_type, path=path)
    if target_type is Path or (
        isinstance(target_type, type) and issubclass(target_type, Path)
    ):
        return _decode_path(value, target_type, path=path)
    if origin in _SEQUENCE_ORIGINS:
        return _decode_sequence(value, target_type, path=path)
    if origin is tuple:
        return _decode_tuple(value, target_type, path=path)
    if origin in _MAPPING_ORIGINS:
        return _decode_mapping(value, target_type, path=path)
    if origin in {UnionType, Union}:
        return _decode_union(value, target_type, path=path)
    if origin is Literal:
        return _decode_literal(value, target_type, path=path)
    if target_type is bool:
        return _decode_bool(value, path=path)
    if target_type in {str, int, float}:
        return _decode_scalar(value, target_type, path=path)
    return (
        value
        if isinstance(value, target_type)
        else _raise_type_error(path, target_type, value)
    )


def _decode_dataclass(value: Any, target_type: type[Any], *, path: str) -> Any:
    if not isinstance(value, dict):
        raise ConfigDecodeError(
            f"Expected mapping at {path}, got {type(value).__name__}"
        )

    type_hints = get_type_hints(target_type)
    kwargs: dict[str, Any] = {}
    for field in fields(target_type):
        field_key = normalize_key(field.name)
        field_path = f"{path}.{field.name}" if path else field.name
        if field_key not in value:
            if field.default is not MISSING or field.default_factory is not MISSING:
                continue
            raise ConfigDecodeError(f"Missing required field {field_path}")
        kwargs[field.name] = decode_to_type(
            value[field_key], type_hints.get(field.name, field.type), path=field_path
        )
    return target_type(**kwargs)


def _decode_enum(value: Any, target_type: type[Enum], *, path: str) -> Enum:
    if isinstance(value, target_type):
        return value

    # Try matching by enum value first (e.g. Color("red") or Code(1))
    try:
        return target_type(value)
    except (ValueError, TypeError, KeyError):
        pass

    # Try matching by enum name if value is string (e.g. Color["RED"] or Color["red"])
    if isinstance(value, str):
        try:
            return target_type[value]
        except KeyError:
            pass
        try:
            return target_type[value.upper()]
        except KeyError:
            pass

    raise ConfigDecodeError(
        f"Expected {target_type.__name__} at {path}, got {value!r}"
    )


def _decode_path(value: Any, target_type: type[Path], *, path: str) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        return target_type(value)
    raise ConfigDecodeError(f"Expected Path at {path}, got {type(value).__name__}")


def _coerce_to_sequence_items(value: Any, *, path: str) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    if isinstance(value, tuple | set | frozenset):
        return list(cast(tuple[object, ...] | set[object], value))
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []
        if (trimmed.startswith("[") and trimmed.endswith("]")) or (
            trimmed.startswith("(") and trimmed.endswith(")")
        ):
            try:
                parsed = json.loads(trimmed)
                if isinstance(parsed, list):
                    return cast(list[object], parsed)
            except (json.JSONDecodeError, ValueError):
                pass
        return [item.strip() for item in trimmed.split(",") if item.strip()]
    raise ConfigDecodeError(f"Expected list at {path}, got {type(value).__name__}")


def _decode_sequence(value: Any, target_type: type[Any], *, path: str) -> Any:
    values = _coerce_to_sequence_items(value, path=path)
    origin = get_origin(target_type)
    args = get_args(target_type)
    item_type = cast(type[object], args[0]) if args else object
    decoded = [
        decode_to_type(item, item_type, path=f"{path}[{index}]")
        for index, item in enumerate(values)
    ]
    if origin in {set, AbcSet, AbcMutableSet}:
        return set(decoded)
    if origin is frozenset:
        return frozenset(decoded)
    return decoded


def _decode_tuple(value: Any, target_type: type[Any], *, path: str) -> Any:
    values = _coerce_to_sequence_items(value, path=path)
    args = get_args(target_type)
    if len(args) == 2 and args[1] is Ellipsis:
        item_type = cast(type[object], args[0])
        return tuple(
            decode_to_type(item, item_type, path=f"{path}[{index}]")
            for index, item in enumerate(values)
        )
    if args and len(args) != len(values):
        raise ConfigDecodeError(
            f"Expected {len(args)} items at {path}, got {len(values)}"
        )
    return tuple(
        decode_to_type(
            item,
            cast(type[object], args[index]) if args else object,
            path=f"{path}[{index}]",
        )
        for index, item in enumerate(values)
    )


def _decode_mapping(value: Any, target_type: type[Any], *, path: str) -> Any:
    if not isinstance(value, dict | AbcMapping):
        raise ConfigDecodeError(
            f"Expected mapping at {path}, got {type(value).__name__}"
        )
    args = get_args(target_type)
    key_type = cast(type[object], args[0]) if args else str
    value_type = cast(type[object], args[1]) if len(args) >= 2 else object
    return {
        _decode_scalar(key, key_type, path=f"{path}.<key>"): decode_to_type(
            item, value_type, path=f"{path}.{key}"
        )
        for key, item in value.items()
    }


def _decode_union(value: Any, target_type: type[Any], *, path: str) -> Any:
    errors: list[str] = []
    for candidate in get_args(target_type):
        candidate_type = cast(type[object], candidate)
        try:
            return decode_to_type(value, candidate_type, path=path)
        except ConfigDecodeError as exc:
            errors.append(str(exc))
    raise ConfigDecodeError(
        f"Value at {path} did not match any allowed type: {'; '.join(errors)}"
    )


def _decode_literal(value: Any, target_type: type[Any], *, path: str) -> Any:
    allowed_values = get_args(target_type)
    for allowed in allowed_values:
        if value == allowed and type(value) is type(allowed):
            return value
    allowed_reprs = ", ".join(repr(v) for v in allowed_values)
    raise ConfigDecodeError(
        f"Expected one of {{{allowed_reprs}}} at {path}, got {value!r}"
    )


def _decode_bool(value: Any, *, path: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigDecodeError(f"Expected boolean at {path}, got {value!r}")


def _decode_scalar(value: Any, target_type: type[Any], *, path: str) -> Any:
    if isinstance(value, target_type) and not (
        target_type is int and isinstance(value, bool)
    ):
        return value
    if isinstance(value, str):
        try:
            return target_type(value)
        except ValueError as exc:
            raise ConfigDecodeError(
                f"Could not coerce value at {path} to {target_type.__name__}"
            ) from exc
    raise ConfigDecodeError(
        f"Expected {target_type.__name__} at {path}, got {type(value).__name__}"
    )


def _raise_type_error(path: str, target_type: type[Any], value: Any) -> Any:
    raise ConfigDecodeError(
        f"Expected {target_type!r} at {path}, got {type(value).__name__}"
    )

