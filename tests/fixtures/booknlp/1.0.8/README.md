<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# BookNLP 1.0.8 consumer fixtures

These fixtures describe the narrow upstream shapes that DerridAI's BookNLP adapter consumes. They are adapter fixtures, not BookNLP conformance tests and not evidence that BookNLP itself is correct.

Keep assertions focused on DerridAI-owned normalization: stable cluster identity, alias projection, source offsets/lemmas, and fields intentionally omitted from the provider-neutral contract. Compatibility with the installed third-party package belongs in a small integration smoke test rather than duplicated schema assertions.
