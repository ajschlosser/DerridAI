# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Validation and composition for Research-facing Chroma filter expressions.

These helpers intentionally own only the stable, bounded filter subset DerridAI
executes. They do not infer scholarly semantics and they never inspect source
text. Higher-level field/semantic resolution belongs outside this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

_METADATA_SCALAR_OPERATORS = {"$eq", "$ne"}
_METADATA_NUMERIC_OPERATORS = {"$gt", "$gte", "$lt", "$lte"}
_METADATA_SET_OPERATORS = {"$in", "$nin"}
_LOGICAL_OPERATORS = {"$and", "$or"}
_DOCUMENT_OPERATORS = {"$contains", "$not_contains"}


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) and value is not None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _homogeneous(values: Sequence[Any]) -> bool:
    """Return whether Chroma's set operand has one scalar runtime type."""

    if not values:
        return False
    first_type = type(values[0])
    return all(type(value) is first_type and _is_scalar(value) for value in values)


def normalize_metadata_filter(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Validate and copy a Chroma-style metadata filter.

    Chroma expects one field/operator per expression node. Multiple predicates
    are represented explicitly through `$and` / `$or`; enforcing that here
    gives the UI deterministic, actionable errors before retrieval starts.
    """

    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        raise ValueError("Metadata filter must be a non-empty JSON object.")
    return _normalize_metadata_node(value, path="where")


def _normalize_metadata_node(value: Mapping[str, Any], *, path: str) -> dict[str, Any]:
    if len(value) != 1:
        raise ValueError(
            f"{path} must contain exactly one field or logical operator; "
            "combine predicates with $and or $or."
        )

    key, operand = next(iter(value.items()))
    if key in _LOGICAL_OPERATORS:
        if not isinstance(operand, list) or len(operand) < 2:
            raise ValueError(f"{path}.{key} must contain at least two filter expressions.")
        normalized_children = []
        for index, child in enumerate(operand):
            if not isinstance(child, Mapping) or not child:
                raise ValueError(f"{path}.{key}[{index}] must be a non-empty JSON object.")
            normalized_children.append(
                _normalize_metadata_node(child, path=f"{path}.{key}[{index}]")
            )
        return {key: normalized_children}

    if not isinstance(key, str) or not key.strip() or key.startswith("$"):
        raise ValueError(f"{path} contains an invalid metadata field name.")
    field = key.strip()

    if _is_scalar(operand):
        return {field: operand}
    if not isinstance(operand, Mapping) or len(operand) != 1:
        raise ValueError(
            f"{path}.{field} must be a scalar or an object containing exactly one operator."
        )

    operator, operator_value = next(iter(operand.items()))
    if operator in _METADATA_SCALAR_OPERATORS:
        if not _is_scalar(operator_value):
            raise ValueError(f"{path}.{field}.{operator} requires a scalar value.")
    elif operator in _METADATA_NUMERIC_OPERATORS:
        if not _is_number(operator_value):
            raise ValueError(f"{path}.{field}.{operator} requires a numeric value.")
    elif operator in _METADATA_SET_OPERATORS:
        if not isinstance(operator_value, list) or not _homogeneous(operator_value):
            raise ValueError(
                f"{path}.{field}.{operator} requires a non-empty list of same-type scalar values."
            )
    else:
        allowed = ", ".join(
            sorted(
                _METADATA_SCALAR_OPERATORS
                | _METADATA_NUMERIC_OPERATORS
                | _METADATA_SET_OPERATORS
            )
        )
        raise ValueError(f"{path}.{field} uses unsupported operator {operator!r}; allowed: {allowed}.")

    return {field: {operator: deepcopy(operator_value)}}


def normalize_document_filter(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Validate and copy the stable Chroma document-filter subset."""

    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        raise ValueError("Document filter must be a non-empty JSON object.")
    return _normalize_document_node(value, path="where_document")


def _normalize_document_node(value: Mapping[str, Any], *, path: str) -> dict[str, Any]:
    if len(value) != 1:
        raise ValueError(
            f"{path} must contain exactly one document or logical operator; "
            "combine predicates with $and or $or."
        )

    operator, operand = next(iter(value.items()))
    if operator in _LOGICAL_OPERATORS:
        if not isinstance(operand, list) or len(operand) < 2:
            raise ValueError(f"{path}.{operator} must contain at least two filter expressions.")
        children = []
        for index, child in enumerate(operand):
            if not isinstance(child, Mapping) or not child:
                raise ValueError(f"{path}.{operator}[{index}] must be a non-empty JSON object.")
            children.append(
                _normalize_document_node(child, path=f"{path}.{operator}[{index}]")
            )
        return {operator: children}

    if operator not in _DOCUMENT_OPERATORS:
        allowed = ", ".join(sorted(_DOCUMENT_OPERATORS))
        raise ValueError(f"{path} uses unsupported operator {operator!r}; allowed: {allowed}.")
    if not isinstance(operand, str) or not operand:
        raise ValueError(f"{path}.{operator} requires a non-empty string.")
    return {operator: operand}


def metadata_filter_fields(value: Mapping[str, Any] | None) -> set[str]:
    """Collect metadata field names referenced by a validated filter."""

    if not value:
        return set()
    key, operand = next(iter(value.items()))
    if key in _LOGICAL_OPERATORS:
        fields: set[str] = set()
        for child in operand:
            if isinstance(child, Mapping):
                fields.update(metadata_filter_fields(child))
        return fields
    return {str(key)}


def combine_metadata_filters(
    *values: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Combine already-valid metadata filters without weakening either one."""

    filters = [normalize_metadata_filter(value) for value in values if value]
    filters = [value for value in filters if value is not None]
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def combine_document_filters(
    *values: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Combine already-valid document filters without weakening either one."""

    filters = [normalize_document_filter(value) for value in values if value]
    filters = [value for value in filters if value is not None]
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}
