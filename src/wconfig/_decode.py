from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from types import NoneType, UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from ._utils import normalize_key
from .errors import ConfigDecodeError


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
    if origin in {list, set, frozenset}:
        return _decode_sequence(value, target_type, path=path)
    if origin is tuple:
        return _decode_tuple(value, target_type, path=path)
    if origin is dict:
        return _decode_mapping(value, target_type, path=path)
    if origin in {UnionType, Union}:
        return _decode_union(value, target_type, path=path)
    if origin is Literal:
        return _decode_literal(value, target_type, path=path)
    if target_type is bool:
        return _decode_bool(value, path=path)
    if target_type in {str, int, float}:
        return _decode_scalar(value, target_type, path=path)
    return value if isinstance(value, target_type) else _raise_type_error(path, target_type, value)


def _decode_dataclass(value: Any, target_type: type[Any], *, path: str) -> Any:
    if not isinstance(value, dict):
        raise ConfigDecodeError(f"Expected mapping at {path}, got {type(value).__name__}")

    type_hints = get_type_hints(target_type)
    kwargs: dict[str, Any] = {}
    for field in fields(target_type):
        field_key = normalize_key(field.name)
        field_path = f"{path}.{field.name}" if path else field.name
        if field_key not in value:
            if field.default is not MISSING or field.default_factory is not MISSING:
                continue
            raise ConfigDecodeError(f"Missing required field {field_path}")
        kwargs[field.name] = decode_to_type(value[field_key], type_hints.get(field.name, field.type), path=field_path)
    return target_type(**kwargs)


def _decode_sequence(value: Any, target_type: type[Any], *, path: str) -> Any:
    if not isinstance(value, list):
        raise ConfigDecodeError(f"Expected list at {path}, got {type(value).__name__}")
    origin = get_origin(target_type)
    args = get_args(target_type)
    item_type = args[0] if args else Any
    decoded = [decode_to_type(item, item_type, path=f"{path}[{index}]") for index, item in enumerate(value)]
    if origin is list:
        return decoded
    if origin is set:
        return set(decoded)
    return frozenset(decoded)


def _decode_tuple(value: Any, target_type: type[Any], *, path: str) -> Any:
    if not isinstance(value, list | tuple):
        raise ConfigDecodeError(f"Expected tuple-compatible value at {path}, got {type(value).__name__}")
    args = get_args(target_type)
    if len(args) == 2 and args[1] is Ellipsis:
        return tuple(decode_to_type(item, args[0], path=f"{path}[{index}]") for index, item in enumerate(value))
    if args and len(args) != len(value):
        raise ConfigDecodeError(f"Expected {len(args)} items at {path}, got {len(value)}")
    return tuple(
        decode_to_type(item, args[index] if args else Any, path=f"{path}[{index}]")
        for index, item in enumerate(value)
    )


def _decode_mapping(value: Any, target_type: type[Any], *, path: str) -> Any:
    if not isinstance(value, dict):
        raise ConfigDecodeError(f"Expected mapping at {path}, got {type(value).__name__}")
    args = get_args(target_type)
    key_type = args[0] if len(args) >= 1 else str
    value_type = args[1] if len(args) >= 2 else Any
    return {
        _decode_scalar(key, key_type, path=f"{path}.<key>"): decode_to_type(item, value_type, path=f"{path}.{key}")
        for key, item in value.items()
    }


def _decode_union(value: Any, target_type: type[Any], *, path: str) -> Any:
    errors: list[str] = []
    for candidate in get_args(target_type):
        try:
            return decode_to_type(value, candidate, path=path)
        except ConfigDecodeError as exc:
            errors.append(str(exc))
    raise ConfigDecodeError(f"Value at {path} did not match any allowed type: {'; '.join(errors)}")


def _decode_literal(value: Any, target_type: type[Any], *, path: str) -> Any:
    allowed_values = get_args(target_type)
    for allowed in allowed_values:
        if value == allowed and type(value) is type(allowed):
            return value
    allowed_reprs = ", ".join(repr(v) for v in allowed_values)
    raise ConfigDecodeError(f"Expected one of {{{allowed_reprs}}} at {path}, got {value!r}")


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
    if isinstance(value, target_type) and not (target_type is int and isinstance(value, bool)):
        return value
    if isinstance(value, str):
        try:
            return target_type(value)
        except ValueError as exc:
            raise ConfigDecodeError(f"Could not coerce value at {path} to {target_type.__name__}") from exc
    raise ConfigDecodeError(f"Expected {target_type.__name__} at {path}, got {type(value).__name__}")


def _raise_type_error(path: str, target_type: type[Any], value: Any) -> Any:
    raise ConfigDecodeError(f"Expected {target_type!r} at {path}, got {type(value).__name__}")
