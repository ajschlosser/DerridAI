# Copyright 2026 Aaron John Schlosser, PhD.
"""Schema assembly: Query root only, bounded, masked, introspection off by default."""
from __future__ import annotations

from collections.abc import Callable

import strawberry
from strawberry.extensions import (
    AddValidationRules,
    MaskErrors,
    MaxAliasesLimiter,
    MaxTokensLimiter,
    QueryDepthLimiter,
)
from strawberry.extensions.base_extension import SchemaExtension
from strawberry.schema.config import StrawberryConfig

from ..config import settings
from .errors import should_mask_error
from .permissions import ROOT_FIELD_POLICY
from .queries.celf import CelfQueries
from .queries.records import RecordQueries
from .queries.research import ResearchQueries


@strawberry.type(description="Read-only cELF queries. Commands are REST; live events are WebSocket.")
class Query(CelfQueries, RecordQueries, ResearchQueries):
    pass


def _extensions(*, introspection: bool) -> list[Callable[[], SchemaExtension]]:
    # Factories, so each request gets fresh extension instances.
    max_tokens = settings.graphql_max_tokens
    max_depth = settings.graphql_max_depth
    max_aliases = settings.graphql_max_aliases
    extensions: list[Callable[[], SchemaExtension]] = [
        lambda: MaxTokensLimiter(max_token_count=max_tokens),
        lambda: QueryDepthLimiter(max_depth=max_depth),
        lambda: MaxAliasesLimiter(max_alias_count=max_aliases),
        lambda: MaskErrors(should_mask_error=should_mask_error, error_message="Internal server error."),
    ]
    if not introspection:
        from graphql.validation import NoSchemaIntrospectionCustomRule

        extensions.append(lambda: AddValidationRules([NoSchemaIntrospectionCustomRule]))
    return extensions


def build_schema(*, introspection: bool | None = None) -> strawberry.Schema:
    enabled = settings.graphql_introspection_enabled if introspection is None else introspection
    schema = strawberry.Schema(
        query=Query,
        config=StrawberryConfig(auto_camel_case=False),
        extensions=_extensions(introspection=enabled),
    )
    assert_root_fields_classified(schema)
    return schema


def assert_root_fields_classified(schema: strawberry.Schema) -> None:
    """Default deny: every root field must declare its authorization policy."""
    graphql_schema = schema._schema
    if graphql_schema.mutation_type is not None or graphql_schema.subscription_type is not None:
        raise RuntimeError("The GraphQL façade is query-only: no Mutation or Subscription root.")
    fields = set(graphql_schema.query_type.fields) if graphql_schema.query_type else set()
    unclassified = sorted(fields - set(ROOT_FIELD_POLICY))
    if unclassified:
        raise RuntimeError(f"GraphQL root fields lack an authorization policy: {', '.join(unclassified)}")


schema = build_schema()
