// Copyright 2026 Aaron John Schlosser, PhD.
// Generates the typed GraphQL client (src/api/graphql/generated.ts) from the checked-in schema
// SDL (schema.graphql, regenerated with `python scripts/export_graphql_schema.py`) and every
// `.graphql` document colocated under src/. `npm run codegen:check` fails if the output is stale.
import type { CodegenConfig } from "@graphql-codegen/cli";

const config: CodegenConfig = {
  schema: "src/api/graphql/schema.graphql",
  documents: "src/**/*.graphql",
  ignoreNoDocuments: false,
  generates: {
    "src/api/graphql/generated.ts": {
      plugins: [
        { add: { content: "/* Copyright 2026 Aaron John Schlosser, PhD. */" } },
        "typescript",
        "typescript-operations",
        "typed-document-node",
      ],
      config: {
        documentMode: "string",
        skipTypename: true,
        enumsAsTypes: true,
        avoidOptionals: false,
        scalars: {
          JSON: "unknown",
        },
      },
    },
  },
};

export default config;
