# Copyright 2026 Aaron John Schlosser, PhD.
"""Validate frontend API calls against FastAPI's live OpenAPI contract."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_API_DIR = ROOT / "web" / "src" / "api"

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}


def _string_constants(source: str) -> dict[str, str]:
    return {
        match.group("name"): match.group("value")
        for match in re.finditer(
            r"""\bconst\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*["'](?P<value>/api/[^"']*)["']""",
            source,
        )
    }


def _skip_generic(source: str, index: int) -> int:
    if index >= len(source) or source[index] != "<":
        return index
    depth = 0
    while index < len(source):
        char = source[index]
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise ValueError("unterminated apiRequest generic")


def _call_bounds(source: str, open_paren: int) -> tuple[int, int]:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(open_paren, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return open_paren + 1, index
    raise ValueError("unterminated apiRequest call")


def _first_argument(call_body: str) -> str:
    paren = bracket = brace = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(call_body):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == "{":
            brace += 1
        elif char == "}":
            brace -= 1
        elif char == "," and paren == bracket == brace == 0:
            return call_body[:index].strip()
    return call_body.strip()


def _template_route(expression: str, constants: dict[str, str]) -> str:
    body = expression[1:-1]
    output: list[str] = []
    index = 0
    while index < len(body):
        if not body.startswith("${", index):
            output.append(body[index])
            index += 1
            continue
        cursor = index + 2
        depth = 1
        while cursor < len(body) and depth:
            if body.startswith("${", cursor):
                depth += 1
                cursor += 2
                continue
            if body[cursor] == "}":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        if depth:
            raise ValueError(f"unterminated template expression: {expression}")
        dynamic = body[index + 2 : cursor].strip()
        if dynamic in constants:
            output.append(constants[dynamic])
        elif (
            re.search(r"(query|params|suffix)", dynamic, re.IGNORECASE)
            or re.search(r"""["']\?""", dynamic)
        ):
            # Query-string construction does not change the OpenAPI route.
            output.append("")
        else:
            output.append("{frontend_param}")
        index = cursor + 1
    return "".join(output)


def _route_expression(expression: str, constants: dict[str, str]) -> str | None:
    expression = expression.strip()
    if expression in constants:
        return constants[expression]
    if len(expression) >= 2 and expression[0] in {"'", '"'} and expression[-1] == expression[0]:
        return expression[1:-1]
    if len(expression) >= 2 and expression[0] == "`" and expression[-1] == "`":
        return _template_route(expression, constants)
    return None


def frontend_api_calls(api_dir: Path = FRONTEND_API_DIR) -> list[tuple[str, str, str]]:
    """Return (method, route, source-location) for every frontend apiRequest call."""
    calls: list[tuple[str, str, str]] = []
    unresolved: list[str] = []
    for path in sorted(api_dir.glob("*.ts")):
        if path.name == "http.ts":
            continue
        source = path.read_text(encoding="utf-8")
        constants = _string_constants(source)
        search_from = 0
        while True:
            start = source.find("apiRequest", search_from)
            if start < 0:
                break
            cursor = start + len("apiRequest")
            while cursor < len(source) and source[cursor].isspace():
                cursor += 1
            if cursor < len(source) and source[cursor] == "<":
                cursor = _skip_generic(source, cursor)
            while cursor < len(source) and source[cursor].isspace():
                cursor += 1
            if cursor >= len(source) or source[cursor] != "(":
                search_from = start + len("apiRequest")
                continue
            body_start, body_end = _call_bounds(source, cursor)
            body = source[body_start:body_end]
            argument = _first_argument(body)
            route = _route_expression(argument, constants)
            line = source.count("\n", 0, start) + 1
            location = f"{path.relative_to(ROOT)}:{line}"
            if route is None:
                unresolved.append(f"{location}: {argument}")
            else:
                route = route.split("?", 1)[0]
                method_match = re.search(r"""\bmethod\s*:\s*["']([A-Za-z]+)["']""", body)
                method = (method_match.group(1) if method_match else "GET").upper()
                calls.append((method, route, location))
            search_from = body_end + 1
    if unresolved:
        raise AssertionError(
            "API contract checker could not resolve frontend calls:\n" + "\n".join(unresolved)
        )
    return calls


def _route_regex(openapi_path: str) -> re.Pattern[str]:
    parts = re.split(r"(\{[^{}]+\})", openapi_path)
    pattern = "".join(r"[^/?]+" if part.startswith("{") else re.escape(part) for part in parts)
    return re.compile(f"^{pattern}$")


def contract_mismatches(openapi: dict[str, Any]) -> list[str]:
    """Return frontend method/path calls absent from the supplied OpenAPI schema."""
    operations: list[tuple[str, re.Pattern[str], str]] = []
    for path, definition in openapi.get("paths", {}).items():
        if not isinstance(definition, dict):
            continue
        for method in definition:
            upper = method.upper()
            if upper in _HTTP_METHODS:
                operations.append((upper, _route_regex(path), path))

    failures: list[str] = []
    for method, route, location in frontend_api_calls():
        if any(candidate_method == method and pattern.fullmatch(route) for candidate_method, pattern, _ in operations):
            continue
        same_route_methods = sorted(
            candidate_method
            for candidate_method, pattern, _ in operations
            if pattern.fullmatch(route)
        )
        detail = (
            f"backend exposes {', '.join(same_route_methods)}"
            if same_route_methods
            else "no matching backend route"
        )
        failures.append(f"{location}: {method} {route} ({detail})")
    return failures
