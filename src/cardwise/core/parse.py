"""Turn JSON-shaped mappings into dataclasses, naming the field that is wrong."""

from __future__ import annotations

import dataclasses
import types
import typing
from collections.abc import Mapping
from typing import Any, TypeVar

from cardwise.core.errors import ValidationError

T = TypeVar("T")


def _check_type(where: str, value: object, annotation: object) -> object:
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = typing.get_args(annotation)
        if value is None and type(None) in args:
            return None
        inner = next(a for a in args if a is not type(None))
        return _check_type(where, value, inner)
    if annotation is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"{where} must be a number, got {type(value).__name__}")
        return float(value)
    if annotation is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"{where} must be a whole number, got {value!r}")
        return value
    if annotation is str:
        if not isinstance(value, str):
            raise ValidationError(f"{where} must be text, got {type(value).__name__}")
        return value
    if annotation is bool:
        if not isinstance(value, bool):
            raise ValidationError(f"{where} must be true or false, got {value!r}")
        return value
    return value


def from_dict(cls: type[T], data: object, where: str = "") -> T:
    """Build ``cls`` (a dataclass) from ``data``, checking field names and scalar types.

    Unknown fields and missing required fields are errors. Nested dataclass
    fields must be handled by the caller (pass them already built in ``data``).
    """
    label = where or cls.__name__
    if not isinstance(data, Mapping):
        raise ValidationError(f"{label} must be an object, got {type(data).__name__}")
    fields = {f.name: f for f in dataclasses.fields(cls)}  # type: ignore[arg-type]
    unknown = sorted(set(data) - set(fields))
    if unknown:
        raise ValidationError(f"{label}: unknown field(s) {', '.join(unknown)}")
    hints = typing.get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for name, f in fields.items():
        if name not in data:
            no_default = f.default is dataclasses.MISSING
            if no_default and f.default_factory is dataclasses.MISSING:
                raise ValidationError(f"{label}: missing {name!r}")
            continue
        value = data[name]
        if dataclasses.is_dataclass(value):
            kwargs[name] = value
        else:
            kwargs[name] = _check_type(f"{label}.{name}", value, hints[name])
    return cls(**kwargs)
