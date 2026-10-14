/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

// Generates the typed GraphQL client (src/api/graphql/generated.ts) from the checked-in schema
// SDL (schema.graphql, regenerated with `python scripts/export_graphql_schema.py`) and every
// `.graphql` document colocated under src/. `npm run codegen:check` fails if the output is stale.
import type { CodegenConfig } from "@graphql-codegen/cli";

const LICENSE_HEADER = `/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */`;

const config: CodegenConfig = {
  schema: "src/api/graphql/schema.graphql",
  documents: "src/**/*.graphql",
  ignoreNoDocuments: false,
  generates: {
    "src/api/graphql/generated.ts": {
      plugins: [
        {
          add: {
            content: LICENSE_HEADER,
          },
        },
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
